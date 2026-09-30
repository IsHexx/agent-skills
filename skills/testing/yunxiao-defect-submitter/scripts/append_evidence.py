#!/usr/bin/env python
"""给已有云效缺陷追加补充说明与截图（不新建缺陷）。

用法：
    python append_evidence.py --workitem-id <缺陷ID> --note "补充现象说明" [--image 路径 ...]
    python append_evidence.py --workitem-id <缺陷ID> --note "..." --image a.png --image b.png

行为：
    1. GET 现有工作项，取出 description；
    2. 逐张上传图片并取得内嵌链接；
    3. 在描述末尾追加「### 补充说明（YYYY-MM-DD）」小节 + 说明文字 + 图片；
    4. PUT 覆盖式更新（原描述内容完整保留，不会丢失）。

注意：update_workitem 是覆盖式更新，本脚本始终以「原描述 + 追加内容」落库，
并且**必须显式带 `formatType="MARKDOWN"`**，否则云效会把描述按富文本
（RICHTEXT）存储，页面上 `## 【…】`、`**加粗**` 会变成字面量（BMGT-1790 案例）。
若原描述本身就是富文本 JSON（页面手写的），脚本会中止，需回页面补充。
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yunxiao_client import YunxiaoApiError, load_config, client_from_config


def main():
    parser = argparse.ArgumentParser(description="给已有云效缺陷追加补充说明与截图")
    parser.add_argument("--workitem-id", required=True, help="缺陷/工作项 ID")
    parser.add_argument("--note", required=True, help="补充说明文字（支持 \\n 换行）")
    parser.add_argument("--image", action="append", default=[], help="截图路径，可重复传入")
    parser.add_argument("--dry-run", action="store_true", help="只预览将写入的描述，不更新")
    args = parser.parse_args()

    cfg = load_config()
    client = None
    if not args.dry_run:
        try:
            client = client_from_config(cfg)
        except YunxiaoApiError as e:
            print(e)
            sys.exit(1)

    wid = args.workitem_id.strip()

    # 1. 取现有描述（dry-run 也需要，故用只读请求）
    reader = client or client_from_config(cfg)
    detail = reader._request("GET", reader._projex(f"/workitems/{wid}"))
    old_desc = (detail.get("description") or "").rstrip()
    if not old_desc:
        print(f"警告：缺陷 {wid} 当前描述为空，将直接写入补充说明。")

    # 云效页面里手写的描述是以富文本（RICHTEXT）存 JSON 的，直接追加 markdown
    # 会把原内容破坏掉，这种情况中止并让用户回页面里改。
    if str(detail.get("formatType") or "").upper() == "RICHTEXT" and old_desc.lstrip().startswith("{"):
        print(f"中止：缺陷 {wid} 的描述是云效富文本（RICHTEXT/JSON）存储的，"
              f"用本脚本追加 markdown 会破坏原描述。")
        print("请在云效页面上手动补充说明。")
        sys.exit(1)

    # 2. 上传图片
    embeds = []
    for p in args.image:
        path = Path(p)
        if not path.exists():
            print(f"截图文件不存在：{p}")
            sys.exit(1)
        if args.dry_run:
            embeds.append(f"![{path.name}](<dry-run 未上传>)")
            continue
        att = reader.upload_attachment(wid, path.read_bytes(), path.name)
        embeds.append(att.get("embedMarkdown") or f"![{path.name}]({att.get('embedUrl')})")

    # 3. 组装追加内容
    block = [f"### 补充说明（{date.today().isoformat()}）", args.note.replace("\\n", "\n").strip()]
    if embeds:
        block.append("")
        block.extend(embeds)
    new_desc = (old_desc + "\n\n" + "\n".join(block)).strip()

    if args.dry_run:
        print("===== 将写入的描述 =====")
        print(new_desc)
        return

    # 4. 覆盖式更新（必须显式带 formatType）
    #    不传 formatType 时云效按默认富文本落库，formatType 变成 RICHTEXT，
    #    页面上会把 ## 【…】、**加粗** 这些 markdown 标记原样显示成字面量 —— 
    #    BMGT-1790 就是这么被写坏的（2026-09-29）。
    reader.update_workitem(wid, description=new_desc, formatType="MARKDOWN")
    print(f"补充说明已追加到缺陷 {wid}（新增 {len(embeds)} 张截图）")


if __name__ == "__main__":
    main()
