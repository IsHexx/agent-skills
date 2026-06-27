import argparse
import re
from typing import Dict, List, Tuple

import openpyxl

from xlsx_lib import REQUIRED_COLUMNS, compute_max_tc_id, find_header


def _split_md_row(line: str) -> List[str]:
    # Split a markdown table row by unescaped pipes.
    # Assumes row looks like: | a | b | c |
    s = line.strip()
    if not s.startswith("|") or "|" not in s[1:]:
        return []
    # remove leading/trailing pipe
    if s.endswith("|"):
        s = s[1:-1]
    else:
        s = s[1:]
    cells: List[str] = []
    cur = []
    escaped = False
    for ch in s:
        if escaped:
            cur.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    cells.append("".join(cur).strip())
    return [c.replace("<br>", "\n") for c in cells]


def _parse_markdown_table(md_text: str) -> Tuple[List[str], List[Dict[str, str]]]:
    lines = [ln for ln in md_text.splitlines() if ln.strip()]
    table_lines = [ln for ln in lines if ln.strip().startswith("|")]
    if len(table_lines) < 2:
        raise ValueError("Markdown 中未找到表格（至少需要表头与分隔行）")

    header = _split_md_row(table_lines[0])
    sep = table_lines[1]
    if not re.search(r"\|\s*-", sep):
        raise ValueError("Markdown 表格缺少分隔行（| --- |）")

    rows: List[Dict[str, str]] = []
    for ln in table_lines[2:]:
        cells = _split_md_row(ln)
        if not cells:
            continue
        # tolerate extra cells by truncation; missing cells become empty
        if len(cells) < len(header):
            cells = cells + [""] * (len(header) - len(cells))
        row = {header[i]: cells[i] for i in range(len(header))}
        rows.append(row)
    return header, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Append Markdown testcase table rows into an .xlsx sheet")
    parser.add_argument("--xlsx", required=True, help="Path to .xlsx")
    parser.add_argument("--sheet", required=True, help="Target sheet name")
    parser.add_argument("--md", required=True, help="Path to markdown file containing the table")
    parser.add_argument(
        "--id-mode",
        choices=["keep", "auto"],
        default="keep",
        help="keep: use 编号 from markdown; auto: overwrite 编号 with next TC-xxx from workbook max",
    )
    args = parser.parse_args()

    with open(args.md, "r", encoding="utf-8") as f:
        md_text = f.read()

    header, md_rows = _parse_markdown_table(md_text)
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise SystemExit(f"Markdown 表头缺少必备列：{missing}")

    wb = openpyxl.load_workbook(args.xlsx)
    if args.sheet in wb.sheetnames:
        ws = wb[args.sheet]
    else:
        ws = wb.create_sheet(args.sheet)

    header_info = find_header(ws)
    if not header_info:
        # create header at row 1
        for i, col in enumerate(REQUIRED_COLUMNS, start=1):
            ws.cell(1, i).value = col
        header_info = find_header(ws)
        if not header_info:
            raise SystemExit("无法创建/识别表头，请检查工作表结构")

    # Determine append start row (first empty after existing content in required columns)
    start_row = ws.max_row + 1
    # But if sheet is new with only header, start at 2
    if ws.max_row == header_info.row:
        start_row = header_info.row + 1

    next_id = compute_max_tc_id(wb) + 1 if args.id_mode == "auto" else None

    for i, r in enumerate(md_rows):
        excel_row = start_row + i
        for col_name in REQUIRED_COLUMNS:
            col_idx = header_info.col_map[col_name]
            v = (r.get(col_name, "") or "").replace("\\|", "|").strip()
            if col_name == "编号" and args.id_mode == "auto":
                v = f"TC-{next_id:03d}"
            ws.cell(excel_row, col_idx).value = v
        if args.id_mode == "auto":
            next_id += 1

    wb.save(args.xlsx)
    print(f"Appended {len(md_rows)} row(s) into {args.xlsx} sheet '{args.sheet}' (id-mode={args.id_mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

