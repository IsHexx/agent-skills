# Excel/XLSX Generation Patterns

## Table of Contents
1. [Sheet Structure](#sheet-structure)
2. [Color Scheme](#color-scheme)
3. [Column Layout](#column-layout)
4. [Formatting Specifications](#formatting-specifications)
5. [Python Implementation Guide](#python-implementation-guide)

---

## Sheet Structure

### Sheet 1: 回归测试分工表 (Assignment Table)

**Purpose:** Assign test modules to team members with resource estimates

**Columns:**
- **A** — 阶段 (Phase/Stage) — Merged for grouped rows
- **B** — 菜单/功能 (Menu/Function)
- **C** — 功能要点 (Function Points / Key Features)
- **D** — 负责人 (Owner/Tester Name)
- **E** — 计划天数 (Estimated Days)
- **F** — 优先级 (Priority: P0/P1/P2)
- **G** — 备注 (Notes)

**Rows:** Group by testing phase/path:
1. **入口 (Entry)** — 1-2 rows, gray background
2. **公共层 (Common Layer)** — 4-5 rows, gray background
3. **A线 (Path A)** — 5-7 rows, green background
4. **B线 (Path B)** — 4-6 rows, orange background
5. **C线 (Path C)** — 7-8 rows, blue background
6. **汇聚 (Convergence)** — 1 row, gray background
7. **出口 (Exit)** — 1 row, gray background
8. **D线 (Path D - Independent)** — 8-10 rows, red background

**Total rows:** ~40-45 data rows (excluding header)

### Sheet 2: 工作量汇总 (Work Summary)

**Purpose:** Summary by owner showing total days and module count

**Columns:**
- **A** — 负责人 (Owner Name)
- **B** — 模块 (Module / Scope)
- **C** — 计划天数 (Total Estimated Days)
- **D** — 菜单数 (Number of Test Menus)
- **E** — 备注 (Notes)

**Rows:**
- One row per tester (A, B, C, D)
- One row for full-team tasks (Entry, Convergence, Exit)
- One final row showing totals (ALL, sum, sum, sum)

**Total rows:** 6-8 data rows

---

## Color Scheme

### Path Colors (matching Draw.io diagrams)

| Path/Section | Hex Code | RGB | Usage |
|--------------|----------|-----|-------|
| Path A | `#d5e8d4` | 213, 232, 212 | Light green |
| Path B | `#FFE6CC` | 255, 230, 204 | Light orange |
| Path C | `#dae8fc` | 218, 232, 252 | Light blue |
| Path D | `#f8cecc` | 248, 206, 204 | Light red/pink |
| Common/Entry/Exit | `#F5F5F5` | 245, 245, 245 | Light gray |
| Header | `#2F5597` | 47, 85, 151 | Dark blue |

### Application Rules
- **Header row:** Dark blue background with white text (bold)
- **Title row:** Dark blue background, spans all columns, white text (larger font)
- **Data rows:** Color fill matching the phase/path group
- **Alternating rows:** Optional (normally not used, single color per group)
- **Borders:** Thin gray borders around all cells

---

## Column Layout

### Column Widths

| Column | Width (chars) | Purpose |
|--------|---------------|---------|
| A | 16 | Phase name (merged cells) |
| B | 22 | Module/menu name |
| C | 38 | Detailed function points |
| D | 12 | Owner name |
| E | 10 | Estimated days |
| F | 10 | Priority level |
| G | 26 | Additional notes |

### Row Heights

| Row Type | Height (pt) | Purpose |
|----------|------------|---------|
| Title | 36 | Main document title |
| Header | 22 | Column headers |
| Data | 32 | Regular data rows |
| Summary | 28 | Summary/total rows |

---

## Formatting Specifications

### Fonts

**Default Font:** 微软雅黑 (Microsoft YaHei) 10pt

| Element | Font | Size | Bold | Color |
|---------|------|------|------|-------|
| Title | YaHei | 14 | Yes | White |
| Header | YaHei | 11 | Yes | White |
| Data | YaHei | 10 | No | Black |
| Section label (Phase A, B, etc) | YaHei | 11 | Yes | Black |

### Alignment

| Column | Horizontal | Vertical |
|--------|-----------|----------|
| A (Phase) | Center | Center |
| B (Menu) | Left | Center |
| C (Points) | Left | Top |
| D (Owner) | Center | Center |
| E (Days) | Center | Center |
| F (Priority) | Center | Center |
| G (Notes) | Left | Center |

**Text wrapping:** Enabled for columns B, C, G (allow multi-line)

### Borders

**Border style:** Thin (0.75pt), gray color (#BFBFBF)

**Apply to:** All cells in data range (A2:G[last_row])

**Special:**
- Slightly thicker borders around phase groups (optional)
- None around merged phase column (A)

### Merged Cells

**Phase column (A):**
- Group rows by phase
- Merge all rows belonging to same phase
- Example: A3:A6 for "公共层" phase (4 rows grouped)
- Centered both horizontally and vertically

### Row Freeze

**Freeze panes at:** B3 (first column and first two rows stay visible when scrolling)

---

## Python Implementation Guide

### Required Library
```python
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
```

### Function: Create Colored Cell

```python
def create_cell(ws, row, col, value, bg_color, font_bold=False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.fill = PatternFill("solid", fgColor=bg_color)
    cell.font = Font(name="微软雅黑", bold=font_bold, size=10)
    cell.border = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF")
    )
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return cell
```

### Function: Merge Phase Cells

```python
def merge_phase_cells(ws, phase_name, start_row, end_row):
    ws.merge_cells(f"A{start_row}:A{end_row}")
    cell = ws.cell(row=start_row, column=1, value=phase_name)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.font = Font(name="微软雅黑", bold=True, size=11)
```

### Function: Create Header Row

```python
def create_header(ws, headers, row=2):
    for col, header_text in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header_text)
        cell.fill = PatternFill("solid", fgColor="2F5597")
        cell.font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF")
        )
    ws.row_dimensions[row].height = 22
```

### Complete Example Structure

```python
# 1. Create workbook and select active sheet
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "回归测试分工表"

# 2. Set column widths
column_widths = {"A": 16, "B": 22, "C": 38, "D": 12, "E": 10, "F": 10, "G": 26}
for col, width in column_widths.items():
    ws.column_dimensions[col].width = width

# 3. Create title row
ws.merge_cells("A1:G1")
title_cell = ws["A1"]
title_cell.value = "税务系统生产环境回归测试分工表"
title_cell.fill = PatternFill("solid", fgColor="2F5597")
title_cell.font = Font(name="微软雅黑", bold=True, size=14, color="FFFFFF")
title_cell.alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 36

# 4. Create header row
headers = ["阶段", "菜单/功能", "功能要点", "负责人", "计划天数", "优先级", "备注"]
create_header(ws, headers, row=2)

# 5. Add data rows with color fills
color_map = {
    "A线": "#d5e8d4",
    "B线": "#FFE6CC",
    "C线": "#dae8fc",
    "D线": "#f8cecc",
    "common": "#F5F5F5"
}

row = 3
for data_row in data_list:
    phase, menu, points, owner, days, priority, notes, color = data_row
    # Create cells...

# 6. Freeze panes
ws.freeze_panes = "B3"

# 7. Save
wb.save("output.xlsx")
```

---

## Tips for Data Input

### Format for Phase Column (Column A)

When multiple rows belong to same phase, use the phase name with `\n` for wrapping:
```python
"A线\n（办税员+票税登录）"
"B线\n（发票采集）"
```

This allows long names to display across 2 lines within single merged cell.

### Priority Values
- "P0" — Must execute 100%
- "P1" — Risk assessment required
- "P2" — Lower priority (optional)

### Work Estimation (Column E)
- Express in decimal days (e.g., "1.5", "2.0", "0.5")
- Assume 1 person, 1 day = 6-8 hours actual work
- For complex modules, estimate by task complexity (not number of menu items)

### Owner Names
- Use consistent naming across sheets
- Example: "测试人员A", "测试人员B" (then replace with real names)
- Or real names if available

