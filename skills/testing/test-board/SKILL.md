---
name: test-board
version: 1.0.0
description: 根据用户输入的人员分工或任务排期描述，自动更新测试任务总表并重新生成人员任务看板（HTML/Excel）。
author: YiNian
tags: [testing, 看板, 任务管理, excel]
---

# 测试看板

根据用户输入的人员分工或任务排期描述，自动更新测试任务总表并重新生成人员任务看板（HTML/Excel）。

## 调用方式

用户在当前目录（`D:\财宝\部门\人员分工表`）输入任务分工描述时自动触发。

该 skill 为全局 skill，存放于 `D:\agent-skills\skills\testing\test-board\SKILL.md`。

## 输入示例

- “周杰和蒲波 7月17~7月22 财宝系统数据检查问题复现验证”
- “张林和曾璐 测试执行 记_08_【出纳流水映射导入excel】 测试到7月21结束”
- “系_05_【...缓存】 暂时搁置不排期”
- “徐浩 7月16 1、xxx 2、yyy 3、zzz”
- “记_09 写用例加一天”

## 执行步骤

1. **读取源表**
   - 源文件：`测试管理甘特图_测试部门统一任务总表.xlsx`
   - 同步目标：`人员看板系统/data/测试管理甘特图_测试部门统一任务总表.xlsx`

2. **解析用户意图**
   从自然语言中提取：
   - 任务名称/关键词（如 税_07、记_08、财宝系统数据检查等）
   - 负责人姓名（周杰、蒲波、张霖湘、徐浩、张林、曾璐等）
   - 时间表达（7月17~7月22、7/20和7/21、到7月21结束、写用例2天等）
   - 操作类型：新增、调整时间、调整负责人、取消排期、删除任务

3. **更新源表**
   - 通过任务编号或标题关键词匹配现有任务
   - 若不存在则新增一行，自动分配任务编号（TEST2026-XXXX，取当前最大+1）
   - 更新字段：负责人、当前状态、预计提测时间、用例开始时间、用例结束时间、计划开始时间、计划完成时间、备注
   - 状态映射：
     - 正在做/进行中/同时在做 → 进行中
     - 待开始/还没做/准备做 → 待开始
     - 暂时搁置/不排/取消/去掉排期 → 待排期
     - 已完成/已上线 → 已完成（尽量不修改历史已上线任务）

## 依赖脚本

本 skill 依赖随附的 Python 脚本，位于 skill 目录下：

- `scripts/generate_person_task_board.py` — 读取测试任务总表，生成人员任务看板 HTML/Excel
- `scripts/templates/person_task_board.html` — HTML 看板模板

脚本支持全局调用：无论从哪个工作目录执行，默认读取当前目录下的 `测试管理甘特图_测试部门统一任务总表.xlsx`，输出到当前工作目录根下。

### 用法示例

在项目目录执行：

```bash
python D:\agent-skills\skills\testing\test-board\scripts\generate_person_task_board.py \
  --input 测试管理甘特图_测试部门统一任务总表.xlsx \
  --output 人员任务看板.html \
  --excel-output 人员任务看板.xlsx
```

或直接执行默认参数（读取当前目录源表，输出到当前目录根下）：

```bash
python D:\agent-skills\skills\testing\test-board\scripts\generate_person_task_board.py
```

4. **生成看板**
   执行看板生成脚本，确保看板文件生成在当前工作目录根下：

   ```bash
   python D:\agent-skills\skills\testing\test-board\scripts\generate_person_task_board.py \
     --input 测试管理甘特图_测试部门统一任务总表.xlsx \
     --output 人员任务看板.html \
     --excel-output 人员任务看板.xlsx
   ```

   ```bash
   python D:\agent-skills\skills\testing\test-board\scripts\generate_person_task_board.py
   ```

5. **验证与汇报**
   - 检查生成的 `人员任务看板.xlsx` 中目标人员行是否包含新任务
   - 确认 HTML 看板包含最新排期
   - 向用户汇报：修改/新增的任务、关键人员时间线、已生成文件、任务总数

## 字段规则

| 用户描述 | 字段映射 |
|---|---|
| 测试执行 / 做某任务 / 开始到X结束 | 计划开始时间 ~ 计划完成时间 |
| 写用例 N 天 | 用例开始时间 ~ 用例结束时间 |
| 测试到 X 结束 | 计划完成时间 = X，开始时间根据上下文或备注推断 |
| 加一天 / 延长 | 在原有结束日期上 +1 天 |
| 暂时搁置 / 不排 | 清空计划/用例/预计提测时间，状态改为“待排期” |
| 同时在做 | 同一时间段内允许并行任务，新增独立任务行 |

## 输出要求

- 使用中文汇报
- 列出修改/新增的任务表格
- 列出关键人员时间线
- 列出已更新的文件路径
- 说明任务总数变化
