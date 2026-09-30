#!/usr/bin/env python3
"""Skill Catalog 的本地只回环管理面板（仅使用 Python 标准库）。"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


MAX_BODY_BYTES = 64 * 1024
SKILL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*_[0-9a-f]{12}$")
FREQUENCIES = {"high", "low", "unclassified"}


def default_state_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / "skill-catalog"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def atomic_json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".", dir=path.parent, text=True)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


class CatalogService:
    """将运行时 JSON 数据安全地投影为面板 API。"""

    def __init__(self, state_root: Path) -> None:
        self.state_root = state_root.resolve()
        self.catalog_path = self.state_root / "catalog.json"
        self.health_path = self.state_root / "health.json"
        self.platform_health_path = self.state_root / "platform-health.json"
        self.overrides_path = self.state_root / "overrides.json"
        self.config_path = self.state_root / "config.json"
        self.skill_root = Path(__file__).resolve().parents[1]
        self.script_path = self.skill_root / "scripts" / "sync-index.ps1"
        self.lock = threading.RLock()

    def config(self) -> dict[str, Any]:
        config = read_json(self.config_path, {})
        if not isinstance(config, dict):
            return {}
        return config

    def allowed_categories(self) -> set[str]:
        values = self.config().get("allowed_categories", ["general", "observe"])
        if not isinstance(values, list):
            return {"general", "observe"}
        return {value for value in values if isinstance(value, str) and value}

    def _runtime_data(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        catalog = read_json(self.catalog_path, {"skills": [], "anomalies": []})
        overrides = read_json(self.overrides_path, {"skills": {}})
        health = read_json(self.health_path, {"status": "unknown", "message": "尚未建立索引。"})
        if not isinstance(catalog, dict):
            catalog = {"skills": [], "anomalies": []}
        if not isinstance(overrides, dict):
            overrides = {"skills": {}}
        if not isinstance(health, dict):
            health = {"status": "unknown", "message": "无法读取健康状态。"}
        if not isinstance(overrides.get("skills"), dict):
            overrides["skills"] = {}
        if not isinstance(catalog.get("skills"), list):
            catalog["skills"] = []
        return catalog, overrides, health

    def catalog_payload(self, csrf_token: str) -> dict[str, Any]:
        with self.lock:
            catalog, overrides, health = self._runtime_data()
            merged: list[dict[str, Any]] = []
            for skill in catalog["skills"]:
                if not isinstance(skill, dict) or not isinstance(skill.get("skill_id"), str):
                    continue
                preference = overrides["skills"].get(skill["skill_id"], {})
                if not isinstance(preference, dict):
                    preference = {}
                merged.append(
                    {
                        "skill_id": skill["skill_id"],
                        "logical_name": skill.get("logical_name", skill.get("name", "")),
                        "name": skill.get("name", ""),
                        "description": skill.get("description", ""),
                        "managed": bool(skill.get("managed", False)),
                        "availability": skill.get("availability", "unknown"),
                        "integrity": skill.get("integrity", "unknown"),
                        "source_kind": skill.get("source_kind", "unknown"),
                        "adoptability": skill.get("adoptability", "review-required"),
                        "sources": [
                            {
                                "root_id": source.get("root_id", ""),
                                "availability": source.get("availability", "unknown"),
                                "source_type": source.get("source_type", ""),
                            }
                            for source in skill.get("sources", [])
                            if isinstance(source, dict)
                        ],
                        "frequency": preference.get("frequency", "unclassified"),
                        "category": preference.get("category", "general"),
                        "tags": preference.get("tags", []),
                        "note": preference.get("note", ""),
                        "pinned": bool(preference.get("pinned", False)),
                    }
                )
            return {
                "skills": merged,
                "health": self._safe_health(health),
                "platform_health": self._safe_platform_health(read_json(self.platform_health_path, {})),
                "anomalies": self._safe_anomalies(catalog.get("anomalies", [])),
                "generated_at": catalog.get("generated_at"),
                "csrf_token": csrf_token,
                "allowed_categories": sorted(self.allowed_categories()),
            }

    @staticmethod
    def _safe_health(health: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": health.get("status", "unknown"),
            "checked_at": health.get("checked_at"),
            "last_success_at": health.get("last_success_at"),
            "message": health.get("message"),
            "anomalies": health.get("anomalies", 0),
        }

    @staticmethod
    def _safe_platform_health(platform_health: Any) -> dict[str, Any]:
        if not isinstance(platform_health, dict):
            return {"status": "unknown", "platforms": []}
        safe_platforms: list[dict[str, Any]] = []
        values = platform_health.get("platforms", [])
        if isinstance(values, list):
            for platform in values:
                if not isinstance(platform, dict):
                    continue
                actions = platform.get("actions", [])
                if not isinstance(actions, list):
                    actions = []
                safe_platforms.append(
                    {
                        "platform_id": platform.get("platform_id", "unknown"),
                        "mode": platform.get("mode", "unknown"),
                        "status": platform.get("status", "unknown"),
                        "message": platform.get("message"),
                        "linked": sum(1 for action in actions if isinstance(action, dict) and action.get("action") == "current"),
                        "pending": sum(1 for action in actions if isinstance(action, dict) and action.get("action") == "create-junction"),
                        "conflicts": sum(1 for action in actions if isinstance(action, dict) and action.get("action") == "conflict"),
                    }
                )
        canonical = platform_health.get("canonical", {})
        if not isinstance(canonical, dict):
            canonical = {}
        return {
            "status": platform_health.get("status", "unknown"),
            "checked_at": platform_health.get("checked_at"),
            "canonical_skills": canonical.get("skills", 0),
            "platforms": safe_platforms,
        }

    @staticmethod
    def _safe_anomalies(anomalies: Any) -> list[dict[str, str]]:
        if not isinstance(anomalies, list):
            return []
        return [
            {
                "root_id": str(item.get("root_id", "")),
                "severity": str(item.get("severity", "warning")),
                "message": str(item.get("message", "")),
            }
            for item in anomalies
            if isinstance(item, dict)
        ]

    def skill_detail(self, skill_id: str) -> dict[str, Any] | None:
        if not SKILL_ID_RE.fullmatch(skill_id):
            return None
        with self.lock:
            catalog, overrides, _ = self._runtime_data()
            target = next(
                (skill for skill in catalog["skills"] if isinstance(skill, dict) and skill.get("skill_id") == skill_id),
                None,
            )
            if not target:
                return None
            sources = target.get("sources", [])
            preferred = sorted(
                (source for source in sources if isinstance(source, dict)),
                key=lambda source: 0 if source.get("availability") == "active" else 1,
            )
            content = ""
            for source in preferred:
                directory = source.get("path")
                if not isinstance(directory, str):
                    continue
                skill_file = Path(directory) / "SKILL.md"
                try:
                    content = skill_file.read_text(encoding="utf-8-sig")
                    break
                except (OSError, UnicodeDecodeError):
                    continue
            preference = overrides["skills"].get(skill_id, {})
            return {
                "skill_id": skill_id,
                "name": target.get("name", ""),
                "description": target.get("description", ""),
                "availability": target.get("availability", "unknown"),
                "integrity": target.get("integrity", "unknown"),
                "source_kind": target.get("source_kind", "unknown"),
                "adoptability": target.get("adoptability", "review-required"),
                "frequency": preference.get("frequency", "unclassified") if isinstance(preference, dict) else "unclassified",
                "category": preference.get("category", "general") if isinstance(preference, dict) else "general",
                "tags": preference.get("tags", []) if isinstance(preference, dict) else [],
                "note": preference.get("note", "") if isinstance(preference, dict) else "",
                "pinned": bool(preference.get("pinned", False)) if isinstance(preference, dict) else False,
                "content": content,
            }

    def update_override(self, payload: dict[str, Any]) -> dict[str, Any]:
        expected = {"skill_id", "frequency", "category", "tags", "note", "pinned"}
        if set(payload) - expected or not isinstance(payload.get("skill_id"), str):
            raise ValueError("请求字段不符合要求。")
        skill_id = payload["skill_id"]
        if not SKILL_ID_RE.fullmatch(skill_id):
            raise ValueError("Skill 标识无效。")
        frequency = payload.get("frequency", "unclassified")
        category = payload.get("category", "general")
        tags = payload.get("tags", [])
        note = payload.get("note", "")
        pinned = payload.get("pinned", False)
        if frequency not in FREQUENCIES or category not in self.allowed_categories():
            raise ValueError("标签值不在允许范围内。")
        if not isinstance(tags, list) or len(tags) > 20 or any(not isinstance(tag, str) or len(tag) > 32 for tag in tags):
            raise ValueError("标签格式无效。")
        if not isinstance(note, str) or len(note) > 500 or not isinstance(pinned, bool):
            raise ValueError("备注或置顶值无效。")
        with self.lock:
            catalog, overrides, _ = self._runtime_data()
            if not any(skill.get("skill_id") == skill_id for skill in catalog["skills"] if isinstance(skill, dict)):
                raise ValueError("未找到该 Skill。")
            if self.overrides_path.exists():
                shutil.copy2(self.overrides_path, self.overrides_path.with_suffix(self.overrides_path.suffix + ".bak"))
            overrides["schema_version"] = overrides.get("schema_version", 1)
            overrides["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            overrides["skills"][skill_id] = {
                "frequency": frequency,
                "category": category,
                "tags": tags,
                "note": note,
                "pinned": pinned,
            }
            atomic_json_write(self.overrides_path, overrides)
        return {"skill_id": skill_id, "frequency": frequency, "category": category}

    def rebuild(self) -> dict[str, Any]:
        with self.lock:
            before, _, _ = self._runtime_data()
            self._run_script(["-Rebuild"], "刷新索引")
            after, _, health = self._runtime_data()
            return {
                "before_count": len(before.get("skills", [])),
                "after_count": len(after.get("skills", [])),
                "health": self._safe_health(health),
            }

    def _run_script(self, arguments: list[str], operation: str, timeout: int = 90) -> str:
        executable = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
        command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.script_path), *arguments, "-StateRoot", str(self.state_root)]
        try:
            completed = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError(f"{operation}未能完成，请稍后重试。")
        if completed.returncode != 0:
            raise RuntimeError(f"{operation}失败，已保留现有数据。")
        return completed.stdout.strip()

    @staticmethod
    def _safe_plan(plan: dict[str, Any]) -> dict[str, Any]:
        manifest = plan.get("copy_manifest", [])
        risks = plan.get("risk_findings", [])
        return {
            "plan_id": plan.get("plan_id"),
            "status": plan.get("status"),
            "expires_at": plan.get("expires_at"),
            "skill_id": plan.get("skill_id"),
            "logical_name": plan.get("logical_name"),
            "expected_content_hash": plan.get("expected_content_hash"),
            "copy_manifest": [
                {"path": item.get("path", ""), "bytes": item.get("bytes", 0)}
                for item in manifest if isinstance(item, dict)
            ],
            "risk_findings": [
                {"type": item.get("type", ""), "path": item.get("path", ""), "bytes": item.get("bytes", 0), "message": item.get("message", "")}
                for item in risks if isinstance(item, dict)
            ],
        }

    def adoption_plan(self, skill_id: str) -> dict[str, Any]:
        if not SKILL_ID_RE.fullmatch(skill_id):
            raise ValueError("Skill 标识无效。")
        with self.lock:
            output = self._run_script(["-AdoptPlan", skill_id], "收编预检")
            try:
                plan = json.loads(output)
            except json.JSONDecodeError:
                raise RuntimeError("收编预检未返回有效计划。")
            if not isinstance(plan, dict) or plan.get("status") != "pending":
                raise RuntimeError("收编预检未生成可提交计划。")
            return self._safe_plan(plan)

    def adoption_commit(self, payload: dict[str, Any]) -> dict[str, Any]:
        expected = {"plan_id", "skill_id", "expected_content_hash"}
        if set(payload) != expected:
            raise ValueError("收编确认字段不符合要求。")
        plan_id = payload.get("plan_id")
        skill_id = payload.get("skill_id")
        expected_hash = payload.get("expected_content_hash")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            raise ValueError("收编计划标识无效。")
        if not isinstance(skill_id, str) or not SKILL_ID_RE.fullmatch(skill_id):
            raise ValueError("Skill 标识无效。")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("内容校验标识无效。")
        with self.lock:
            plan = read_json(self.state_root / "transactions" / "plans" / f"{plan_id}.json", {})
            if not isinstance(plan, dict) or plan.get("status") != "pending":
                raise ValueError("收编计划已不可提交。")
            if plan.get("skill_id") != skill_id or plan.get("expected_content_hash") != expected_hash:
                raise ValueError("收编计划与确认内容不一致。")
            output = self._run_script(["-AdoptCommit", plan_id, "-Confirmed"], "收编提交", timeout=150)
            try:
                result = json.loads(output)
            except json.JSONDecodeError:
                raise RuntimeError("收编提交未返回有效结果。")
            return {"status": result.get("status"), "logical_name": result.get("logical_name")}


class CatalogHandler(BaseHTTPRequestHandler):
    service: CatalogService
    csrf_token: str
    public_origin: str

    server_version = "SkillCatalog/1.0"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # 本地面板不输出 URL 查询串或请求体，避免意外暴露用户输入。
        return

    def _headers(self, status: HTTPStatus, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
        )

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self._headers(status, content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"error": message})

    def _is_same_origin(self) -> bool:
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        expected_host = self.public_origin[len("http://") :]
        return host == expected_host and origin == self.public_origin

    def _read_json_body(self) -> dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "仅接受 JSON 请求。")
            return None
        length = self.headers.get("Content-Length")
        try:
            size = int(length)
        except (TypeError, ValueError):
            self._error(HTTPStatus.LENGTH_REQUIRED, "请求长度无效。")
            return None
        if size < 0 or size > MAX_BODY_BYTES:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "请求体过大。")
            return None
        try:
            body = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(HTTPStatus.BAD_REQUEST, "JSON 格式无效。")
            return None
        if not isinstance(body, dict):
            self._error(HTTPStatus.BAD_REQUEST, "请求体必须为对象。")
            return None
        return body

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            try:
                page = (self.service.skill_root / "panel" / "static" / "index.html").read_bytes()
            except OSError:
                self._error(HTTPStatus.SERVICE_UNAVAILABLE, "面板资源暂不可用。")
                return
            self._text(HTTPStatus.OK, page, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/catalog":
            self._json(HTTPStatus.OK, self.service.catalog_payload(self.csrf_token))
            return
        if parsed.path == "/api/skill":
            skill_id = parse_qs(parsed.query).get("id", [""])[0]
            detail = self.service.skill_detail(skill_id)
            if detail is None:
                self._error(HTTPStatus.NOT_FOUND, "未找到该 Skill。")
                return
            self._json(HTTPStatus.OK, detail)
            return
        self._error(HTTPStatus.NOT_FOUND, "未找到请求的资源。")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not self._is_same_origin() or not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), self.csrf_token):
            self._error(HTTPStatus.FORBIDDEN, "请求未通过本地安全校验。")
            return
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            if parsed.path == "/api/overrides":
                self._json(HTTPStatus.OK, {"saved": self.service.update_override(payload)})
                return
            if parsed.path == "/api/rebuild":
                if payload:
                    raise ValueError("刷新请求不接受额外字段。")
                self._json(HTTPStatus.OK, {"rebuilt": self.service.rebuild()})
                return
            if parsed.path == "/api/adopt/plan":
                if set(payload) != {"skill_id"}:
                    raise ValueError("收编预检字段不符合要求。")
                self._json(HTTPStatus.OK, {"plan": self.service.adoption_plan(payload["skill_id"])})
                return
            if parsed.path == "/api/adopt/commit":
                self._json(HTTPStatus.OK, {"committed": self.service.adoption_commit(payload)})
                return
            self._error(HTTPStatus.NOT_FOUND, "未找到请求的资源。")
        except ValueError as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except RuntimeError as error:
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))


def start_server(service: CatalogService) -> tuple[ThreadingHTTPServer, str]:
    panel = service.config().get("panel", {})
    requested_port = panel.get("port", 8765) if isinstance(panel, dict) else 8765
    try:
        requested_port = int(requested_port)
    except (TypeError, ValueError):
        requested_port = 8765
    requested_port = max(1024, min(requested_port, 65515))
    for port in range(requested_port, min(requested_port + 21, 65536)):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), CatalogHandler)
            origin = f"http://127.0.0.1:{port}"
            CatalogHandler.service = service
            CatalogHandler.csrf_token = secrets.token_urlsafe(32)
            CatalogHandler.public_origin = origin
            return server, origin
        except OSError:
            continue
    raise RuntimeError("本地面板端口不可用，请稍后重试。")


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 Skill Catalog 本地面板")
    parser.add_argument("--state-root", type=Path, default=default_state_root(), help="运行时状态目录")
    args = parser.parse_args()
    service = CatalogService(args.state_root)
    server, origin = start_server(service)
    print(f"Skill Catalog 面板已启动：{origin}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
