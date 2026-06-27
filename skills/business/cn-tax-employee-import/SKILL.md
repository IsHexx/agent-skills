---
name: cn-tax-employee-import
description: Extract employee and payroll JSON blocks from Chinese individual income tax export .txt files and write them into matching Excel import workbooks. Use when asked to process files like “员工信息：[...]\n工资信息：[...]”, populate “人员信息采集导入模板.xls”, “工资表模板.xlsx”, or update a field-dictionary style “个税数据库.xlsx”.
---

# Chinese Tax Employee Import

## Workflow

Use `scripts/import_tax_txt.py` for this workflow whenever possible. It handles the fragile parts: parsing the two JSON blocks, preserving Excel data validation in `.xls`, keeping身份证号/手机号 as text, mapping tax enum codes to the import template's Chinese dropdown values, and backing up workbooks before writing.

Run from the folder containing the source `.txt` files and templates:

```powershell
python "$env:USERPROFILE\.codex\skills\cn-tax-employee-import\scripts\import_tax_txt.py" --txt "上海蜀锦汇文化传媒有限公司.txt" "中民国合（四川）科技有限公司.txt" --personnel-template "人员信息采集导入模板.xls"
```

Common modes:

```powershell
# Personnel collection template only
python "<skill>\scripts\import_tax_txt.py" --txt *.txt --personnel-template "人员信息采集导入模板.xls"

# Salary import template only
python "<skill>\scripts\import_tax_txt.py" --txt *.txt --salary-template "工资表模板.xlsx"

# Field-dictionary tax database workbook only
python "<skill>\scripts\import_tax_txt.py" --txt *.txt --tax-db "个税数据库.xlsx"

# All supported outputs in one run
python "<skill>\scripts\import_tax_txt.py" --txt *.txt --personnel-template "人员信息采集导入模板.xls" --salary-template "工资表模板.xlsx" --tax-db "个税数据库.xlsx"
```

Replace `<skill>` with the absolute skill directory if `$env:USERPROFILE` is unavailable.

## Input Format

Each text file must contain:

```text
员工信息：[{...}]

工资信息：[{...}]
```

The script matches salary rows to employee rows by `NSRID`.

## Field Rules

For `人员信息采集导入模板.xls`:

- Write to worksheet `人员信息`.
- Preserve row 1 headers, validation, and formatting.
- Clear old values from row 2 down before writing.
- Map `ZZLX=201` to `居民身份证`.
- Map `GJ=156` to `中国`.
- Map `XB=1/2` to `男/女`.
- Map `RZSGLX=10` to `雇员`.
- Map boolean-like fields such as `SFCJ`, `SFLS`, `SFGL`, `SFKCJCFY` to `是/否`.
- Keep `证件号码`, `手机号码`, bank account, and similar identifier columns as text.

For `工资表模板.xlsx`:

- Write one row per `工资信息` record.
- Merge employee fields from the matching `员工信息` by `NSRID`.
- Clear old rows below the header before writing.
- Use the workbook's existing horizontal headers.

For `个税数据库.xlsx`:

- Treat sheets like `人员表` and `工资薪金表` as field dictionaries where field names are in column A.
- Remove previously generated columns whose row 1 value is `导入数据`.
- Append one generated data column per employee or salary record.
- Populate values where the column A field name matches a source JSON key.

## Validation

After writing, read back the output workbook and report:

- Record count written.
- Names, ID numbers, phone numbers, and employment dates for personnel imports.
- Salary row names, ID numbers, and income values for salary imports.
- Generated data columns for tax database imports.

If Excel COM cannot open `.xls`, report the blocker. Do not replace the `.xls` with `.xlsx` unless the user explicitly accepts that format change.
