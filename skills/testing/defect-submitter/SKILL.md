---
name: defect-submitter
description: 向缺陷管理平台（禅道 / Jira / 云效 / TAPD 等）提交缺陷的通用工具包。当用户要提缺陷、发来 bug 截图+描述、要把 Excel/docx/Markdown 里的缺陷批量导入缺陷平台，或首次拿到本工具包需要安装配置时使用。覆盖：环境自举安装、平台接入与字段配置、AI 对话生成缺陷单（截图内嵌描述）、单条 JSON 创建、Excel 批量导入。
---

# 提缺陷通用工具包

本目录即完整工具包，所有路径均相对于本目录（SKILL.md 所在目录，下称 `<ROOT>`）。

```
<ROOT>/
├── SKILL.md                    ← 本文件（Agent 的安装与使用指引）
├── scripts/
│   ├── defect_client.py        ← 平台适配层（第 0 阶段由 Agent 按目标平台实现）
│   ├── create_bug.py           ← 单条创建（消费 bug JSON，截图内嵌描述；只依赖适配层）
│   ├── import_defects.py       ← Excel 批量导入（回写状态，幂等可重跑；只依赖适配层）
│   ├── probe_fields.py         ← 联调探测：列项目 / 列缺陷类型 / 查字段配置 / 搜成员
│   ├── requirements.txt        ← 依赖（仅 openpyxl；适配层如需额外库在此追加）
│   ├── config.example.json     ← 配置模板（安装时复制为 config.json）
│   ├── 模块人员映射.csv         ← 模块→负责人/验证者（用户维护，内含示例）
│   └── 缺陷导入模板.xlsx        ← 批量导入模板
└── references/
    ├── bug_draft_prompt.md     ← AI 生成缺陷草稿的规范（提单时必读）
    └── 使用手册.md              ← 面向测试同学的使用手册（按团队实际情况编写）
```

**架构约定**：`create_bug.py`、`import_defects.py`、`probe_fields.py` 不直接调用任何平台 API，所有平台差异（认证方式、接口路径、字段模型）收敛在 `defect_client.py` 一个文件里。换平台只换适配层，主流程不变。

## 适配层接口契约（defect_client.py 必须实现的函数）

```
load_config(path=None)                      # 读 config.json，支持环境变量覆盖敏感项
client_from_config(cfg)                     # 按配置构造客户端
client.search_projects()                    # 列项目 → [{id, key, name}, ...]
client.list_issue_types(project)            # 列缺陷类工作项类型 → [{id, name, enabled}, ...]
client.get_type_fields(project, type_id)    # 拉字段配置（含各选项的 id）
client.search_members(name)                 # 姓名 → [{name, id}, ...]
client.create_issue(project, type_id,       # 创建缺陷，返回缺陷 ID/key
    title, description, assignee=None,
    verifier=None, custom_fields=None,
    **extra)                                # extra 可带 sprint / versions，平台不支持则忽略
client.upload_attachment(issue_id,          # 上传附件，返回可用于内嵌描述的标记
    file_bytes, filename)                   #   （如平台的 embed 语法；无则返回附件链接）
client.update_issue(issue_id, **fields)     # 更新描述等字段（用于截图内嵌回写）
```

错误统一抛 `DefectApiError(message, status=None, body=None)`。

常见平台接入要点（以官方文档为准，下列仅是入口提示）：

- **禅道（Zentao）**：18 系列起有 REST API（`/api.php/v1/`），先 POST `/tokens` 换 token，缺陷挂在产品/执行下（products / executions / bugs），字段 options 在 bug 的创建页结构里；
- **Jira**：`/rest/api/2/issue`，Basic Auth（邮箱 + API Token）或 Bearer；项目键（key）即项目标识，缺陷类型一般叫 Bug，优先级/自定义字段通过 `/rest/api/2/field` 和 createmeta 查选项 ID；
- **云效（Apsara DevOps）**：个人访问令牌（`pt-` 开头）放请求头，注意中心版接口路径带组织段；
- **其他平台**：只要能「创建缺陷 + 上传附件 + 查字段选项」，就能接入；接口不全的平台（如不能传附件）在适配层降级为「附件链接追加到描述」。

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

### 0.2 平台接入与配置

1. 【需用户提供】**目标平台与访问凭证**。确认平台种类（禅道/Jira/云效/其他）和地址；凭证按平台指引用户申请（个人访问令牌或 API Token），填入 config.json 的 `token`。
2. **实现/补全 `scripts/defect_client.py`**。查该平台官方 API 文档，按上面的接口契约实现适配函数；create_bug.py / import_defects.py / probe_fields.py 不需要改。
3. 复制配置模板并探测填写（全部由 Agent 调接口完成，不要让用户手查）：
   - 列项目 → 给用户挑一个默认项目 → 填 `project`、`project_name`，其余可选项目登记进 `projects`（便于以后 --project 切换）；
   - 列缺陷类型 → 选「Bug/缺陷」（若不可用，列出可用类型让用户选）→ 填 `issue_type`；
   - 拉字段配置 → 填 `field_map`：优先级、严重程度等单选字段，把中文语义（致命/严重/一般/轻微/建议）映射到平台实际的字段 ID 和选项 ID；
   - 取当前用户信息 → 填 `default_assignee`，并把该用户姓名→标识写入 `users`。
4. 自检：`<PY> scripts/probe_fields.py types` 能列出类型即成功。
5. 告诉用户：config.json 含凭证，勿外发勿提交 git；`模块人员映射.csv` 按需维护（格式见文件内示例）。

### 0.3 安装完成回复模板

向用户报告：目标平台、默认项目、缺陷类型、默认指派人、配置文件位置，以及一句话用法：「把 bug 截图+一句话描述发给我即可提单」。

---

## 使用阶段

### 模式一：AI 对话提单（最常用）

区分两种场景（判断规则详见 `references/bug_draft_prompt.md`）：

- **场景A 日常迭代提缺陷**：用户发「截图 + 简要描述」→ ReadMediaFile 读图 → 按规范中的【缺陷报告模板】生成草稿（对比需求/UI推断/精准步骤，Markdown 代码块，无引导语和原因猜测）→ 展示确认 → 创建。
- **场景B 用户反馈 bug**：用户明确说用户反馈/原样提交 → 描述保持原文不改写，只提炼标题、剔除占位垃圾行；批量时先给完整清单确认。

通用流程：

1. 负责人/验证者按 `scripts/模块人员映射.csv` 推断（先按 config 的 project_name 过滤项目列，再模块关键词模糊匹配）；用户明确指定时以用户为准。
2. **先展示草稿给用户确认**，确认后才允许创建；有修改意见就改完再确认。
3. 确认后把 JSON 写临时文件，执行：
   ```bash
   <PY> scripts/create_bug.py --file <临时json>                          # 默认项目
   <PY> scripts/create_bug.py --file <临时json> --project "项目名"        # 切换项目
   ```
4. 返回缺陷ID，提醒用户到平台核对；删除临时 JSON。

### 模式二：单条 JSON 创建

用户直接给结构化内容时，组 JSON（字段见 bug_draft_prompt.md）后同模式一第 3 步；`--dry-run` 只预览不创建。

### 模式三：Excel 批量导入

1. 指引用户在 `scripts/缺陷导入模板.xlsx` 对应模块 sheet 按行填（缺陷标题必填）。
2. 预检：`<PY> scripts/import_defects.py --dry-run`。
3. 正式：`<PY> scripts/import_defects.py`，结果回写「导入状态」列；已成功行自动跳过，可重跑。
4. 从 docx/Markdown 等非结构文档批量提单：先解析成 bug JSON 列表（docx 用 python-docx 遍历 body 按编号标题分组、表格 a:blip 提取图片；python-docx 需临时 pip 安装），逐条走创建流程；**批量前必须给用户确认完整清单**（条数、标题、负责人、跳过项）。用户要求"直接放原文"时描述保持原文不改写。

---

## 关键规则

- **先确认再创建**：AI 生成/清洗的内容未经用户确认不得调创建接口。
- 不得编造截图/原文里没有的信息；看不清的数值向用户核实。
- 删除已创建缺陷前必须确认 ID 无误；有回收站机制的平台（如禅道、云效）告知用户删除可恢复。
- config.json 含凭证：任何输出、分享、提交场景都不得带出；给示例用 config.example.json。
- 本工具包可整体复制/分发；分发前删除 `.venv/` 和 `scripts/config.json`（接收方 Agent 会重新走第 0 阶段）。

## 解析与排障

- 姓名→用户标识：config.users → 适配层 `search_members` 实时查（精确匹配姓名）→ 失败则该字段留空并提醒用户。
- 字段报错/失效：跑 `<PY> scripts/probe_fields.py fields` 取最新字段 ID/选项 ID 更新 config.field_map。
- 注意各平台 API 的路径前缀和版本差异（组织段、项目键、上下文路径），404 优先查路径。
- 附件内嵌：很多平台附件返回的是短时效临时链，内嵌描述必须用平台提供的 embed 语法或永久链；不支持内嵌的平台把附件链接追加到描述末尾。
- WPS 单元格图片（=DISPIMG）openpyxl 读不到；批量带图导入改用 docx 来源或解析 xl/cellimages.xml。
- 回收站/已删除状态的缺陷不能更新，批量重跑时先排除。
