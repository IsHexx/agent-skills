# -*- coding: utf-8 -*-
"""云效 Projex OpenAPI 封装层（创建工作项/缺陷相关）。

接口文档：
- CreateWorkitem            POST /oapi/v1/projex/workitems
- ListWorkitemTypes         GET  /oapi/v1/projex/organizations/{organizationId}/projects/{id}/workitemTypes
- GetWorkitemTypeFieldConfig GET /oapi/v1/projex/projects/{projectId}/workitemTypes/{id}/fields

认证：请求头 x-yunxiao-token（个人访问令牌）。
中心版接入点：openapi-rdc.aliyuncs.com；专属版填实例域名。
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"


def load_config(path=None):
    """读取配置文件（默认同目录 config.json），并支持环境变量覆盖敏感项：
    YUNXIAO_TOKEN / YUNXIAO_ORG_ID / YUNXIAO_SPACE_ID / YUNXIAO_DOMAIN。
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    env_map = {
        "YUNXIAO_TOKEN": "token",
        "YUNXIAO_ORG_ID": "organization_id",
        "YUNXIAO_SPACE_ID": "space_id",
        "YUNXIAO_DOMAIN": "domain",
    }
    for env_key, cfg_key in env_map.items():
        if os.environ.get(env_key):
            cfg[cfg_key] = os.environ[env_key]
    return cfg


def client_from_config(cfg):
    """按配置 dict 构造 YunxiaoClient。"""
    if not cfg.get("token"):
        raise YunxiaoApiError("未配置 token：请填 config.json 的 token 或设置环境变量 YUNXIAO_TOKEN")
    return YunxiaoClient(
        token=cfg["token"],
        domain=cfg.get("domain", "openapi-rdc.aliyuncs.com"),
        organization_id=cfg.get("organization_id"),
    )


class YunxiaoApiError(Exception):
    """云效接口调用失败（HTTP 错误或业务错误）。"""

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


class YunxiaoClient:
    def __init__(self, token, domain="openapi-rdc.aliyuncs.com", organization_id=None, timeout=30):
        self.token = token
        self.domain = domain.rstrip("/")
        self.organization_id = organization_id
        self.timeout = timeout

    # ---------- 基础请求 ----------

    def _url(self, path):
        return f"https://{self.domain}{path}"

    def _projex(self, suffix):
        """中心版路径带 /organizations/{orgId}；专属版（Region）不带。"""
        if self.organization_id:
            return f"/oapi/v1/projex/organizations/{self.organization_id}{suffix}"
        return f"/oapi/v1/projex{suffix}"

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self._url(path),
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "x-yunxiao-token": self.token,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                if not body:
                    return {}
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return {"raw": body}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise YunxiaoApiError(f"HTTP {e.code}: {body}", status=e.code, body=body) from e
        except urllib.error.URLError as e:
            raise YunxiaoApiError(f"网络错误: {e.reason}") from e

    # ---------- 项目（联调用） ----------

    def search_projects(self, name=None, per_page=50):
        """搜索项目，用于查 spaceId。name 为空时返回全部（分页取第一页）。"""
        payload = {"perPage": per_page, "page": 1}
        if name:
            payload["conditions"] = json.dumps([{"field": "name", "operator": "CONTAINS", "value": [name]}])
        return self._request("POST", self._projex("/projects:search"), payload)

    # ---------- 工作项类型 / 字段配置（联调用） ----------

    def list_workitem_types(self, space_id, category="Bug"):
        """获取项目下的工作项类型列表，用于查「缺陷」的 workitemTypeId。
        category 可选 Req / Bug / Task 等。"""
        return self._request("GET", self._projex(f"/projects/{space_id}/workitemTypes?category={category}"))

    def get_type_fields(self, space_id, workitem_type_id):
        """获取某工作项类型的字段配置，用于查优先级/严重程度等字段的 fieldId 与选项ID。"""
        return self._request("GET", self._projex(f"/projects/{space_id}/workitemTypes/{workitem_type_id}/fields"))

    # ---------- 创建工作项 ----------

    def create_workitem(self, space_id, workitem_type_id, subject, assigned_to,
                        description=None, custom_field_values=None,
                        sprint=None, versions=None, labels=None,
                        verifier=None, participants=None, trackers=None,
                        format_type="MARKDOWN"):
        """创建工作项（缺陷/需求/任务等），返回创建的工作项 id。"""
        payload = {
            "spaceId": space_id,
            "workitemTypeId": workitem_type_id,
            "subject": subject,
            "assignedTo": assigned_to,
            "formatType": format_type,
        }
        if description:
            payload["description"] = description
        if custom_field_values:
            payload["customFieldValues"] = custom_field_values
        if sprint:
            payload["sprint"] = sprint
        if versions:
            payload["versions"] = versions
        if labels:
            payload["labels"] = labels
        if verifier:
            payload["verifier"] = verifier
        if participants:
            payload["participants"] = participants
        if trackers:
            payload["trackers"] = trackers

        result = self._request("POST", self._projex("/workitems"), payload)
        workitem_id = result.get("id")
        if not workitem_id:
            raise YunxiaoApiError(f"创建失败，返回异常: {result}", body=json.dumps(result, ensure_ascii=False))
        return workitem_id

    # ---------- 更新工作项 ----------

    def update_workitem(self, workitem_id, **fields):
        """更新工作项，支持 subject/description/formatType/assignedTo/verifier/
        sprint/labels/trackers/participants/versions 及 customFieldValues。"""
        custom = fields.pop("custom_field_values", None)
        body = {k: v for k, v in fields.items() if v is not None}
        if custom:
            body.update(custom)
        return self._request("PUT", self._projex(f"/workitems/{workitem_id}"), body)

    # ---------- 附件 ----------

    def upload_attachment(self, workitem_id, file_bytes, filename):
        """给工作项上传附件（multipart/form-data），返回附件信息 dict。"""
        import uuid
        boundary = "----pybd" + uuid.uuid4().hex
        safe_name = filename.replace('"', "_").replace("\\", "_")
        body = b"\r\n".join([
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{safe_name}"'.encode(),
            b"Content-Type: application/octet-stream",
            b"", file_bytes,
            f"--{boundary}--".encode(), b"",
        ])
        req = urllib.request.Request(
            self._url(self._projex(f"/workitems/{workitem_id}/attachments")),
            data=body, method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "x-yunxiao-token": self.token,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode("utf-8", errors="replace")
            raise YunxiaoApiError(f"附件上传失败 HTTP {e.code}: {body_txt}", status=e.code, body=body_txt) from e
