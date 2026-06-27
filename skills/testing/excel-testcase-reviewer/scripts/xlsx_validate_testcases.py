import argparse
import json
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import openpyxl

from xlsx_lib import REQUIRED_COLUMNS, find_header, iter_case_rows, parse_tc_id


def _count_numbered_items(text: str) -> int:
    # Count "1." / "1、" / "1)" patterns at line starts.
    if not text:
        return 0
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) >= 2 and line[0].isdigit() and line[1] in {".", "、", ")"}:
            count += 1
            continue
        # 10. / 12、 etc
        if len(line) >= 3 and line[:2].isdigit() and line[2] in {".", "、", ")"}:
            count += 1
            continue
    return count


def validate_workbook(xlsx_path: str, sheet: str | None, enforce_sequential: bool) -> Dict[str, Any]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheets = [sheet] if sheet else wb.sheetnames

    report: Dict[str, Any] = {
        "xlsx": xlsx_path,
        "sheet_scope": sheet or "ALL",
        "errors": [],
        "warnings": [],
        "sheets": {},
    }

    id_locations: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for sheet_name in sheets:
        ws = wb[sheet_name]
        header = find_header(ws)
        sheet_report: Dict[str, Any] = {
            "header_row": header.row if header else None,
            "missing_columns": [],
            "row_count": 0,
            "error_rows": 0,
            "warning_rows": 0,
        }

        if not header:
            report["warnings"].append(
                {"type": "missing_header", "sheet": sheet_name, "message": "未找到包含必备列的表头行"}
            )
            report["sheets"][sheet_name] = sheet_report
            continue

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in header.col_map]
        if missing_cols:
            sheet_report["missing_columns"] = missing_cols
            report["errors"].append(
                {"type": "missing_columns", "sheet": sheet_name, "columns": missing_cols, "message": "表头缺少必备列"}
            )
            report["sheets"][sheet_name] = sheet_report
            continue

        seen_nums: List[int] = []
        last_num = None

        for row_idx, row in iter_case_rows(ws, header):
            sheet_report["row_count"] += 1
            row_errors: List[Dict[str, Any]] = []
            row_warnings: List[Dict[str, Any]] = []

            # Required fields non-empty
            for col in REQUIRED_COLUMNS:
                if not row.get(col, "").strip():
                    row_errors.append({"type": "empty_required", "column": col, "message": f"必填列为空：{col}"})

            # ID format
            tc_id = row.get("编号", "")
            n = parse_tc_id(tc_id) if tc_id else None
            if tc_id and n is None:
                row_errors.append({"type": "invalid_id", "column": "编号", "message": "编号不符合 TC-数字 格式"})
            if tc_id:
                id_locations[tc_id].append((sheet_name, row_idx))

            # Priority range
            p = row.get("优先级", "")
            if p and p not in {"P0", "P1", "P2", "P3"}:
                row_errors.append({"type": "invalid_priority", "column": "优先级", "message": "优先级必须为 P0/P1/P2/P3"})

            # Preconditions should contain 3 categories (heuristic warning)
            pre = row.get("前置条件", "")
            if pre and _count_numbered_items(pre) < 3:
                row_warnings.append(
                    {
                        "type": "preconditions_maybe_incomplete",
                        "column": "前置条件",
                        "message": "前置条件建议同时包含：系统状态/权限配置/数据准备（至少 3 条）",
                    }
                )

            # Sequential check (optional)
            if enforce_sequential and n is not None:
                if last_num is not None and n != last_num + 1:
                    row_errors.append(
                        {
                            "type": "non_sequential_id",
                            "column": "编号",
                            "message": f"编号非连续递增：上一条为 TC-{last_num:03d}，当前为 {tc_id}",
                        }
                    )
                last_num = n
                seen_nums.append(n)

            if row_errors:
                sheet_report["error_rows"] += 1
                report["errors"].append({"sheet": sheet_name, "row": row_idx, "issues": row_errors})
            if row_warnings:
                sheet_report["warning_rows"] += 1
                report["warnings"].append({"sheet": sheet_name, "row": row_idx, "issues": row_warnings})

        report["sheets"][sheet_name] = sheet_report

    # Duplicated IDs across scanned scope
    dups = {tc_id: locs for tc_id, locs in id_locations.items() if len(locs) > 1}
    for tc_id, locs in dups.items():
        report["errors"].append(
            {
                "type": "duplicate_id",
                "id": tc_id,
                "locations": [{"sheet": s, "row": r} for s, r in locs],
                "message": "编号重复（要求唯一）",
            }
        )

    report["summary"] = {
        "error_count": len(report["errors"]),
        "warning_count": len(report["warnings"]),
        "duplicate_id_count": len(dups),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate testcase workbook (.xlsx) basic constraints")
    parser.add_argument("--xlsx", required=True, help="Path to .xlsx")
    parser.add_argument("--sheet", default=None, help="Only validate a single sheet name")
    parser.add_argument("--enforce-sequential", action="store_true", help="Error if IDs are not strictly sequential")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report = validate_workbook(args.xlsx, args.sheet, args.enforce_sequential)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"XLSX: {report['xlsx']}")
        print(f"Scope: {report['sheet_scope']}")
        print(f"Errors: {report['summary']['error_count']}, Warnings: {report['summary']['warning_count']}")
        if report["summary"]["duplicate_id_count"]:
            print(f"Duplicate IDs: {report['summary']['duplicate_id_count']}")
        if report["errors"]:
            print("First 10 errors:")
            for e in report["errors"][:10]:
                if e.get("type") == "duplicate_id":
                    print(f"- duplicate_id {e['id']} @ {e['locations']}")
                elif "row" in e:
                    print(f"- {e['sheet']}!row {e['row']}: {len(e['issues'])} issue(s)")
                else:
                    print(f"- {e}")

    return 1 if report["summary"]["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

