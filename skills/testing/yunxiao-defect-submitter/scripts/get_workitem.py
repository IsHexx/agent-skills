#!/usr/bin/env python
"""查询云效工作项（缺陷/需求/任务）详情，打印关键字段，用于提单后核对。

用法：
    python get_workitem.py --workitem-id <工作项ID>
    python get_workitem.py --workitem-id <工作项ID> --full     # 额外打印完整描述

用途：`create_bug.py` 在正式创建时不打印姓名解析告警，姓名解析失败会静默回落到
default_assignee；创建后用本脚本核对 assignedTo / verifier / 图片数最稳妥。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from yunxiao_client import load_config, client_from_config


def main():
    parser = argparse.ArgumentParser(description="查询云效工作项详情")
    parser.add_argument("--workitem-id", required=True, help="工作项 ID")
    parser.add_argument("--full", action="store_true", help="额外打印完整描述")
    args = parser.parse_args()

    cfg = load_config()
    client = client_from_config(cfg)
    wid = args.workitem_id.strip()

    r = client._request("GET", client._projex(f"/workitems/{wid}"))
    desc = r.get("description") or ""

    def name_of(v):
        if isinstance(v, dict):
            return v.get("name") or v.get("id")
        return v

    print(f"ID        : {r.get('id')}")
    print(f"编号      : {r.get('serialNumber')}")
    print(f"标题      : {r.get('subject')}")
    print(f"状态      : {name_of(r.get('status'))}")
    print(f"负责人    : {name_of(r.get('assignedTo'))}")
    print(f"验证者    : {name_of(r.get('verifier'))}")
    print(f"创建时间  : {r.get('gmtCreate')}")
    print(f"描述图片数: {desc.count('![')}")
    if args.full:
        print("----- 描述 -----")
        print(desc)


if __name__ == "__main__":
    main()
