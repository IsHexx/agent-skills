---
name: menu-module-sheet-grouper
description: Extract multi-level headings from a requirement document (Markdown .md), remove heading rows containing 查询条件/弹窗字段/校验规则/列表字段/功能按钮 (and their descendants), then concatenate menu paths and output an Excel workbook (.xlsx) with merged-path sheets and per-module (一级标题) grouped sheets for task assignment.
---

# Menu Module Sheet Grouper（菜单路径模块分组）

## Quick Start

1. Install dependency:
   - `pip install openpyxl`
2. Generate output workbook from a requirement Markdown:
   - `python scripts/req_md_menu_sheet_grouper.py --md <需求文档.md> --prefix <前缀可选>`

Output defaults to: `<input>__菜单路径模块分组.xlsx`

## What It Produces

For a given requirement Markdown:

- `合并路径(含细项)`: merged full paths, **including** detail headings
- `合并路径`: merged full paths, **filtered** (drops detail segments and their descendants)
- `模块-<一级标题>`: per-module grouped paths (filtered; module = first segment)
- `模块汇总`: module → count → sheet name

Detail segments dropped by default:
- `列表字段`、`功能按钮`、`查询条件`、`弹窗字段`、`校验规则`

## Usage Patterns

### Process a single requirement Markdown

- `python scripts/req_md_menu_sheet_grouper.py --md 005_记账/01-需求/需求文档/记账报税-第二部分.md --prefix 记账平台-财务`

### Customize filtered “detail segments”

- Add more segments to drop:
  - `python scripts/req_md_menu_sheet_grouper.py --md <file.md> --detail-segment 列表操作 --detail-segment 导出字段 --keep-default-detail-segments`
- If you provide any `--detail-segment` without `--keep-default-detail-segments`, it **replaces** defaults.

### In-place (not recommended)

- Use `--out-xlsx` to control output path. The script does not modify the source `.md`.

## Notes / Constraints

- Excel sheet names are limited to 31 characters; the script will sanitize/truncate and ensure uniqueness.
- The script deduplicates merged paths while preserving first-seen order.
- Default extraction scope is under the first heading that contains `功能详细说明` (configurable via `--scope-heading-contains`).
