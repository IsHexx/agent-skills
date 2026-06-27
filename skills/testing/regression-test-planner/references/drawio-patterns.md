# Draw.io Flow Diagram Patterns

## Table of Contents
1. [Main Flow Structure](#main-flow-structure)
2. [Color Scheme](#color-scheme)
3. [XML Patterns](#xml-patterns)
4. [State Machine Patterns](#state-machine-patterns)
5. [Decision Diamond Patterns](#decision-diamond-patterns)
6. [Dashed Box Pattern (Independent Operations)](#dashed-box-pattern)

---

## Main Flow Structure

### Progressive Disclosure Design

**First impression (at any zoom):** Reader immediately understands the main flow
- Entry → Preparation → Common layer → Split → Execution paths → Convergence → Verification → Exit

**Second level (focused viewing):** Reader sees path names and node labels explaining what happens in each swimlane

**Third level (detail hovering):** Reader can see description annotations (small gray text) in node labels

### Recommended Canvas Size
- **Width:** 1800px
- **Height:** 1200px
- **Grid:** 10px (helps with alignment)

### Standard Page Structure (top to bottom)

1. **Title** (20px from top)
   - Font: 18pt bold, centered
   - Color: Dark gray/black
   - No background

2. **Legend** (60-245px from top)
   - Border box on left side (30px from left, 200px wide)
   - Color swatches matching path colors
   - Legend font: 10pt normal

3. **Entry node** (70px from top, centered)
   - Ellipse shape
   - 160×50px size
   - Label: "开始回归测试" or similar

4. **Prep layer** (160px from top)
   - Two nodes in parallel (580-800px left, 1000-1220px left)
   - Light yellow background (#fff2cc)
   - 220×55px size

5. **Common layer swimlane** (260px from top)
   - Width: 940px, Height: 100px
   - Light gray background (#f5f5f5)
   - Contains 4-5 submodules

6. **Split diamond** (390px from top, centered)
   - Diamond shape, 160×70px
   - Light gray background
   - Label: "按业务线分工执行"

7. **Execution paths (A/B/C swimlanes)** (500px from top)
   - Three side-by-side swimlanes
   - Each 380×340px
   - Colors: Green/Orange/Blue
   - Each contains 6-8 nodes

8. **Convergence node** (880px from top, centered)
   - Rounded rectangle
   - 280×50px
   - Purple background (#e1d5e7)
   - Label: "汇聚 — 全链路闭环验证"

9. **Verification boxes** (970px from top)
   - Four boxes (A/B/C/D paths)
   - Each 200×55px
   - Semi-transparent (opacity=50)
   - Colors matching their paths

10. **Exit node** (1070px from top, centered)
    - Ellipse, 240×60px
    - Light gray background
    - Label: "回归测试完成"

11. **Path D dashed box** (120px from top, right side at 1440px)
    - Swimlane with dashed border
    - Red color (#b85450), 2px stroke
    - 310×700px
    - Contains 8-10 independent operation nodes
    - Dashed arrow from bottom of box to exit

---

## Color Scheme

### Standard Colors

| Path/Element | Color | Hex Code | Usage |
|--------------|-------|----------|-------|
| Path A | Green | `#d5e8d4` | Office staff entry + tax bureau login |
| Path B | Orange | `#FFE6CC` | Invoice collection |
| Path C | Blue | `#dae8fc` | Zero declaration + reporting |
| Path D | Red | `#f8cecc` | Operations platform (dashed) |
| Common/Entry/Exit | Gray | `#F5F5F5` | Non-colored elements |
| Convergence | Purple | `#e1d5e7` | Merge point |
| Prep | Light Yellow | `#fff2cc` | Preparation nodes |

### Stroke Colors

Match fill color for consistency:
- Path A stroke: `#82b366`
- Path B stroke: `#d79b00`
- Path C stroke: `#6c8ebf`
- Path D stroke: `#b85450` (with dashed=1)
- Gray elements stroke: `#666666` or `#999999`

---

## XML Patterns

### Node Patterns

#### Ellipse Entry/Exit Node
```xml
<mxCell id="entry" value="开始回归测试"
  style="ellipse;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontSize=13;fontStyle=1;"
  parent="1" vertex="1">
  <mxGeometry x="820" y="70" width="160" height="50" as="geometry" />
</mxCell>
```

#### Swimlane
```xml
<mxCell id="path_a" value="A线：办税员录入 + 票税登录"
  style="swimlane;startSize=26;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1;fontSize=12;"
  parent="1" vertex="1">
  <mxGeometry x="100" y="500" width="380" height="340" as="geometry" />
</mxCell>
```

Key swimlane attributes:
- `startSize=26` — Height of title bar
- `fillColor` — Background (lighter shade of path color)
- `strokeColor` — Border (darker shade matching path)
- `fontStyle=1` — Bold for swimlane title
- `fontSize=12` — Slightly larger

#### Node within Swimlane
```xml
<mxCell id="a1" value="新增办税员"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;"
  parent="path_a" vertex="1">
  <mxGeometry x="30" y="40" width="140" height="36" as="geometry" />
</mxCell>
```

#### Edge (Arrow)
```xml
<mxCell id="a1_2" edge="1" source="a1" target="a2" parent="path_a">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

#### Dashed Edge
```xml
<mxCell id="d_to_exit" value=""
  style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#b85450;exitX=0;exitY=1;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
  edge="1" source="path_d_box" target="exit" parent="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

#### Dashed Swimlane (Path D)
```xml
<mxCell id="path_d_box" value="D线：运营平台管理（独立）"
  style="swimlane;startSize=26;fillColor=none;strokeColor=#b85450;strokeWidth=2;dashed=1;fontStyle=1;fontSize=12;fontColor=#b85450;"
  parent="1" vertex="1">
  <mxGeometry x="1440" y="120" width="310" height="700" as="geometry" />
</mxCell>
```

Key dashed box attributes:
- `fillColor=none` — No background fill
- `strokeColor=#b85450` — Red border
- `strokeWidth=2` — Thicker border
- `dashed=1` — Dashed style
- `fontColor=#b85450` — Red title text

#### Description Annotation (Gray text)
```xml
<mxCell id="a1s" value="凭证单 / 科目检索&#xa;借贷校验 / 外币 / 附件"
  style="text;html=1;align=left;verticalAlign=top;fontSize=9;fontColor=#555;strokeColor=none;fillColor=none;"
  parent="path_a" vertex="1">
  <mxGeometry x="170" y="28" width="160" height="32" as="geometry" />
</mxCell>
```

#### Semi-transparent Node (Verification box)
```xml
<mxCell id="verify_a" value="✓ 路径A验证&#xa;办税员→票税登录→RPA回调"
  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;opacity=50;fontSize=10;"
  parent="1" vertex="1">
  <mxGeometry x="430" y="970" width="200" height="55" as="geometry" />
</mxCell>
```

---

## State Machine Patterns

### Simple State Transition Diagram

**Use for:** Single module state flow (login states, document status, etc.)

**Pattern:**
```
State 1 → State 2 → State 3
  ↓
[Exception] → Error State
```

**Node styles:**
- Circle or rounded rectangle for states
- Arrow with label for transitions
- Diamond for decision points (if/else branches)

**Colors:**
- Normal state: Light gray or path color
- Error state: Light red (#ffcccc)
- Terminal state: Light green (#ccffcc)

### Example: Tax Bureau Login States
```
未维护 → 未登录 → 登录验证中 → 登录在线
           ↓
        登录异常 → [Manual fix required]
           ↓
        重新验证 → 登录在线
```

---

## Decision Diamond Patterns

### Single Decision Point
```xml
<mxCell id="split" value="按业务线分工执行"
  style="rhombus;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=11;fontStyle=1;"
  parent="1" vertex="1">
  <mxGeometry x="820" y="390" width="160" height="70" as="geometry" />
</mxCell>
```

**Outputs:**
- Label edges with path names (A线, B线, C线)
- Each leads to corresponding swimlane

### Complex Decision Tree

**Use for:** Multi-level branching (taxpayer type → invoice type → calculation method)

**Pattern:**
```
Decision 1 (diamond)
  ├→ Path A → Decision 2a → Output A1, A2
  ├→ Path B → Decision 2b → Output B1, B2
  └→ Path C → Output C
```

**Colors:**
- Use path colors for branches (consistent with swimlanes)
- Green for "true" paths, red for "false" when applicable

---

## Dashed Box Pattern

### Purpose
Highlight operations that run independently, not blocking the main flow.

### Structure
```xml
<mxCell id="path_d_box"
  style="swimlane;startSize=26;fillColor=none;strokeColor=#b85450;strokeWidth=2;dashed=1;..."
  parent="1" vertex="1">
  <mxGeometry x="1440" y="120" width="310" height="700" as="geometry" />
</mxCell>
```

**Key attributes:**
- `fillColor=none` — Transparent background
- `dashed=1` — Dashed border (not solid)
- `strokeWidth=2` — Double line width for visibility
- Red color (#b85450) — Signals independent/alternative path

### Connection to Main Flow
- Dashed edge from bottom of box
- Use `dashed=1` on the edge too
- Same red color (#b85450)
- `edgeStyle=orthogonalEdgeStyle` — For clean right angles

### Example Connection
```xml
<mxCell id="d_to_exit" value=""
  style="edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#b85450;"
  edge="1" source="path_d_box" target="exit" parent="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

---

## Layout Tips

### Alignment
- Use 10px grid (`gridSize=10`)
- Snap nodes to grid for clean appearance
- Center titles in swimlanes

### Spacing
- Swimlane height: 320-360px for 6-8 nodes
- Node height: 28-50px (taller for descriptions)
- Vertical spacing between rows: 10-30px
- Horizontal swimlane spacing: 10-20px

### Readability
- Keep node labels short (2-3 words + parenthetical details)
- Place description annotations to right of node (9pt gray text)
- Use bold (`fontStyle=1`) only for titles and key nodes
- Keep text centered in nodes (`align=center`)

