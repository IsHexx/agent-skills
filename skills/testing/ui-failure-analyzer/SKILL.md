---
name: ui-failure-analyzer
description: 失败分析 Skill。对 UI 自动化回归执行失败做第一轮归因，区分环境问题/用例问题/真实 Bug，减少 QA 人工检查失败的数量。当回归测试出现失败需要自动归因分析时使用。
---

# ui-failure-analyzer

失败分析 Skill。对回归执行失败做第一轮归因，减少 QA 需要人工检查的失败数量。

> 执行失败不能直接认为是 Bug。AI 首先回答「为什么失败」，而不是「是不是 Bug」。

## 输入

```text
测试用例（test-cases/）
测试代码（tests/generated/）
ui-elements.csv
Error Stack
Trace（reports/artifacts/ 下的 trace.zip，用 Trace Viewer 查看）
Screenshot
Console 日志
Network 请求
执行报告（reports/report.html）
```

## 失败分类（六类，统一定义）

| 分类 | 含义 | 下一步动作 |
| --- | --- | --- |
| AUTOMATION_ERROR | 自动化代码自身问题 | AI 修复测试代码并重跑 |
| ELEMENT_CHANGED | 页面元素发生变化 | 调用 ui-element-builder 增量维护元素库 |
| TEST_DATA_ERROR | 测试数据问题 | 提示修复测试数据 |
| ENVIRONMENT_ERROR | 测试环境问题 | 提示检查环境 |
| PRODUCT_BUG | 疑似产品 Bug | 生成疑似 Bug 报告，交 QA 确认 |
| UNKNOWN | AI 暂时无法准确判断 | 交 QA 人工判断 |

## 分析示例

```text
测试步骤：点击「保存」
执行结果：等待 30 秒没有找到按钮
元素库：customer.save_button
历史 Locator：get_by_role('button', name='保存')
当前页面 Snapshot：button "提交"

判断：ELEMENT_CHANGED（可能是 UI 文案变更，confidence: high）
```

## AI 可以自动修

- Playwright 语法错误、公共方法调用错误
- 等待方式问题、Fixture 使用问题
- 已经确认过的 Locator 变更（仅技术定位变化，不涉及业务语义）
- 测试框架自身问题

修复后自动重跑。

## AI 绝对不能自动修改

业务测试步骤、预期结果、Assertion、业务规则、权限结果、状态结果、
金额结果、财税业务计算结果。

> AI 可以修自动化实现，不能修改 QA 定义的业务正确性。

## PRODUCT_BUG 输出格式

```text
疑似Bug

用例ID / 用例名称 / 模块 / 失败步骤
前置条件 / 操作步骤 / 预期结果 / 实际结果
Screenshot / Trace / Console异常 / Network异常
失败时间 / AI判断依据
```

之后流程：QA 人工确认 → 确认 Bug → 调用 Bug Skill → 测试管理平台 → 通知开发。
不是 Bug 则回到修正用例 / 数据 / 自动化。
