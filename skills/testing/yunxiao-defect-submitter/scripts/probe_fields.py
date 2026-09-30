# -*- coding: utf-8 -*-
"""联调辅助：列出项目的工作项类型、查看缺陷类型的字段配置。

用法：
    python probe_fields.py types            # 列出工作项类型（找「缺陷」的 workitemTypeId）
    python probe_fields.py fields           # 查看 config 中 workitem_type_id 的字段配置
"""

import sys

from yunxiao_client import YunxiaoApiError, load_config, client_from_config


def main():
    cfg = load_config()
    for key in ("organization_id", "space_id"):
        if not cfg.get(key):
            print(f"config.json 缺少配置项: {key}")
            sys.exit(1)
    try:
        client = client_from_config(cfg)
    except YunxiaoApiError as e:
        print(e)
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "types"

    if mode == "types":
        category = sys.argv[2] if len(sys.argv) > 2 else "Bug"
        types = client.list_workitem_types(cfg["space_id"], category=category)
        print(f"{'name':<16}{'id'}")
        for t in types:
            print(f"{t.get('name', ''):<16}{t.get('id', '')}")

    elif mode == "fields":
        if not cfg.get("workitem_type_id"):
            print("请先在 config.json 填入 workitem_type_id")
            sys.exit(1)
        fields = client.get_type_fields(cfg["space_id"], cfg["workitem_type_id"])
        for f in fields:
            print(f"\n字段: {f.get('name')}  id={f.get('id')}  type={f.get('type')}  format={f.get('format')}  required={f.get('required')}")
            for opt in f.get("options") or []:
                print(f"    选项: {opt.get('displayValue')}  id={opt.get('id')}  value={opt.get('value')}")
    else:
        print("未知参数，用 types 或 fields")
        sys.exit(1)


if __name__ == "__main__":
    main()
