---
name: feishu-native-kb-export
description: Export authorized Feishu/Lark wiki knowledge-base branches to local folders using the browser's native download/export flows while preserving the wiki tree structure. Use when the user wants a whole Feishu wiki or subtree saved locally, especially when Doc pages should be exported as Word, Sheets as local Excel .xlsx, Bitable as Excel/CSV download, and file nodes as their original attachments.
---

# Feishu Native KB Export

Use this skill only when the user is authorized and already logged in to the target Feishu/Lark workspace in a local browser. Reuse that logged-in session via Playwright CDP; do not bypass login or tenant permissions.

## Workflow

1. Confirm prerequisites.
2. Enumerate the target wiki branch into a node manifest.
3. Export each node with the correct browser-native path by object type.
4. Save outputs under a root folder that mirrors the wiki tree.
5. Write `meta.json` per node and a root `manifest.json` for auditing.

## Prerequisites

- A usable Chromium session is already logged in to Feishu/Lark.
- A CDP endpoint is available, for example `ws://127.0.0.1:55156/devtools/browser/...`.
- `playwright` is installed in the working directory or otherwise available to Node.js.
- Use the bundled scripts in `scripts/`. If they are missing from the current workspace, copy them from this skill first.

## Scripts

- `scripts/enumerate_feishu_branch_playwright.js`
  - Recursively walks a wiki branch and writes a flat JSON manifest of nodes.
- `scripts/export_feishu_kb_playwright.js`
  - Exports each node according to `obj_type` and preserves the tree in local folders.

## Enumerate A Branch

Set the required environment variables:

```powershell
$env:FEISHU_CDP_URL='ws://127.0.0.1:55156/devtools/browser/<id>'
$env:FEISHU_ROOT_WIKI_TOKEN='ABR9w88X6in90vkUw4acEDAanvf'
$env:FEISHU_ENUM_OUTPUT=(Resolve-Path '.').Path + '\branch_nodes.json'
node .\scripts\enumerate_feishu_branch_playwright.js
```

The output JSON is the authoritative export manifest. Keep it.

## Export Rules By Object Type

  - `obj_type=22`: open wiki/doc page and use `... -> <doc word export menu>`, save `.docx`
  - `obj_type=3`: open Sheet page and use `... -> <sheet xlsx export menu>`, save `.xlsx`
  - `obj_type=8`: open Bitable page and use `... -> <bitable xlsx export menu>`, save `.xlsx`
- `obj_type=12`: file node
  - Prefer direct `下载` button when present
  - Fallback to `... -> 下载`
  - Save the browser's suggested filename unchanged except for Windows-invalid characters

For unknown types, extend the script conservatively after probing the live UI.

## Run Full Export

```powershell
$env:FEISHU_CDP_URL='ws://127.0.0.1:55156/devtools/browser/<id>'
$env:FEISHU_NODE_MANIFEST=(Resolve-Path '.\branch_nodes.json').Path
$env:FEISHU_OUTPUT_ROOT=(Resolve-Path '.').Path + '\Feishu_native_export'
node .\scripts\export_feishu_kb_playwright.js
```

The exporter writes:

- tree-preserved exported files
- `meta.json` inside each node folder
- root `manifest.json`

## Validation

Check export counts:

```powershell
$m = Get-Content -Raw -LiteralPath '.\Feishu_native_export\manifest.json' | ConvertFrom-Json
$m | Group-Object export_mode | Sort-Object Name | Format-Table Count,Name -AutoSize
$m | Where-Object { $_.export_mode -eq 'failed' }
```

Expected modes from the current script:

- `playwright_word_export`
- `playwright_sheet_xlsx_export`
- `playwright_bitable_xlsx_export`
- `playwright_file_download`

## Notes

- Preserve existing export folders unless the user explicitly wants a clean rerun.
- If a node fails, record it in `meta.json` and continue the batch; do not abort the whole export.
- Prefer browser-native export over reconstructed Markdown when the user wants the closest result to the original knowledge base structure.
- For non-copyable page extraction rather than native export, the separate `feishu-docx-extractor` skill is the better fit.
