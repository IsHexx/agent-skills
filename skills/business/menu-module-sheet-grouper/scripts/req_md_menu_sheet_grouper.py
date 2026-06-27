import argparse
import os
import re
from collections import defaultdict

import openpyxl


DEFAULT_DETAIL_SEGMENTS = ["列表字段", "功能按钮", "查询条件", "弹窗字段", "校验规则"]


HEADING_RE = re.compile(r"^\s*(?:\d+\.\s*)?(#{1,6})\s+(.+?)\s*$")
NUM_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)(?:\.)?\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*```")
LOCATION_LINE_RE = re.compile(r"^\s*-\s*(.+?)\s*$")


def _read_text_best_effort(path: str) -> str:
    # Chinese Windows often uses GBK, but most exported Markdown is UTF-8.
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _sanitize_sheet_name(name: str) -> str:
    name = re.sub(r"[:\\/?*\[\]]", "_", name).strip()
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


def _get_or_reset_sheet(wb: openpyxl.Workbook, name: str) -> openpyxl.worksheet.worksheet.Worksheet:
    if name in wb.sheetnames:
        ws = wb[name]
        if ws.max_row:
            ws.delete_rows(1, ws.max_row)
        return ws
    return wb.create_sheet(name)


def _split_path(path_value: str) -> list[str]:
    return [p.strip() for p in path_value.split(" - ") if p and p.strip()]


def _write_paths_sheet(ws, header: str, paths: list[str]) -> None:
    ws.cell(1, 1, header)
    for i, v in enumerate(paths, start=2):
        ws.cell(i, 1, v)
    ws.column_dimensions["A"].width = 90


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def extract_heading_paths(
    *,
    md_text: str,
    scope_heading_contains: str | None,
    detail_segments: set[str],
) -> tuple[list[list[str]], list[list[str]]]:
    """
    Return (raw_paths, clean_paths), where each path is a list of heading titles.

    - raw_paths: includes all headings under scope
    - clean_paths: drops headings containing detail segments and their descendants
    """
    in_fence = False
    in_scope = scope_heading_contains is None

    stack: list[tuple[int, str]] = []

    raw: list[list[str]] = []
    clean: list[list[str]] = []
    dropped_level: int | None = None

    for line in md_text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if scope_heading_contains and not in_scope:
            # Scope marker in these exported docs might not be a Markdown heading.
            if scope_heading_contains in line:
                in_scope = True
                stack = []
                dropped_level = None
            continue

        if not in_scope:
            continue

        level = None
        title = None

        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
        else:
            m2 = NUM_HEADING_RE.match(line)
            if m2 and not m2.group(2).lstrip().startswith("#"):
                idx = m2.group(1)
                level = len(idx.split("."))
                title = m2.group(2).strip()

        if level is None or title is None:
            continue

        # pop to parent level
        while stack and stack[-1][0] >= level:
            stack.pop()

        # Update drop state when moving up
        if dropped_level is not None and level <= dropped_level:
            dropped_level = None

        stack.append((level, title))
        path = [t for _, t in stack]
        raw.append(path)

        if dropped_level is not None:
            continue

        if any(seg in title for seg in detail_segments):
            dropped_level = level
            continue

        clean.append(path)

    return raw, clean


def extract_location_paths(
    *,
    md_text: str,
    scope_heading_contains: str | None,
    root_prefixes: tuple[str, ...] = ("业务平台", "记账系统"),
) -> list[list[str]]:
    """
    Extract menu paths from bullet lines typically found under '位置' sections, e.g.:
    - 业务平台 - 财务-记账管理
    - 记账系统-设置-账套设置

    Returns list of segments, split by '-' after normalizing separators/spaces.
    """
    in_fence = False
    in_scope = scope_heading_contains is None

    paths: list[list[str]] = []

    for line in md_text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if scope_heading_contains and not in_scope:
            if scope_heading_contains in line:
                in_scope = True
            continue
        if not in_scope:
            continue

        m = LOCATION_LINE_RE.match(line)
        if not m:
            continue

        content = m.group(1).strip()
        if not content:
            continue

        # Only accept likely menu paths (reduce false positives from generic bullets).
        if not any(content.startswith(p) for p in root_prefixes):
            continue
        if "-" not in content and "－" not in content:
            continue

        normalized = content.replace("－", "-")
        normalized = re.sub(r"\s*-\s*", "-", normalized)
        segments = [s.strip() for s in normalized.split("-") if s and s.strip()]
        if len(segments) < 2:
            continue

        paths.append(segments)

    return paths


def default_out_path(md_path: str) -> str:
    root, _ = os.path.splitext(md_path)
    return f"{root}__菜单路径模块分组.xlsx"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract headings from a requirement Markdown, filter detail headings, then output merged paths and per-module sheets to Excel.",
    )
    parser.add_argument("--md", required=True, help="Input requirement Markdown (.md)")
    parser.add_argument("--out-xlsx", default=None, help="Output .xlsx path (default: <input>__菜单路径模块分组.xlsx)")
    parser.add_argument(
        "--mode",
        choices=("auto", "headings", "location"),
        default="auto",
        help="Extraction mode: headings (parse title hierarchy), location (parse '位置' bullet menu paths), auto (prefer location when present).",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Optional prefix to prepend to merged paths (e.g., 记账平台-财务). If omitted, do not add a prefix.",
    )
    parser.add_argument(
        "--scope-heading-contains",
        default="功能详细说明",
        help="Only extract headings under the first heading containing this text. Use empty string to disable.",
    )
    parser.add_argument(
        "--detail-segment",
        action="append",
        default=[],
        help="Heading keywords to drop (repeatable). If omitted, uses defaults unless --keep-default-detail-segments is set.",
    )
    parser.add_argument(
        "--keep-default-detail-segments",
        action="store_true",
        help="Keep default drop keywords and append any provided --detail-segment values.",
    )

    args = parser.parse_args()

    md_path = args.md
    if not os.path.exists(md_path):
        raise SystemExit(f"Input not found: {md_path}")

    out_xlsx = args.out_xlsx or default_out_path(md_path)
    prefix = args.prefix
    add_prefix = bool(prefix and prefix.strip())
    if add_prefix:
        prefix = prefix.strip()

    segs = [s.strip() for s in args.detail_segment if s and s.strip()]
    if args.keep_default_detail_segments:
        segs = DEFAULT_DETAIL_SEGMENTS + [s for s in segs if s not in DEFAULT_DETAIL_SEGMENTS]
    elif not segs:
        segs = DEFAULT_DETAIL_SEGMENTS

    scope_contains = args.scope_heading_contains
    if scope_contains is not None and scope_contains.strip() == "":
        scope_contains = None

    text = _read_text_best_effort(md_path)
    detail_set = set(segs)

    used_mode = args.mode
    if args.mode in ("auto", "location"):
        location_paths = extract_location_paths(
            md_text=text,
            scope_heading_contains=scope_contains,
        )
        if args.mode == "location" or (args.mode == "auto" and len(location_paths) >= 5):
            used_mode = "location"
            raw_paths = location_paths
            clean_paths = [
                p
                for p in location_paths
                if not any(any(seg in part for seg in detail_set) for part in p)
            ]
        else:
            used_mode = "headings"
            raw_paths, clean_paths = extract_heading_paths(
                md_text=text,
                scope_heading_contains=scope_contains,
                detail_segments=detail_set,
            )
    else:
        raw_paths, clean_paths = extract_heading_paths(
            md_text=text,
            scope_heading_contains=scope_contains,
            detail_segments=detail_set,
        )

    # Convert to merged strings
    if add_prefix:
        raw_merged = _dedupe_preserve_order([" - ".join([prefix] + p) for p in raw_paths if p])
        clean_merged = _dedupe_preserve_order([" - ".join([prefix] + p) for p in clean_paths if p])
        module_index = 1
    else:
        raw_merged = _dedupe_preserve_order([" - ".join(p) for p in raw_paths if p])
        clean_merged = _dedupe_preserve_order([" - ".join(p) for p in clean_paths if p])
        module_index = 0

    wb = openpyxl.Workbook()
    # remove default empty sheet
    wb.remove(wb.active)

    ws_raw = wb.create_sheet(_unique_sheet_name(wb, "合并路径(含细项)"))
    _write_paths_sheet(ws_raw, "合并路径", raw_merged)

    ws_clean = wb.create_sheet(_unique_sheet_name(wb, "合并路径"))
    _write_paths_sheet(ws_clean, "合并路径", clean_merged)

    # Group by first segment after prefix (module)
    grouped: dict[str, list[str]] = defaultdict(list)
    for v in clean_merged:
        parts = _split_path(v)
        module = parts[module_index] if len(parts) > module_index else "未分类"
        grouped[module].append(v)

    summary = wb.create_sheet(_unique_sheet_name(wb, "模块汇总"))
    summary.cell(1, 1, "模块")
    summary.cell(1, 2, "数量")
    summary.cell(1, 3, "Sheet")
    summary.column_dimensions["A"].width = 18
    summary.column_dimensions["B"].width = 10
    summary.column_dimensions["C"].width = 26

    row = 2
    for module in sorted(grouped.keys()):
        sheet_name = _unique_sheet_name(wb, f"模块-{module}")
        ws_m = wb.create_sheet(sheet_name)
        _write_paths_sheet(ws_m, "合并路径", _dedupe_preserve_order(grouped[module]))

        summary.cell(row, 1, module)
        summary.cell(row, 2, len(_dedupe_preserve_order(grouped[module])))
        summary.cell(row, 3, sheet_name)
        row += 1

    wb.save(out_xlsx)
    print(f"OK: {out_xlsx}")
    print(f"- mode: {used_mode}")
    print(f"- raw: {len(raw_merged)}")
    print(f"- clean: {len(clean_merged)}")
    print(f"- modules: {len(grouped)}")


if __name__ == "__main__":
    main()
