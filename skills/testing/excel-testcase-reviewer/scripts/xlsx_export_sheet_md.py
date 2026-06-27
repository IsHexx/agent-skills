import argparse
from typing import List

import openpyxl

from xlsx_lib import REQUIRED_COLUMNS, find_header, iter_case_rows


def _md_escape(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("|", "\\|")
    s = s.replace("\n", "<br>")
    return s


def _render_table(rows: List[List[str]]) -> str:
    lines = []
    header = rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a testcase sheet to Markdown table")
    parser.add_argument("--xlsx", required=True, help="Path to .xlsx")
    parser.add_argument("--sheet", required=True, help="Sheet name")
    parser.add_argument("--max-rows", type=int, default=0, help="Limit exported data rows (0 = no limit)")
    parser.add_argument("--out", default="", help="Output .md path (default stdout)")
    args = parser.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, data_only=True)
    ws = wb[args.sheet]
    header = find_header(ws)
    if not header:
        raise SystemExit(f"Header not found in sheet: {args.sheet}")

    rows: List[List[str]] = [REQUIRED_COLUMNS]
    count = 0
    for _, row in iter_case_rows(ws, header):
        data = [_md_escape(row.get(c, "")) for c in REQUIRED_COLUMNS]
        rows.append(data)
        count += 1
        if args.max_rows and count >= args.max_rows:
            break

    md = _render_table(rows)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
            f.write("\n")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

