---
name: ui-element-builder
description: 元素库建设 Skill。把页面元素沉淀为 element-library/ui-elements.csv 候选元素。当需要在 UI 自动化测试体系中建设/维护页面元素库（识别页面元素、生成或更新 ui-elements.csv）时使用。
---

# ui-element-builder

元素库建设 Skill。负责把页面元素沉淀为 `element-library/ui-elements.csv` 中的候选元素。

> 页面识别只发生在元素库建设和页面发生变化的时候，而不是每条自动化用例生成的时候。

## 输入

1. 目标页面（route 或 URL）
2. 登录信息 / 现有登录状态（fixtures/auth.py 的 storage_state）

## 执行流程

```text
打开页面
  ↓
获取 ARIA Snapshot
  ↓
识别可操作元素（button / textbox / link / combobox / dialog 等）
  ↓
生成候选 Locator
  ↓
Playwright 实际验证（存在性 + 唯一性 + 实际执行一次操作）
  ↓
输出 CSV 候选元素（status=candidate）
  ↓
QA 首次审核确认
  ↓
status=verified，写入 ui-elements.csv
```

## Locator 优先级规范（Python）

```text
推荐：
page.get_by_role(...)
page.get_by_label(...)
page.get_by_test_id(...)
page.get_by_placeholder(...)
page.get_by_text(...)

必要时：
page.locator(css)

最后兜底：
page.locator("xpath=...")
```

要求：**最终写入元素库的 Locator 必须经过实际页面验证**，并记录
`source`（aria_snapshot）与 `last_verified_at`。

## 输出（CSV 候选行）

字段与 `element-library/ui-elements.csv` 表头一致：

```text
module, page_id, page_name, route, element_id, element_name,
element_type, locator_type, locator_value, locator_name,
playwright_locator, status, source, last_verified_at, remark
```

注意：

- `locator_type / locator_value / locator_name` 是运行时的单一事实源，
  `playwright_locator` 列仅作可读展示；
- 公共组件（导航、表格、分页、弹窗、日期选择、上传等）使用 `module=COMMON`，
  各业务页面不重复维护；
- 元素状态只允许：`candidate / verified / invalid / deprecated`。
