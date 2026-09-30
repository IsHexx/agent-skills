---
name: yunxiao-defect-submitter
description: 往云效（Apsara DevOps / Projex）提交缺陷的完整工具包。当用户要提缺陷、发来 bug 截图+描述、要把 Excel/docx/Markdown 里的缺陷批量导入云效，或首次拿到本工具包需要安装配置时使用。覆盖：环境自举安装、令牌与项目配置、AI 对话生成缺陷单（截图内嵌描述）、单条 JSON 创建、Excel 批量导入。
---

# 云效提缺陷工具包

本目录即完整工具包，所有路径均相对于本目录（SKILL.md 所在目录，下称 `<ROOT>`）。

```
<ROOT>/
├── SKILL.md                    ← 本文件（Agent 的安装与使用指引）
├── scripts/
│   ├── yunxiao_client.py       ← OpenAPI 封装（创建/更新/附件/类型/字段/成员搜索）
│   ├── create_bug.py           ← 单条创建（消费 bug JSON，截图内嵌描述）
│   ├── append_evidence.py      ← 给已有缺陷追加补充说明/截图（不新建缺陷）
│   ├── get_workitem.py         ← 查询工作项详情（提单后核对负责人/验证者/附件）
│   ├── update_subject.py       ← 改标题（合并缺陷/扩大影响范围时同步标题）
│   ├── import_defects.py       ← Excel 批量导入（回写状态，幂等可重跑）
│   ├── probe_fields.py         ← 联调：types 列工作项类型 / fields 查字段配置
│   ├── requirements.txt        ← 依赖（仅 openpyxl）
│   ├── config.example.json     ← 配置模板（安装时复制为 config.json）
│   ├── 模块人员映射.csv         ← 模块→负责人/验证者（用户维护，内含示例）
│   └── 缺陷导入模板.xlsx        ← 批量导入模板
└── references/
    ├── bug_draft_prompt.md     ← AI 生成缺陷草稿的规范（提单时必读）
    └── 使用手册.md              ← 面向测试同学的使用手册
```

---

## 第 0 阶段：安装与初始化（仅在 scripts/config.json 不存在时执行）

Agent 按顺序完成，用户只需在标注【需用户提供】处给信息。

### 0.1 搭建 Python 环境

1. 确认有 Python ≥ 3.9（`python --version` 或 `py --version`；没有则指引用户安装 python.org 版本并勾选 Add to PATH）。
2. 创建虚拟环境并装依赖：
   ```bash
   cd <ROOT>
   python -m venv .venv
   # Windows:
   .venv/Scripts/python.exe -m pip install -r scripts/requirements.txt
   # macOS/Linux:
   .venv/bin/python -m pip install -r scripts/requirements.txt
   ```
   下文统一用 `<PY>` 代指该解释器路径。

### 0.2 初始化配置

1. 复制模板：`cp scripts/config.example.json scripts/config.json`
2. 【需用户提供】**云效个人访问令牌**。若用户没有，指引：云效页面右上角头像 → 个人设置 → 个人访问令牌 → 新建 → 勾选「项目协作」的读、写权限 → 复制 `pt-` 开头令牌。填入 config.json 的 `token`。
3. 以下全部由 Agent 调接口自动完成（不要让用户手查）：
   - `GET /oapi/v1/platform/user` → 取 `lastOrganization` 填 `organization_id`，取 `id` 填 `default_assignee` 并把该用户姓名→id 写入 `users`。
   - `POST /oapi/v1/projex/organizations/{org}/projects:search`（body `{"perPage":50,"page":1}`）→ 列出项目清单给用户挑一个默认项目 → 填 `space_id`、`project_name`，同时把可选项目登记进 `projects`（便于以后 --project 切换）。
   - `GET .../projects/{spaceId}/workitemTypes?category=Bug` → 选「缺陷」（若 enable=false 或没有，列出可用类型让用户选，如「线上故障」）→ 填 `workitem_type_id`。
   - `GET .../projects/{spaceId}/workitemTypes/{typeId}/fields` → 填 `field_map`：优先级用 `priority` 字段（选项 displayValue→id）；严重程度找名为「严重程度」的单选字段（P0~P4 的自定义字段优先，映射 致命→P0、严重→P1、一般→P2、轻微→P3、建议→P4；若是 `1-致命` 这类选项则按中文名直接映射选项 id）。
4. 自检：`<PY> scripts/probe_fields.py types` 能列出类型即成功。
5. 告诉用户：config.json 含令牌，勿外发勿提交 git；`模块人员映射.csv` 按需维护（格式见文件内示例）。

### 0.3 安装完成回复模板

向用户报告：默认项目、工作项类型、默认指派人、配置文件位置，以及一句话用法：「把 bug 截图+一句话描述发给我即可提单」。

---

## 使用阶段

### 模式一：AI 对话提单（最常用）

区分两种场景（判断规则详见 `references/bug_draft_prompt.md`）：

- **场景A 日常迭代提缺陷**：用户发「截图 + 简要描述」→ ReadMediaFile 读图 → 按规范中的【缺陷报告模板】生成草稿（对比需求/UI推断/精准步骤，Markdown 代码块，无引导语和原因猜测）→ 展示确认 → 创建。
- **场景B 用户反馈 bug**：用户明确说用户反馈/原样提交 → 描述保持原文不改写，只提炼标题、剔除占位垃圾行；批量时先给完整清单确认。

通用流程：

1. 负责人/验证者按 `scripts/模块人员映射.csv` 推断（先按 project_name 过滤项目列，再模块关键词模糊匹配）；用户明确指定时以用户为准。
2. **先展示草稿给用户确认**，确认后才允许创建；有修改意见就改完再确认。
3. 确认后把 JSON 写临时文件，执行：
   ```bash
   <PY> scripts/create_bug.py --file <临时json>                          # 默认项目
   <PY> scripts/create_bug.py --file <临时json> --project "项目名"        # 切换项目
   ```
6. 返回缺陷ID，提醒用户到云效核对；删除临时 JSON。

### 模式二：单条 JSON 创建

用户直接给结构化内容时，组 JSON（字段见 bug_draft_prompt.md）后同模式一第 5 步；`--dry-run` 只预览不创建。

### 模式三：Excel 批量导入

1. 指引用户在 `scripts/缺陷导入模板.xlsx` 对应模块 sheet 按行填（缺陷标题必填）。
2. 预检：`<PY> scripts/import_defects.py --dry-run`。
3. 正式：`<PY> scripts/import_defects.py`，结果回写「导入状态」列；已成功行自动跳过，可重跑。
4. 从 docx/Markdown 等非结构文档批量提单：先解析成 bug JSON 列表（docx 用 python-docx 遍历 body 按编号标题分组、表格 a:blip 提取图片；python-docx 需临时 pip 安装），逐条走创建流程；**批量前必须给用户确认完整清单**（条数、标题、负责人、跳过项）。用户要求"直接放原文"时描述保持原文不改写。

---

## 关键规则

- **先确认再创建**：AI 生成/清洗的内容未经用户确认不得调创建接口。
- 不得编造截图/原文里没有的信息；看不清的数值向用户核实。
- 删除已创建工作项前必须确认 ID 无误，并告知用户删除会进云效回收站（可恢复）。
- **补充证据写回原缺陷**：给已有缺陷追加截图/现象时不要新建缺陷，用 `scripts/append_evidence.py --workitem-id <id> --note "补充说明" --image a.png`（GET 原描述 → 上传附件 → 末尾追加 → 覆盖式 PUT，自动保留原文）。
- **覆盖式 PUT 必须带 `formatType="MARKDOWN"`**：`update_workitem(description=…)` 不传 formatType 时，云效按默认富文本落库，`formatType` 变成 `RICHTEXT`，页面上 `## 【复现步骤】`、`**加粗**` 这些 markdown 标记会原样显示成字面量（用户会说「格式不对」）。`append_evidence.py` 已修好；自己写脚本改描述时也别漏。判断某条缺陷是否被写坏：`GET /workitems/{id}` 看 `formatType`，正常应为 `MARKDOWN`。修复方式：把描述原样再 PUT 一次并带 `formatType="MARKDOWN"`。
- **合并缺陷时同步标题**：同一问题在多个入口（如产品端/租户端）出现时，合并为一个缺陷跟踪，用 `scripts/update_subject.py --workitem-id <id> --subject "新标题"` 把范围写进标题；`update_workitem` 为部分更新，只传 subject 不影响其他字段。
- **创建后核对指派**：`create_bug.py` 正式创建时不打印姓名解析告警，解析失败会静默回落到 `default_assignee`；创建后用 `scripts/get_workitem.py --workitem-id <id>` 核对 assignedTo / verifier / 描述内图片数。
- **描述章节可定制**：需要标准模板外的章节（如【前置条件】）时，用 bug JSON 的 `description` 字段直接给成品描述（此时 steps/actual/expected 不必填）。
- config.json 含令牌：任何输出、分享、提交场景都不得带出；给示例用 config.example.json。
- 本工具包可整体复制/分发；分发前删除 `.venv/` 和 `scripts/config.json`（接收方 Agent 会重新走第 0 阶段）。

## 解析与排障

- 姓名→userId：config.users → `POST /oapi/v1/platform/organizations/{org}/members:search`（精确匹配姓名）→ 失败则该字段留空并提醒用户。
- 字段报错/失效：跑 `<PY> scripts/probe_fields.py fields` 取最新 fieldId/选项ID 更新 config.field_map。
- 中心版 API 路径必须带 `/organizations/{orgId}`，否则 404。
- 附件返回的 `url` 是 30 秒过期临时链；嵌描述必须用 `embedMarkdown`/`embedUrl`。
- WPS 单元格图片（=DISPIMG）openpyxl 读不到；批量带图导入改用 docx 来源或解析 xl/cellimages.xml。
- 回收站中的工作项不能更新（报"当前工作项已进回收站"）。
