#!/usr/bin/env python
"""更新已有云效缺陷的标题（合并缺陷、扩大影响范围时用）。

用法：
    python update_subject.py --workitem-id <缺陷ID> --subject "新的缺陷标题"
    python update_subject.py --workitem-id <缺陷ID> --subject "..." --dry-run

说明：
    update_workitem 是**部分更新**语义，本脚本只提交 subject，描述/负责人/验证者
    等字段不会受影响（对比 append_evidence.py 走的是「原描述 + 追加」的覆盖式更新）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yunxiao_client import YunxiaoApiError, load_config, client_from_config


def main():
    parser = argparse.ArgumentParser(description="更新已有云效缺陷的标题")
    parser.add_argument("--workitem-id", required=True, help="缺陷/工作项 ID")
    parser.add_argument("--subject", required=True, help="新的标题")
    parser.add_argument("--dry-run", action="store_true", help="只打印将改成的标题，不提交")
    args = parser.parse_args()

    cfg = load_config()
    client = client_from_config(cfg)
    wid = args.workitem_id.strip()
    new_subject = args.subject.strip()

    detail = client._request("GET", client._projex(f"/workitems/{wid}"))
    old_subject = detail.get("subject") or ""
    print(f"原标题: {old_subject}")
    print(f"新标题: {new_subject}")

    if args.dry_run:
        print("（dry-run，未提交）")
        return

    try:
        client.update_workitem(wid, subject=new_subject)
    except YunxiaoApiError as e:
        print(f"更新失败: {e}")
        sys.exit(1)
    print(f"缺陷 {wid} 标题已更新")


if __name__ == "__main__":
    main()
