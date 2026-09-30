# -*- coding: utf-8 -*-
"""创建单个缺陷：消费 AI 生成的 bug JSON（见 bug_draft_prompt.md）。

用法：
    python create_bug.py --file bug.json     # 正式创建
    python create_bug.py --file bug.json --dry-run   # 只打印将创建的内容
    type bug.json | python create_bug.py     # stdin 传入（Windows）

bug JSON 字段：
    module    模块名（可选，写入描述）
    title     缺陷标题（必填）
    steps     复现步骤，字符串数组（必填）
    expected  预期结果（必填）
    actual    实际结果（必填）
    images    截图文件路径数组（可选，创建后上传并内嵌进描述）
    severity  严重程度（可选，默认按 field_map 第一项；需 field_map 有映射）
    priority  优先级（可选，同上）
    assignee  负责人姓名（可选，解析不到则留空）
    verifier  验证者姓名（可选，解析不到则留空）
"""

import argparse
import json
import sys
from pathlib import Path

from yunxiao_client import YunxiaoApiError, load_config, client_from_config

REQUIRED_FIELDS = ("title", "steps", "expected", "actual")


def load_bug_json(args):
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    try:
        bug = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"bug JSON 解析失败: {e}")
        sys.exit(1)
    if not bug.get("title"):
        print("bug JSON 缺少必填字段: ['title']")
        sys.exit(1)
    if bug.get("description"):
        # 场景B/自定义：直接给成品描述，steps/expected/actual 不再必填
        return bug
    missing = [k for k in REQUIRED_FIELDS if not bug.get(k)]
    if missing:
        print(f"bug JSON 缺少必填字段: {missing}（或改用 description 直接给成品描述）")
        sys.exit(1)
    if isinstance(bug["steps"], str):
        bug["steps"] = [bug["steps"]]
    return bug


def resolve_user(client, cfg, name, warnings, cache):
    """姓名 -> userId：config.users → members:search 实时查。失败返回 None。"""
    if not name:
        return None
    name = str(name).strip()
    if not name:
        return None
    if name in cache:
        return cache[name]
    uid = cfg.get("users", {}).get(name)
    if not uid and client is not None:
        try:
            r = client._request(
                "POST",
                f"/oapi/v1/platform/organizations/{cfg['organization_id']}/members:search",
                {"query": name, "page": 1, "perPage": 10},
            )
            exact = [m for m in r if m.get("name") == name]
            if exact:
                uid = exact[0]["userId"]
            elif r:
                warnings.append(f"「{name}」无精确匹配，候选: {[m.get('name') for m in r]}，该字段留空")
        except YunxiaoApiError as e:
            warnings.append(f"「{name}」成员查询失败: {e}，该字段留空")
    if not uid:
        warnings.append(f"「{name}」无法解析 userId，该字段留空（创建后在云效分配）")
    cache[name] = uid
    return uid


def map_field(cfg, field_name, value, defaults, warnings):
    """严重程度/优先级中文名 -> (fieldId, optionId)。"""
    field_cfg = cfg.get("field_map", {}).get(field_name) or {}
    field_id = field_cfg.get("field_id")
    if not field_id:
        return None
    options = field_cfg.get("options", {})
    value = (value or "").strip() or defaults.get(field_name)
    option_id = options.get(value)
    if not option_id:
        warnings.append(f"[{field_name}] 值「{value}」无映射，已跳过该字段")
        return None
    return (field_id, option_id)


def build_description(bug):
    """场景A 模板：模块路径 → 复现步骤 → 实际结果 → 预期结果。"""
    lines = []
    if bug.get("module"):
        lines.append("## 【模块名称/路径】")
        lines.append(str(bug["module"]).strip())
        lines.append("")
    lines.append("## 【复现步骤】")
    for i, step in enumerate(bug["steps"], 1):
        s = str(step).strip()
        # AI 生成的步骤可能自带编号，去掉统一重排
        for prefix in (f"{i}.", f"{i}、", f"{i}."):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
                break
        lines.append(f"{i}. {s}")
    lines.append("\n## 【实际结果】")
    lines.append(str(bug["actual"]).strip())
    lines.append("\n## 【预期结果】")
    lines.append(str(bug["expected"]).strip())
    return "\n".join(lines)


def get_description(bug):
    """成品描述优先（场景B 原文/自定义），否则按场景A 模板组装。"""
    if bug.get("description"):
        return str(bug["description"]).strip()
    return build_description(bug)


def print_draft(bug, custom, assignee_uid, verifier_uid, warnings):
    print("===== 缺陷草稿 =====")
    print(f"标题: {bug['title']}")
    print(f"模块: {bug.get('module') or '-'}")
    print(f"负责人: {bug.get('assignee') or '-'} ({assignee_uid or '留空'})")
    print(f"验证者: {bug.get('verifier') or '-'} ({verifier_uid or '留空'})")
    print(f"严重程度: {bug.get('severity') or '默认'}  优先级: {bug.get('priority') or '默认'}")
    print(f"自定义字段: {custom or '无'}")
    print(f"截图: {len(bug.get('images') or [])} 张")
    print("----- 描述 -----")
    print(get_description(bug))
    for w in warnings:
        print(f"[提醒] {w}")


def main():
    parser = argparse.ArgumentParser(description="按 bug JSON 创建单个云效缺陷")
    parser.add_argument("--file", help="bug JSON 文件路径，缺省读 stdin")
    parser.add_argument("--dry-run", action="store_true", help="只打印草稿，不调用接口")
    parser.add_argument("--project", help="切换到 config.projects 里的其他项目（如 02【税务】）")
    args = parser.parse_args()

    cfg = load_config()
    if args.project:
        prof = cfg.get("projects", {}).get(args.project)
        if not prof:
            print(f"config.projects 中未配置项目: {args.project}")
            sys.exit(1)
        cfg.update(prof)  # 覆盖 space_id / project_name 等
    bug = load_bug_json(args)

    # 图片存在性检查
    images = bug.get("images") or []
    for p in images:
        if not Path(p).exists():
            print(f"截图文件不存在: {p}")
            sys.exit(1)

    warnings = []
    client = None
    if not args.dry_run:
        for key in ("space_id", "workitem_type_id"):
            if not cfg.get(key):
                print(f"config.json 缺少配置项: {key}")
                sys.exit(1)
        try:
            client = client_from_config(cfg)
        except YunxiaoApiError as e:
            print(e)
            sys.exit(1)

    cache = {}
    assignee_uid = resolve_user(client, cfg, bug.get("assignee"), warnings, cache)
    verifier_uid = resolve_user(client, cfg, bug.get("verifier"), warnings, cache)
    custom = {}
    for field_name, key in (("严重程度", "severity"), ("优先级", "priority")):
        mapped = map_field(cfg, field_name, bug.get(key),
                           {"严重程度": "一般", "优先级": "中"}, warnings)
        if mapped:
            custom[mapped[0]] = mapped[1]

    if args.dry_run:
        print_draft(bug, custom, assignee_uid, verifier_uid, warnings)
        return

    description = get_description(bug)
    try:
        wid = client.create_workitem(
            space_id=cfg["space_id"],
            workitem_type_id=cfg["workitem_type_id"],
            subject=bug["title"].strip(),
            assigned_to=assignee_uid or cfg.get("default_assignee"),
            verifier=verifier_uid,
            description=description,
            custom_field_values=custom or None,
        )
    except YunxiaoApiError as e:
        print(f"创建缺陷失败: {e}")
        sys.exit(1)

    # 上传截图并内嵌到描述末尾
    embeds = []
    for i, p in enumerate(images, 1):
        path = Path(p)
        try:
            att = client.upload_attachment(wid, path.read_bytes(), path.name)
            embeds.append(att.get("embedMarkdown") or f"![{path.name}]({att.get('embedUrl')})")
        except YunxiaoApiError as e:
            print(f"[提醒] 截图 {path.name} 上传失败: {e}")
    if embeds:
        client.update_workitem(wid, description=description + "\n\n" + "\n".join(embeds),
                               formatType="MARKDOWN")

    print(f"缺陷创建成功: {wid}")
    print(f"项目: {cfg.get('project_name') or cfg['space_id']}（在云效对应项目中搜索标题即可查看）")
    for w in warnings:
        print(f"[提醒] {w}")


if __name__ == "__main__":
    main()
