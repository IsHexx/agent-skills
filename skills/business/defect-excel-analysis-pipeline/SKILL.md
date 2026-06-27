---
name: defect-excel-analysis-pipeline
description: Generate defect analysis reports from raw defect export Excel files (.xlsx/.xls). Use when asked to clean/standardize a defects workbook into the same structure as 签单_合同--2026-01-07.xlsx (a 'work items' sheet with 标题/负责人/严重程度 plus a Sheet1 table), then run scripts to output an analysis workbook like 签单_合同--2026-01-07_缺陷分析.xlsx (按模块统计, 按严重级别统计, 人员x严重级别). Supports mapping accounting modules via 记账模块分工.xls and re-evaluating severities with a large model (OpenAI API) with per-row 调整理由.
---

## Workflow

### 0) One-command pipeline (recommended)

```powershell
$env:OPENAI_API_KEY="..."
python -m defect_analyzer.pipeline --input "<原始缺陷.xlsx>" --module-map "记账模块分工.xls" --adjust-severity llm
```

### 1) Standardize input workbook

Run in the repo that contains `defect_analyzer/` (e.g. `D:\\code\\TestDataAnlysie`):

```powershell
python -m defect_analyzer.clean --input "<原始缺陷.xlsx>" --output "<项目_日期>_标准化.xlsx" --module-map "记账模块分工.xls"
```

Output workbook layout:

- `work items` sheet: `标题`, `负责人`, `严重程度`
- `Sheet1` sheet: `序号`, `缺陷等级`, `所属模块`, `BUG标题`, `负责人`

### 2) Generate analysis workbook (reference-format)

If severity should be re-evaluated by a large model, require `OPENAI_API_KEY`:

```powershell
$env:OPENAI_API_KEY="..."
python -m defect_analyzer --input "<项目_日期>_标准化.xlsx" --output "<项目_日期>_缺陷分析.xlsx" --adjust-severity llm
```

If you do NOT want model-based severity adjustments:

```powershell
python -m defect_analyzer --input "<项目_日期>_标准化.xlsx" --output "<项目_日期>_缺陷分析.xlsx" --adjust-severity off
```

Generated sheets (matches the reference summary format, with an extra detail sheet for adjustments):

- `按模块统计`
- `按严重级别统计`
- `人员x严重级别`
- `缺陷明细(含调整)`（当发生严重级别调整时写入 `调整理由`）

### 3) Quick sanity check (optional)

```powershell
python - <<'PY'
import openpyxl
wb=openpyxl.load_workbook("<项目_日期>_缺陷分析.xlsx", data_only=True)
print(wb.sheetnames)
for s in ["按模块统计","按严重级别统计","人员x严重级别"]:
    ws=wb[s]
    print(s, ws.max_row, ws.max_column, [ws.cell(1,c).value for c in range(1, ws.max_column+1)])
PY
```

## Notes

- `--adjust-severity auto` only enables `llm` when the input filename contains “记账” and `OPENAI_API_KEY` is set; otherwise it stays `off`.
- Module mapping uses `记账模块分工.xls` (Sheet1/列名 `模块名称`) to map bracket-extracted module tokens to a standardized module path.
