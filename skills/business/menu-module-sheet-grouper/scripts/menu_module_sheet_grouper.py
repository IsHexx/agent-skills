import argparse
import os
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass

import openpyxl


DEFAULT_DETAIL_SEGMENTS = ["列表字段", "功能按钮", "查询条件", "弹窗字段", "校验规则"]


@dataclass(frozen=True)
class SheetProcessResult:
    table_sheet: str
    prefix: str
    raw_count: int
    clean_count: int
    dropped_count: int
    module_counts: dict[str, int]


def _split_path(value: str) -> list[str]:
    # Delimiter is " - " (space-hyphen-space) in our artifacts.
    return [p.strip() for p in value.split(" - ") if p and str(p).strip()]


def _should_drop(value: str, detail_segments: set[str]) -> bool:
    return any(part in detail_segments for part in _split_path(value))


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


_INVALID_SHEET_CHARS = re.compile(r"[:\\/?*\[\]]")


def _sanitize_sheet_name(name: str) -> str:
    name = _INVALID_SHEET_CHARS.sub("_", name).strip()
    return name or "Sheet"


def _unique_sheet_name(wb: openpyxl.Workbook, desired: str) -> str:
    desired = _sanitize_sheet_name(desired)
    if len(desired) > 31:
        desired = desired[:31]
    if desired not in wb.sheetnames:
        return desired
    base = desired[:28] if len(desired) > 28 else desired
    for i in range(1, 1000):
        cand = f"{base}-{i}"
        if len(cand) > 31:
            cand = cand[:31]
        if cand not in wb.sheetnames:
            return cand
    raise RuntimeError(f"Unable to find unique sheet name for {desired!r}")


def _preferred_sheet_name(wb: openpyxl.Workbook, desired: str) -> str:
    """
    Prefer a deterministic name (overwrite if already exists).

    If the sanitized/truncated desired name already exists, return it.
    Otherwise, return a unique variant.
    """
    desired = _sanitize_sheet_name(desired)
    if len(desired) > 31:
        desired = desired[:31]
    if desired in wb.sheetnames:
        return desired
    return _unique_sheet_name(wb, desired)


def _get_or_reset_sheet(wb: openpyxl.Workbook, name: str) -> openpyxl.worksheet.worksheet.Worksheet:
    if name in wb.sheetnames:
        ws = wb[name]
        if ws.max_row:
            ws.delete_rows(1, ws.max_row)
        return ws
    return wb.create_sheet(name)


def _find_header_indices(
    header_row: list[object],
    *,
    module_header: str = "一级菜单",
    merge_headers: tuple[str, ...] = ("合并路径(不含前缀)", "合并路径"),
) -> tuple[int | None, int | None]:
    module_idx = None
    merge_idx = None

    for i, v in enumerate(header_row, start=1):
        if isinstance(v, str) and v.strip() == module_header:
            module_idx = i
        if isinstance(v, str) and v.strip() in merge_headers:
            merge_idx = i
    return module_idx, merge_idx


def _detect_table_sheets(
    wb: openpyxl.Workbook,
    *,
    forced_sheet: str | None,
) -> list[str]:
    if forced_sheet:
        if forced_sheet not in wb.sheetnames:
            raise SystemExit(f"--table-sheet not found: {forced_sheet!r}. Available: {wb.sheetnames}")
        return [forced_sheet]

    detected: list[str] = []
    for name in wb.sheetnames:
        ws = wb[name]
        header = [ws.cell(1, c).value for c in range(1, min(20, ws.max_column) + 1)]
        module_idx, merge_idx = _find_header_indices(header)
        if module_idx is not None and merge_idx is not None:
            detected.append(name)
    return detected


def process_workbook(
    *,
    xlsx_path: str,
    out_xlsx_path: str,
    table_sheet: str | None,
    detail_segments: list[str],
    keep_default_detail_segments: bool,
) -> list[SheetProcessResult]:
    if not os.path.exists(xlsx_path):
        raise SystemExit(f"Input not found: {xlsx_path}")

    if os.path.abspath(out_xlsx_path) != os.path.abspath(xlsx_path):
        shutil.copy2(xlsx_path, out_xlsx_path)

    wb = openpyxl.load_workbook(out_xlsx_path)

    targets = _detect_table_sheets(wb, forced_sheet=table_sheet)
    if not targets:
        raise SystemExit(
            "No menu table sheets detected. "
            "Expected header to contain '一级菜单' and '合并路径(不含前缀)' (or '合并路径'). "
            "Use --table-sheet to force processing."
        )

    segs = [s.strip() for s in detail_segments if s and s.strip()]
    if keep_default_detail_segments:
        segs = DEFAULT_DETAIL_SEGMENTS + [s for s in segs if s not in DEFAULT_DETAIL_SEGMENTS]
    elif not segs:
        segs = DEFAULT_DETAIL_SEGMENTS

    detail_set = set(segs)

    results: list[SheetProcessResult] = []

    for sheet_name in targets:
        ws = wb[sheet_name]
        prefix = sheet_name

        header = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        module_col, merge_col = _find_header_indices(header)
        if module_col is None or merge_col is None:
            raise SystemExit(f"Sheet {sheet_name!r} does not match expected header format.")

        raw_paths: list[str] = []
        clean_paths: list[str] = []
        dropped = 0
        module_paths: dict[str, list[str]] = defaultdict(list)

        for r in range(2, ws.max_row + 1):
            merge_rel = ws.cell(r, merge_col).value
            if isinstance(merge_rel, str) and merge_rel.strip():
                rel = merge_rel.strip()
            else:
                # Fallback: join first 4 menu levels if merge column is empty.
                parts = []
                for c in range(1, min(4, ws.max_column) + 1):
                    v = ws.cell(r, c).value
                    if isinstance(v, str) and v.strip():
                        parts.append(v.strip())
                if not parts:
                    continue
                rel = " - ".join(parts)

            full_path = f"{prefix} - {rel}"
            raw_paths.append(full_path)

            if _should_drop(full_path, detail_set):
                dropped += 1
                continue

            clean_paths.append(full_path)

            module_value = ws.cell(r, module_col).value
            module_name = module_value.strip() if isinstance(module_value, str) and module_value.strip() else "未分类"
            module_paths[module_name].append(full_path)

        raw_paths = _ordered_unique(raw_paths)
        clean_paths = _ordered_unique(clean_paths)

        raw_sheet_name = _preferred_sheet_name(wb, f"{prefix}-合并(含细项)")
        clean_sheet_name = _preferred_sheet_name(wb, f"{prefix}-合并")

        raw_ws = _get_or_reset_sheet(wb, raw_sheet_name)
        raw_ws.cell(1, 1, "合并路径")
        for i, v in enumerate(raw_paths, start=2):
            raw_ws.cell(i, 1, v)
        raw_ws.column_dimensions["A"].width = 90

        clean_ws = _get_or_reset_sheet(wb, clean_sheet_name)
        clean_ws.cell(1, 1, "合并路径")
        for i, v in enumerate(clean_paths, start=2):
            clean_ws.cell(i, 1, v)
        clean_ws.column_dimensions["A"].width = 90

        module_counts: dict[str, int] = {}
        module_sheet_names: dict[str, str] = {}

        for module_name, paths in sorted(module_paths.items(), key=lambda x: x[0]):
            paths = _ordered_unique(paths)
            module_counts[module_name] = len(paths)

            desired = f"{prefix}-模块-{module_name}"
            # Best-effort to keep meaning under Excel 31-char limit.
            if len(_sanitize_sheet_name(desired)) > 31:
                desired = f"模块-{module_name}"
            module_sheet_name = _preferred_sheet_name(wb, desired)
            module_sheet_names[module_name] = module_sheet_name

            mws = _get_or_reset_sheet(wb, module_sheet_name)
            mws.cell(1, 1, "合并路径")
            for i, v in enumerate(paths, start=2):
                mws.cell(i, 1, v)
            mws.column_dimensions["A"].width = 90

        summary_name = _preferred_sheet_name(wb, f"{prefix}-模块汇总")
        sws = _get_or_reset_sheet(wb, summary_name)
        sws.cell(1, 1, "模块")
        sws.cell(1, 2, "数量")
        sws.cell(1, 3, "Sheet")
        row = 2
        for module_name in sorted(module_counts.keys()):
            sws.cell(row, 1, module_name)
            sws.cell(row, 2, module_counts[module_name])
            sws.cell(row, 3, module_sheet_names.get(module_name, ""))
            row += 1
        sws.column_dimensions["A"].width = 18
        sws.column_dimensions["B"].width = 10
        sws.column_dimensions["C"].width = 26

        results.append(
            SheetProcessResult(
                table_sheet=sheet_name,
                prefix=prefix,
                raw_count=len(raw_paths),
                clean_count=len(clean_paths),
                dropped_count=dropped,
                module_counts=module_counts,
            )
        )

    wb.save(out_xlsx_path)
    return results


def _default_out_path(xlsx_path: str) -> str:
    root, ext = os.path.splitext(xlsx_path)
    if not ext:
        ext = ".xlsx"
    return f"{root}__模块分组{ext}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate merged menu paths and per-module grouped sheets from a menu-path requirement workbook (.xlsx).",
    )
    parser.add_argument("--xlsx", required=True, help="Input .xlsx menu-path requirement workbook")
    parser.add_argument(
        "--out-xlsx",
        default=None,
        help="Output workbook path (default: <input>__模块分组.xlsx)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Modify the input workbook in-place (not recommended).",
    )
    parser.add_argument(
        "--table-sheet",
        default=None,
        help="Force processing a specific table sheet (auto-detect by default).",
    )
    parser.add_argument(
        "--detail-segment",
        action="append",
        default=[],
        help="Segment names to drop (repeatable). If omitted, uses defaults unless --keep-default-detail-segments is set.",
    )
    parser.add_argument(
        "--keep-default-detail-segments",
        action="store_true",
        help="Keep default drop segments and append any provided --detail-segment values.",
    )

    args = parser.parse_args()

    in_path = args.xlsx
    if args.inplace:
        out_path = in_path
    else:
        out_path = args.out_xlsx or _default_out_path(in_path)

    results = process_workbook(
        xlsx_path=in_path,
        out_xlsx_path=out_path,
        table_sheet=args.table_sheet,
        detail_segments=args.detail_segment,
        keep_default_detail_segments=args.keep_default_detail_segments,
    )

    print(f"OK: {out_path}")
    for r in results:
        modules = ", ".join(f"{k}:{v}" for k, v in sorted(r.module_counts.items(), key=lambda x: x[0]))
        print(
            f"- sheet: {r.table_sheet} | raw:{r.raw_count} clean:{r.clean_count} dropped:{r.dropped_count} | {modules}"
        )


if __name__ == "__main__":
    main()
