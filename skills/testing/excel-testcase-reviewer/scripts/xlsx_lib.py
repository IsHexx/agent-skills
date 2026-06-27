import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

REQUIRED_COLUMNS: List[str] = [
    "编号",
    "目录",
    "优先级",
    "标题",
    "前置条件",
    "步骤描述",
    "预期结果",
    "负责人",
    "用例类型",
]

TC_ID_RE = re.compile(r"^TC-(\d+)$")


@dataclass(frozen=True)
class HeaderInfo:
    row: int
    col_map: Dict[str, int]  # column name -> 1-based column index


def _cell_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def find_header(ws, required_columns: List[str] = REQUIRED_COLUMNS, search_rows: int = 30) -> Optional[HeaderInfo]:
    required_set = set(required_columns)
    for row_idx in range(1, min(search_rows, ws.max_row) + 1):
        seen: Dict[str, int] = {}
        for col_idx in range(1, ws.max_column + 1):
            text = _cell_text(ws.cell(row_idx, col_idx).value)
            if text in required_set and text not in seen:
                seen[text] = col_idx
        if required_set.issubset(seen.keys()):
            return HeaderInfo(row=row_idx, col_map=seen)
    return None


def iter_case_rows(ws, header: HeaderInfo) -> Iterable[Tuple[int, Dict[str, str]]]:
    start = header.row + 1
    for row_idx in range(start, ws.max_row + 1):
        row: Dict[str, str] = {}
        all_empty = True
        for col_name, col_idx in header.col_map.items():
            val = _cell_text(ws.cell(row_idx, col_idx).value)
            row[col_name] = val
            if val:
                all_empty = False
        if all_empty:
            continue
        yield row_idx, row


def parse_tc_id(value: str) -> Optional[int]:
    m = TC_ID_RE.match(value.strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def compute_max_tc_id(wb) -> int:
    max_id = 0
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header = find_header(ws)
        if not header:
            continue
        for _, row in iter_case_rows(ws, header):
            n = parse_tc_id(row.get("编号", ""))
            if n is not None and n > max_id:
                max_id = n
    return max_id

