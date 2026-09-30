# -*- coding: utf-8 -*-
"""联调辅助：列出项目的缺陷类型、查看缺陷类型的字段配置。

用法：
    python probe_fields.py types            # 列出缺陷类工作项类型（找 issue_type）
    python probe_fields.py fields           # 查看 config 中 issue_type 的字段配置

平台差异全部在 defect_client.py，本脚本不直接调任何平台 API。
"""

import sys

from defect_client import DefectApiError, load_config, client_from_config


def main():
    cfg = load_config()
    if not cfg.get("project"):
        print("config.json 缺少配置项: project")
        sys.exit(1)
    try:
        client = client_from_config(cfg)
    except DefectApiError as e:
        print(e)
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "types"

    if mode == "types":
        types = client.list_issue_types(cfg["project"])
        print(f"{'name':<16}{'id'}")
        for t in types:
            print(f"{t.get('name', ''):<16}{t.get('id', '')}")

    elif mode == "fields":
        if not cfg.get("issue_type"):
            print("请先在 config.json 填入 issue_type")
            sys.exit(1)
        fields = client.get_type_fields(cfg["project"], cfg["issue_type"])
        for f in fields:
            print(f"\n字段: {f.get('name')}  id={f.get('id')}  type={f.get('type')}  format={f.get('format')}  required={f.get('required')}")
            for opt in f.get("options") or []:
                print(f"    选项: {opt.get('displayValue')}  id={opt.get('id')}  value={opt.get('value')}")
    else:
        print("未知参数，用 types 或 fields")
        sys.exit(1)


if __name__ == "__main__":
    main()
