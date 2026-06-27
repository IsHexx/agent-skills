---
name: regression-test-planner
description: Create comprehensive production regression test plans with flow diagrams, business branch diagrams, and staffing tables. Use when: (1) designing regression tests for large systems, (2) creating multi-path flowcharts with color-coded swimlanes, (3) generating Draw.io diagrams following progressive disclosure principles, (4) building xlsx assignment tables with color differentiation by module/path, (5) defining end-to-end test scenarios across dependent modules.
---

# Regression Test Planner

## Overview

This skill enables you to create production-grade regression test plans for complex systems. It provides:

1. **Markdown Test Plan** — Structured documentation covering scope, data, workflows, risks, and scheduling
2. **Main Flow Diagram** (Draw.io) — Progressive disclosure design showing entry → prep → common layer → path split → swimlanes → convergence → verification → exit
3. **Business Branch Diagrams** (Draw.io) — Multi-page diagrams covering state machines, decision logic, and edge cases
4. **Assignment Table** (xlsx) — Color-coded by module/path, with work estimation and priority levels

## When to Use This Skill

- **Designing system-wide test coverage** for multi-phase releases
- **Creating flowcharts with swimlane layouts** and color-coded execution paths
- **Applying progressive disclosure** (overview first, then details)
- **Building structured test plans** that reference existing templates and best practices
- **Generating repeatable test artifacts** (diagrams, tables) across similar projects

## Core Workflow

### Step 1: Read Requirement Documents

Gather source materials:
- Functional requirement specs (modules, features, workflows)
- Existing reference diagrams (e.g., `记账回归测试流程图.drawio`, `回归测试人员分工表.xlsx`)
- Test environment info (URLs, platforms, roles)

### Step 2: Generate Markdown Test Plan

See [test-plan-template.md](references/test-plan-template.md) for the standard structure:
- Project background
- Test scope (platforms, modules, features)
- Test data (use cases, accounts, data construction)
- Test flow (strategy, end-to-end paths, defect logging)
- Risk assessment
- Schedule
- Progress sync mechanisms

### Step 3: Create Main Flow Diagram (Draw.io)

Use the progressive disclosure pattern from [drawio-patterns.md](references/drawio-patterns.md):

**Structure:**
- **Entry** (ellipse) → **Prep layer** (parallel nodes) → **Common layer** (swimlane) → **Path split** (diamond)
- **Execution paths** (A, B, C swimlanes in different colors)
- **Convergence** (purple node) → **Verification boxes** (semi-transparent, one per path)
- **Exit** (ellipse) with **Path D dashed box** (independent operations)

**Color scheme:**
- Path A (green `#d5e8d4`) — Office staff entry + tax bureau login
- Path B (orange `#FFE6CC`) — Invoice collection
- Path C (blue `#dae8fc`) — Zero declaration + reporting
- Path D (red `#f8cecc`, dashed) — Operations platform (independent)
- Common/entry/exit (gray `#F5F5F5`)
- Convergence (purple `#e1d5e7`)

**Key principle:** First glance should show the main flow clearly. Details appear in swimlane node labels and annotations.

### Step 4: Create Business Branch Diagrams (Draw.io)

Multi-page diagram (10+ pages) covering:
1. RPA task state machine
2. Tax bureau login state flow
3. Office staff capture & sync states
4. Invoice capture status flow
5. Tax calculation branches (by taxpayer type)
6. Tax confirmation state flow
7. Zero declaration judgment logic
8. Reporting flow (phase 2)
9. Assistant app redirection logic
10. Exception handling paths

See [drawio-patterns.md](references/drawio-patterns.md) for state machine and branching patterns.

### Step 5: Generate Assignment Table (xlsx)

Use [xlsx-generation.md](references/xlsx-generation.md) for structure and coloring:

**Sheet 1: 回归测试分工表**
- Columns: Phase (merged) | Menu/Function | Function Points | Owner | Est. Days | Priority | Notes
- Color-coded rows by module/path (A/B/C/D lines)
- Fixed header formatting

**Sheet 2: 工作量汇总**
- Summary by owner with totals

Use the Python template in `scripts/gen_xlsx_template.py` to generate with proper formatting.

## Practical Example

**Task:** "Create regression test plan for tax system covering 3 modules with parallel testing"

**Process:**

1. Read requirement document (features, workflows, environment info)
2. Identify parallel execution paths:
   - Path A: Office staff setup → Tax bureau login verification
   - Path B: Invoice collection → Tax calculation
   - Path C: Zero declaration → Reporting
   - Path D (independent): Operations platform management
3. Generate Markdown plan referencing test-plan-template.md
4. Create main flowchart:
   - Entry → Parallel prep (operations config + RPA client)
   - Common layer (robot groups, management, task monitoring)
   - Split into 3 paths via diamond
   - Each path as swimlane with color
   - Converge → Verification → Exit
   - Path D as red dashed box on right
5. Create business branch diagram with state machines and decision trees
6. Generate xlsx with color coding (green for Path A, orange for B, blue for C, red for D, gray for common)

## Resources

### scripts/

**gen_xlsx_template.py** — Python script for generating color-coded xlsx files.

Features:
- Merge cells for phase grouping
- Custom fonts and alignment
- Color fills by module/path
- Border styling
- Two-sheet structure (main table + summary)

Run: `python scripts/gen_xlsx_template.py --config <config.yaml>`

### references/

**test-plan-template.md** — Standard markdown structure for regression test plans. Includes all required sections with guidance.

**drawio-patterns.md** — Draw.io mxGraph XML patterns for:
- Swimlane structure and styling
- Color-coded nodes by path
- Entry/exit shapes
- State machine diagrams
- Decision diamond patterns
- Dashed boxes for independent operations

**xlsx-generation.md** — Spreadsheet design patterns with:
- Column layout and widths
- Header formatting
- Row coloring by module/path
- Merged cell strategy
- Two-sheet structure

## Tips for Quality Output

1. **Progressive disclosure:** Main diagram should be understandable at a glance. Details in swimlane node labels.
2. **Color consistency:** Use the standard color palette across all diagrams and tables.
3. **Reference templates:** Always check existing diagrams in your project for style consistency before creating new ones.
4. **State machines:** For complex workflows, break them into separate pages in business branch diagram, one per module.
5. **Defect tracking:** Link to your organization's bug tracking system (Cloud Effectiveness/Jira/Linear) in the test plan.
6. **Data isolation:** Emphasize test data naming conventions and cleanup in the plan document.

