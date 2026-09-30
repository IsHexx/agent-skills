# 计划：skill-catalog 元 Skill（Skill 检索与资产目录）v8

## 0. 结论先行

建设一个可在 Agent 会话中直接查询、并带本地网页面板的个人 Skill 目录，解决：

1. 忘记自己有哪些 Skill；
2. 不知道某项任务该用哪个 Skill；
3. 忘记某个 Skill 的触发方式和必要输入；
4. 无法区分高频、低频、未评级和异常 Skill；
5. 分不清"Hub 有原件"和"当前 Agent 已安装可用"；
6. 本机新装 Skill 需要被定期发现，**按来源证据分级后**收编进 Hub 统一治理。

分期定位：

| 阶段 | 内容 | 风险特征 |
|---|---|---|
| 阶段一 | 核心非破坏性能力（扫描、查询、标签） | 不触碰其他 Skill 与 Hub 资产 |
| 阶段 1.1 | 网页面板（无收编按钮） | + 写 overrides |
| 阶段 1.2 | 收编与入口治理（面板加收编按钮） | 写 Hub，两阶段事务 |
| 阶段二 | 收尾（校验、登记、INVENTORY 废止） | — |

阶段一通过即可投入日常使用，不必等待后续阶段。

技术栈：**零新增第三方包** —— PowerShell（扫描/索引/收编）+ Python 标准库（面板服务）+ Markdown/JSON（数据）。前置条件：Windows PowerShell、Python 3.x。

**核心架构原则：**
- 程序原件（Hub，可进 Git、可移植）与本机运行数据（%LOCALAPPDATA%，不进 Git）严格分离；
- 扫描事实（catalog.json）与人工标签（overrides.json）严格分离，运行时合并；
- skill_id 跨机器稳定：不依赖盘符、用户名等本机路径成分；
- 治理方向单向收敛：**有明确本地自建证据**的 Skill 经确认后收编进 Hub；外部/工具生成/来源不明的 Skill 保留原更新链，不默认收编；
- **没有外部来源证据 ≠ 本地自建；无法判断时一律 unknown。**

---

## 1. 成功标准

| 场景 | 期望结果 |
|---|---|
| 查询全部 Skill | 按高频、低频、未评级、未纳管（再细分）、观察、异常分组；明示覆盖范围 |
| 按任务找 Skill | 推荐 1～3 个，含推荐理由和可复制触发话术；只推荐 availability=active 且 integrity∈[ok, drift] 的项，drift 附警告 |
| 查询具体 Skill | 完整读取目标 SKILL.md 后总结触发条件、输入、流程、限制 |
| Hub 有原件但未安装 | 明确回答"只有原件，尚未安装"，给出安装建议与命令（不自动执行） |
| 未纳管 Skill | 按 可直接收编/需评估/保持外部管理 三组展示；来源不明永不进"全部收编" |
| 收编执行 | -AdoptPlan 生成持久化计划（含 copy_manifest），用户确认后 -AdoptCommit 按白名单复制，失败逆序回滚 |
| 索引过期 | 查询前自动 -Check，过期自动 Rebuild，失败用旧数据并明示 |
| 扫描失败状态 | health.json 持久记录最近执行结果；会话/面板实时读取，INDEX 展示 Rebuild 时快照 |
| 同名重复 | name 不充当唯一标识，详情/标签/API 全部使用 skill_id |
| 换电脑迁移 | skill_id 不变，overrides 导出导入后标签准确匹配 |
| 扫描根临时失败 | 不误判删除；旧数据保留；显著警告 |
| 重建索引 | overrides 不受影响；重复 Rebuild 幂等（除 generated_at） |

---

## 2. 范围定义

### 2.1 纳管范围

| root_id | source_type | 默认路径 | available_in | required | 布局 |
|---|---|---|---|---|---|
| hub-origin | hub | `${SKILL_HUB_ROOT}\skills` | （原件源） | 是 | direct-children，深度 1 |
| agents-user | user-entry | `${USERPROFILE}\.agents\skills` | agents（Kimi/Claude/Codex 等通用入口） | 是 | direct-children，深度 1 |
| codex-user | user-entry | `${CODEX_HOME}\skills`（未设置回退 `${USERPROFILE}\.codex`） | codex | 否 | nested，深度 2（兼容 `local/<skill>/`） |
| 项目级 | project | config.json 显式配置 | 按配置 | 否 | 按需，深度 1 |

### 2.2 默认不纳管

- Codex `.system` 内置 Skill（只读、随产品更新）
- 插件缓存目录（多版本噪音，默认关闭）
- 无 `SKILL.md` 的目录：记录为"非标准目录"，不计入有效 Skill
- `.git`、`node_modules`、`.venv`、缓存、备份、归档

回答"我有哪些 Skill"时必须提示覆盖范围：**当前展示个人本地及已配置项目的 Skill，不含系统内置和插件缓存 Skill**。

### 2.3 数量口径

- 不使用固定数字作为验收条件；目录数、有效 Skill 数、唯一名称数分别统计
- 首轮验证基线：`.agents\skills` 41 个一级目录、39 个含标准 SKILL.md，以实时扫描为准

---

## 3. 架构：原件与运行数据分离

### 3.1 Hub（只放可移植程序原件，可进 Git）

```text
${SKILL_HUB_ROOT}\skills\skill-catalog\
├── SKILL.md                  # 触发描述、查询流程、刷新规则
├── agents/openai.yaml        # UI 名称、简介
├── config.example.json       # 配置模板（不含本机路径）
├── scripts/
│   └── sync-index.ps1        # 扫描、解析、去重、校验、生成索引、收编
├── panel/
│   ├── server.py             # 本地面板服务（仅标准库 ThreadingHTTPServer）
│   └── static/index.html     # 单页面板（原生 JS）
└── references/
    ├── schema.md             # JSON 数据结构文档
    └── apple-design.md       # 面板设计规范（实施时从 _workspace/skill管理/skill.md 迁入，为唯一规范来源）
```

用户级入口用 Junction 指向原件（`mklink /J`，无需管理员权限）：

```text
${USERPROFILE}\.agents\skills\skill-catalog -> ${SKILL_HUB_ROOT}\skills\skill-catalog
```

### 3.2 本机运行数据（不进 Git）

```text
%LOCALAPPDATA%\skill-catalog\
├── config.json               # 本机扫描根、排除规则、面板端口、分类枚举（支持环境变量）
├── catalog.json              # 扫描事实源（纯机器数据）
├── health.json               # 最近一次 Check/Rebuild 的执行结果（脱敏，原子写入）
├── INDEX.md                  # 阅读视图（catalog+overrides 运行时合并生成，禁止人工编辑）
├── overrides.json            # 人工标签：频率/分类/置顶/触发示例/备注
├── adopt-backups/            # 收编事务的原目录备份（在扫描根之外）
└── transactions/
    ├── plans/                # AdoptPlan 生成的计划 <plan_id>.json
    └── journals/             # AdoptCommit 的事务日志 <transaction_id>.json
```

### 3.3 跨机器迁移

- 程序原件随 Hub 走（Git 或整体拷贝）
- 人工标签迁移：`sync-index.ps1 -ExportPreferences <path>` / `-ImportPreferences <path>`
  - 默认**排除** `confirmed_used_at` 等本机使用记录；需要时显式加 `-IncludeUsage`
  - 导入匹配链：`skill_id` → `aliases` → `logical_name + root_id + 相对路径`；仍不匹配的报告未匹配清单，不静默丢弃
- 本机路径、使用时间**不得**提交到 Hub

### 3.4 台账职责（已定案，不留待决策）

| 文件 | 唯一职责 |
|---|---|
| `skills-registry.md`（Hub） | 只记录自维护、正式纳管的 Skill 资产（收编动作必须同步登记） |
| `catalog.json`（本机） | 当前机器扫描出的结构化事实源 |
| `health.json`（本机） | 最近一次 Check/Rebuild 执行结果；会话/面板的警告实时以它为准 |
| `INDEX.md`（本机） | catalog+overrides 合并后的生成视图；健康横幅只反映 Rebuild 时快照并注明时间 |
| `GLOBAL_SKILLS_INVENTORY.md`（Hub） | **废止手工维护**。文件保留一段迁移说明，指向 `%LOCALAPPDATA%\skill-catalog\INDEX.md`；不再写入本机扫描结果 |

---

## 4. 数据模型

所有 JSON 带 `schema_version`。

### 4.1 唯一标识（跨机器稳定）

```text
skill_id     = name + "_" + sha256(root_id + "/" + 相对路径) 前 12 位
logical_name = frontmatter 的 name（仅用于展示和跨版本标签）
```

- `root_id` 来自 config 的扫描根配置（如 `agents-user`），相对路径是 skill 目录相对扫描根的路径——**不含盘符、用户名等本机成分**，换电脑后 ID 不变
- 相对路径统一为 `/` 分隔、转小写后参与哈希；哈希取前 **12** 位降低冲突概率
- 多个完全相同来源合并时：使用优先级最高来源的稳定 skill_id，其余候选 ID 写入 `aliases`
- name 不作为唯一标识；详情查询、overrides 键、面板 API 全部使用 `skill_id`

### 4.2 状态拆维

| 字段 | 枚举 | 含义 |
|---|---|---|
| `availability` | active | 已安装到可发现入口，可调用 |
| | source-only | 仅 Hub 有原件，未安装 |
| | unavailable | 路径失效等不可用 |
| `integrity` | ok | 内容一致或无原件可比 |
| | drift | 安装副本与 Hub 原件 content_hash 不同（可调用但附警告） |
| | conflict | 同名不同内容且无法判定原件关系（不推荐） |
| | invalid | frontmatter 异常（不推荐） |

**推荐规则**：`availability=active` 且 `integrity ∈ [ok, drift]`；drift 默认附带警告不排除；conflict/invalid/unavailable 不推荐。

### 4.3 来源与可收编性（证据导向，禁止反向推断）

| `source_kind` | 判定标准（必须持有正面证据） |
|---|---|
| local-authored | 有明确本地自建证据：Hub registry 声明、skill 内 `provenance.json` 声明、或用户人工确认 |
| external | 有外部来源证据：上游 URL、包管理安装记录、Git remote、第三方 License 来源等 |
| plugin-generated | 位于插件/工具生成目录，或存在生成器标记 |
| unknown | **无法取得明确来源证据时的唯一去向** |

铁律：

- **没有外部来源证据不等于本地自建**；无法判断必须归 unknown
- 位于 Hub 只说明 `managed=true`，**不自动说明 local-authored**（Hub 里也可能收编过第三方资产）
- unknown 一律 review-required，永不进入"全部收编"默认范围
- 只有 local-authored 且 AdoptPlan 预检通过的才是 eligible

| `adoptability` | 含义 |
|---|---|
| eligible | local-authored + 预检通过，可直接收编 |
| review-required | external / unknown：需逐项确认来源与许可证 |
| blocked | plugin-generated：保留原更新链，永不收编 |

"未纳管"展示拆为三组：**可直接收编（eligible）/ 需评估（review-required）/ 保持外部管理（blocked）**。

### 4.4 catalog.json（纯扫描事实，不含任何人工字段）

```json
{
  "schema_version": 1,
  "generated_at": "2026-08-04T10:00:00+08:00",
  "inventory_fingerprint": "sha256(排序后的manifest)",
  "scan_health": "complete",
  "root_results": [
    { "root_id": "agents-user", "status": "ok", "scanned_at": "..." }
  ],
  "statistics": { "dirs_scanned": 0, "valid_skills": 0, "unique_names": 0 },
  "manifest": [
    { "path": "<root_id>/<相对路径>", "length": 123, "mtime_utc": "..." }
  ],
  "skills": [
    {
      "skill_id": "dws_a1b2c3d4e5f6",
      "logical_name": "dws",
      "aliases": [],
      "description": "...",
      "managed": false,
      "installed": true,
      "available_in": ["agents", "codex"],
      "entrypoints": ["..."],
      "source_path": "...",
      "source_kind": "external",
      "adoptability": "review-required",
      "metadata_hash": "...",
      "content_hash": "...",
      "availability": "active",
      "integrity": "ok",
      "warnings": []
    }
  ],
  "anomalies": []
}
```

- `catalog.json.scan_health`：**生成这份 catalog 时**的扫描完整性（complete/partial/failed）
- `frequency`/`category`/`example_prompt` 等人工属性**只存在 overrides.json**
- `INDEX.md` 与 `/api/catalog` 在运行时合并 catalog + overrides
- `manifest` 覆盖 skill 目录内全部有效文件（排除 .git/缓存/venv/日志/运行输出）——scripts/ 变更才能触发 drift 重算

### 4.5 health.json（最近一次执行结果）

```json
{
  "schema_version": 1,
  "last_attempt_at": "...",
  "operation": "check",
  "scan_health": "failed",
  "root_results": [
    { "root_id": "agents-user", "status": "failed", "error": "access_denied" }
  ],
  "catalog_generated_at": "..."
}
```

- 每次 `-Check`/`-Rebuild` 都更新 health.json（包括失败场景）
- **原子写入**（临时文件+替换）；并发 `-Check` 使用轻量 Check 锁
- 警告展示：**会话和面板实时读 health.json；INDEX.md 只展示最后一次 Rebuild 时的快照并注明时间**（不声称三处天然实时一致）
- 错误信息脱敏：只存错误类别（如 access_denied/path_not_found），不存完整堆栈

### 4.6 overrides.json（人工，唯一可手改的数据文件）

```json
{
  "schema_version": 1,
  "logical_names": {
    "lark-base": { "frequency": "高频" }
  },
  "skills": {
    "task-scheduler_e5f6a7b8c9d0": {
      "frequency": "高频",
      "category": "测试管理",
      "pinned": true,
      "example_prompt": "周杰 8月3~5日 测CRM_15",
      "note": "",
      "confirmed_used_at": "2026-08-01"
    }
  }
}
```

- `skills` 按 skill_id 设置（精确）；`logical_names` 按名称设置（作用于所有同名版本）
- **合并优先级：skill_id 级 > logical_name 级 > 默认值**

### 4.7 config.json（本机）

```json
{
  "schema_version": 1,
  "scan_roots": [
    {
      "root_id": "agents-user",
      "source_type": "user-entry",
      "path": "${USERPROFILE}\\.agents\\skills",
      "available_in": ["agents"],
      "required": true,
      "layout": "direct-children",
      "max_depth": 1,
      "enabled": true
    }
  ],
  "excludes": [".git", "node_modules", ".venv"],
  "allowed_categories": ["测试管理", "飞书", "文档办公", "数据分析", "开发设计", "其他"],
  "panel_port": 8627
}
```

- 路径支持 `${USERPROFILE}`、`${LOCALAPPDATA}`、`${CODEX_HOME}`、`${SKILL_HUB_ROOT}` 展开；`${CODEX_HOME}` 未设置时回退 `${USERPROFILE}\.codex`
- **root_id 校验（首次加载即查）**：非空；所有启用根唯一；只允许小写字母、数字、连字符；不满足则报错并拒绝扫描
- `allowed_categories` 为面板/标签的分类枚举来源，**不在代码里写死**；枚举之外的值拒绝写入
- Skill 自身路径从 `$PSScriptRoot` 反向解析；路径比较忽略大小写、统一分隔符

---

## 5. SKILL.md 设计

### 5.1 Frontmatter（只保留 name + description）

```yaml
---
name: skill-catalog
description: 查询、检索和维护本机个人 Skill 目录。用户询问"我有哪些 Skill/技能""某件事该用哪个 Skill""某个 Skill 怎么使用或触发""列出高频或低频 Skill"，或需要刷新 Skill 索引、标注使用频率、检查重复、失效、非标准 Skill，以及把本机新安装的本地自建 Skill 收编进 Hub 统一管理时使用。
---
```

### 5.2 核心行为

1. **任何列表查询或推荐请求，先执行** `sync-index.ps1 -Check`：
   ```text
   退出码 0（最新）→ 读 INDEX.md 回答
   退出码 2（过期）→ 自动 -Rebuild 后读取
   退出码 1（失败）→ 用旧 INDEX 回答，并按 health.json 明确提示失败原因
   ```
2. 按任务意图推荐 1～3 个，每项含 `名称 — 用途 — 推荐原因 — 可复制触发话术`；推荐规则见 §4.2；无匹配时明说，不编造。
3. 回答"我有哪些 Skill"时提示覆盖范围（§2.2 末段）；health.json 非 complete 时必须先给警告再给结果；存在 eligible 未纳管 Skill 时附一句收编提醒（§8.2）。
4. 查询具体 Skill 用法时，按 skill_id 定位并**完整读取**其 SKILL.md 后总结，不只靠索引摘要。
5. source-only 应答："找到对应 Skill，但当前只有原件，尚未安装到本会话可发现的入口。"**一期只给出安装建议和具体命令（如 mklink /J 示例），不自动执行**。
6. 收编（§8）：检测和提醒随时可做；执行必须先 `-AdoptPlan` 展示预检清单，用户确认后 `-AdoptCommit`。
7. 修改标签只写 `overrides.json`（写前自动备份 `overrides.json.bak`），随后触发 Rebuild。
8. 只允许写本 skill 的 `config.json`、`%LOCALAPPDATA%\skill-catalog\` 下文件；收编事务（§8.3）允许写 Hub 目标目录、`skills-registry.md` 和转换用户级入口；**其他情况不得改任何 Skill 文件**。
9. 遇到 drift/conflict/invalid 只报告，不自行删除、覆盖、迁移。
10. 面板启动：`python <skill目录>\panel\server.py`，提示实际端口。

### 5.3 回答格式

紧凑表格：`| Skill | 用途 | 频率 | 触发示例 | 状态 |`

---

## 6. 扫描与索引规则

### 6.1 Frontmatter 解析（受限状态机，非正则）

只解析 `name` 和 `description`，必须支持：

- `description: "..."`（双引号，含转义）、`description: '...'`（单引号）
- `description: |`、`|-`、`>`、`>-` 多行块（按 YAML 折叠规则拼接，压缩空白）
- UTF-8 BOM（**当前 123 个样本中未发现，但解析器需兼容**）、CRLF/LF
- description 内含冒号、引号、换行
- 分隔符 `---` 缺失或不闭合、name/description 缺失 → 标记 integrity=invalid，不猜测

实测分布基线（123 个样本）：91 引号单行 / 25 裸单行 / 7 多行，含 CRLF 变体。

### 6.2 双指纹与合并规则

| 指纹 | 计算范围 | 用途 |
|---|---|---|
| `metadata_hash` | SKILL.md 内容 SHA256 | 触发信息是否变化 |
| `content_hash` | skill 目录内全部有效文件 | 副本识别、drift、真实重复 |

**计算时机约束**（保 `-Check` ≤3 秒）：

- `-Check`：只重建轻量 manifest（路径+长度+mtime），算 `inventory_fingerprint` 比对，不算文件哈希
- `-Rebuild`：全量算 `metadata_hash`；`content_hash` 只对同名候选对、Hub↔安装副本对计算

**合并规则**（仅两种情形可合并为一个条目）：

1. 多入口指向同一规范化真实目录（Junction）→ 一个 skill_id，保留全部 entrypoints
2. `logical_name` 与 `content_hash` 都相同 → 合并：取优先级最高来源的 skill_id，其余候选 ID 写入 `aliases`

其余同名：integrity=drift（能确定原件关系）或 conflict（无法确定）。

### 6.3 扫描根失败策略（失败≠删除）

| 场景 | 处理 |
|---|---|
| `-Check` 中任一启用根失败 | 退出码 1，旧 INDEX 继续使用；health.json 记录失败 |
| `-Rebuild` 中任一 **required** 根失败 | 终止替换，保留旧 catalog/INDEX；health.json 记 `failed` |
| **可选**根失败 | 保留该根上一次数据，catalog 标 `partial`、该根 `status=stale`；health.json 同步记录 |
| 用户确认目录永久移除 | 先在 config 中 `enabled=false`，再 Rebuild |

警告展示按 §4.5：会话/面板实时读 health.json；INDEX 展示 Rebuild 时快照。

### 6.4 Staleness 与退出码

- `-Check`：重新生成当前 manifest → 计算 fingerprint → 与 catalog.json 的 `inventory_fingerprint` 比对
- 不一致 → 退出码 2（过期）；扫描/解析失败 → 1；一致 → 0

### 6.5 原子写入与失败恢复

- Rebuild 先写临时文件 → JSON/Markdown 校验通过 → 原子替换正式文件
- health.json 同样原子写入（§4.5）
- 更新 overrides.json 前保留 `overrides.json.bak`
- 写入失败时保留旧索引可用
- Rebuild 与 overrides 写入加互斥锁（锁文件），防并发覆盖

---

## 7. 高频/低频管理

### 7.1 标签定义

| 标签 | 定义 |
|---|---|
| 高频 | 经常使用或需优先展示 |
| 低频 | 按需使用，继续保留 |
| 未评级 | 新发现或证据不足（**所有新增项的默认值**） |
| 观察 | 非标准、长期未确认、待评估（不等于删除建议） |

### 7.2 初始预填（展开为显式 skill_id 名单，禁用通配符）

- **高频**：lark-base、lark-wiki、lark-doc、lark-sheets、lark-im、task-scheduler、codebase-reader、officecli
- **低频**：neat-freak、storage-analyzer、aihot、khazix-writer、hv-analysis、leader、kami、lark-workflow-meeting-summary、lark-workflow-standup-report，及其余按需 lark-*（首轮扫描后**逐个展开**写入，不写 `lark-*` 模式）
- **观察**：dws、agent-reach、awesome-design-md、remotion-best-practices（标"待评估"，不写删除建议）
- 首轮 Rebuild 后人工核对一次名单，之后新增项一律"未评级"

### 7.3 触发示例来源

- `overrides.json` 的 `example_prompt` 是唯一稳定来源
- 首次生成：Agent 根据 description 草拟，**用户确认后**写入；未确认的在回答阶段现场组织，PowerShell 不编造
- 已确认的 example_prompt 后续 Rebuild 保持稳定

### 7.4 使用记录边界（一期）

- 不自动统计调用；仅用户明说"记录刚才用了 XX"时更新 `confirmed_used_at`
- 二期再评估从会话记录统计 `last_used`/`usage_count_30d`，且只给升降级建议

---

## 8. 收编：本机新装 Skill 分级导入 Hub（阶段 1.2）

### 8.1 检测（"定期"的实现方式）

- 不引入后台守护/定时任务（与 §13 一致）；**"定期"= 每次查询前的 `-Check` / `-Rebuild` 自然检测**
- 候选识别：`managed=false` 且 `installed=true` 的有效 Skill，按 §4.3 的证据规则判定 `source_kind` 与 `adoptability`
- 用户也可随时主动问："检查有没有没纳管的 Skill"

### 8.2 提醒（按三组展示）

- INDEX.md："未纳管"分三区——可直接收编 / 需评估 / 保持外部管理
- 会话回答：列表末尾附一句，如"1 个本地自建 Skill 可直接收编；2 个需评估来源；外部 Skill 保持原更新链不动"
- 面板（阶段 1.2 加收编按钮）：三组分区展示，只有 eligible 有收编按钮，review-required 需逐项确认，blocked 无按钮

### 8.3 两阶段事务（计划持久化 + 白名单复制）

**阶段 A：预检 `sync-index.ps1 -AdoptPlan <skill_id>`**

不修改任何 Skill、Hub、入口和 registry；**允许写入运行状态目录的计划文件** `transactions/plans/<plan_id>.json`：

```json
{
  "plan_id": "...",
  "created_at": "...",
  "expires_at": "...",
  "skill_id": "...",
  "source_path": "...",
  "expected_content_hash": "...",
  "copy_manifest": ["SKILL.md", "scripts/a.py", "references/x.md"],
  "risk_findings": [],
  "planned_paths": [],
  "registry_change_preview": {},
  "status": "pending"
}
```

预检内容：

- 来源证据复核（§4.3）、License 检查
- **copy_manifest 白名单**：Commit 只允许复制清单内文件，规则：

| 类型 | 策略 |
|---|---|
| `.git` | **永久排除，不允许放行** |
| `node_modules`、`.venv`、缓存、日志 | **永久排除** |
| `.env`、Token、Cookie、私钥、账号配置 | **默认阻断且不可放行**：用户须先清理源 Skill 再重新 Plan |
| 指向 skill 目录外的 Reparse Point | **永久阻断** |
| 大文件、普通二进制资源 | 显示大小，用户逐项确认后入 manifest |
| LICENSE、来源说明 | 应保留 |
| SKILL.md、scripts、references、assets、agents | 正常纳入 |

- Hub 同名冲突检查；`expected_content_hash` 基于 **copy_manifest** 计算
- 计划状态机：pending → committed / failed / expired；**已终结的计划禁止重复提交**

**阶段 B：提交 `sync-index.ps1 -AdoptCommit <plan_id>`**

1. 读取计划文件：检查未过期、状态为 pending、核对用户确认的风险项
2. 重新校验 source path 存在、当前内容哈希 == `expected_content_hash`（不等 → 中止，要求重新 Plan）
3. 创建事务 journal `transactions/journals/<transaction_id>.json`
4. 按 **copy_manifest** 复制到 Hub 临时目录 `skills/.adopt_tmp/<transaction_id>/`
5. 复制后重算目标目录哈希，与 manifest 预期哈希比较——**不一致立即回滚**
6. 备份 `skills-registry.md`
7. 临时目录原子改名为正式目录 `skills/<name>/`
8. 原安装目录移动到扫描根之外的 `adopt-backups/<transaction_id>/`
9. 建立 Junction 并验证可读、SKILL.md 可访问
10. 原子更新 registry（追加"收编自本机安装"记录）
11. Rebuild；skill 变为 `managed=true`，skill_id 更新为 hub-origin 稳定 ID，原 ID 写入 `aliases`（overrides 标签经匹配链自动跟随）；计划标记 committed

**回滚**：任一步失败，逆序执行——删本事务 Junction → 恢复原安装目录 → 恢复 registry 备份 → 删除本事务 Hub 目录；journal 记录失败原因。**只允许删除带本 transaction_id 且由本操作创建的目标。**

### 8.4 批量收编

"全部收编"执行前必须展示完整清单：名称与来源证据、adoptability、文件数与大小、敏感项、Hub 冲突、将修改的路径和 registry 记录。**只有 eligible 进入批量默认选择**；review-required 逐项确认；blocked/unknown 永不进入。任一失败不影响其他，最后汇总成功/失败清单。

### 8.5 收编边界

- 一期**不自动收编**：检测和提醒自动，执行必须确认
- 项目级入口的 Skill 一期不收编（只报告），避免误搬项目资产
- integrity=conflict 的同名对不自动处理，由用户先看冲突详情再决定

---

## 9. 网页管理面板（阶段 1.1；收编按钮在 1.2 加入）

### 9.1 技术

- `panel/server.py`：仅标准库，**ThreadingHTTPServer**，绑 `127.0.0.1`，端口占用自动 +1 重试并提示；Rebuild/Adopt 单实例锁
- `panel/static/index.html`：单页、原生 JS、无构建
- API（1.1）：
  - `GET /` 页面
  - `GET /api/catalog`（catalog+overrides+health 运行时合并）
  - `GET /api/skill?id=<skill_id>`（SKILL.md 全文）
  - `POST /api/overrides`（改标签，先备份，互斥锁）
  - `POST /api/rebuild`（调 ps1，返回变化摘要）
- API（1.2 增加，两阶段）：
  - `POST /api/adopt/plan` → 返回计划文件内容 + plan_id
  - `POST /api/adopt/commit`：携带 `plan_id` + `skill_id` + `expected_content_hash` + CSRF token；服务端验证计划未过期、内容未变化，互斥锁保护

### 9.2 功能边界

- 1.1 做：分组浏览（高频/低频/未评级/未纳管三组/观察/异常）、搜索、来源/状态筛选、详情抽屉（完整 SKILL.md）、标签编辑、刷新索引并提示变化；health 警告条（实时读 health.json）
- 1.2 增加：eligible 条目的收编按钮（点后展示 plan 清单，确认后 commit）
- 不做：删除、禁用、批量安装

### 9.3 安全约束（全部必须实现）

- `/api/skill` 只按 catalog 中存在的 `skill_id` 查表读取，**禁止接收文件路径**，杜绝路径穿越
- SKILL.md 展示用 `textContent` 或转义后 `<pre>`，**禁止 innerHTML**，防 XSS
- POST 校验 Origin/Host；启动时生成随机 CSRF token，变更类请求必须携带
- 不开 CORS；限制 `Content-Type: application/json` 和请求体大小（如 64KB）
- `frequency`/`category` 服务端按 config 的 `allowed_categories` 枚举校验，拒绝未知字段
- 调 PowerShell：固定参数数组、`shell=False`、固定脚本路径、超时控制
- API 错误不返回本机堆栈和完整文件路径
- 响应头：`Content-Security-Policy`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`、`Cache-Control: no-store`
- 未识别路径统一 404，禁止目录列表

### 9.4 设计语言（执行摘要）

唯一规范来源：`references/apple-design.md`（实施时从 `D:\财宝\AgentWorkspace\_workspace\skill管理\skill.md` 迁入 skill 内，不依赖临时目录）。实现前完整阅读。落地条目：

- **即时反馈**：按钮/可点行 pointer-down 立即反馈（`scale(0.97)`，100ms）；操作结果按 状态/完成/警告/错误 四类 toast；保存与刷新必须有完成提示
- **详情抽屉**：右侧滑入滑出（同路径进出）；spring 近似——临界阻尼无回弹（damping 1.0、response 0.3~0.4，原生 rAF 或等效 cubic-bezier）；动画中不锁输入；Esc 关闭
- **材质层次**：侧栏/顶栏 `backdrop-filter: blur(20px)` + 半透背景；不叠双层半透明；sticky 顶栏交界处用渐变过渡，不用生硬 1px 线
- **排版**：system-ui；大标题 tracking -0.02em、正文近 0；间距 rem；层级靠 字重+字号+行距 组合
- **无障碍**：`prefers-reduced-motion` 降级为 opacity 渐隐；`prefers-reduced-transparency` 材质近实色；键盘可操作、焦点可见
- **不做**：无拖拽手势，不引动量投影/橡皮筋/第三方动效库

---

## 10. 实施步骤

### 阶段一：核心非破坏性能力（扫描、查询、标签）
1. 用 skill-creator 的 `init_skill.py` 在 Hub `skills/` 初始化 skill-catalog；按 §5.1 重写 SKILL.md、校对 `agents/openai.yaml`
2. 建立用户级 Junction（`mklink /J`）；在 `skills-registry.md` 登记（沿用现有格式）
3. 迁入设计规范到 `references/apple-design.md`
4. 实现 `sync-index.ps1`：配置读取（环境变量展开+回退、root_id 校验）、frontmatter 状态机、路径规范化、root_id/相对路径 skill_id（12 位哈希）、双指纹、深度控制、source_kind/adoptability 证据判定、去重/drift/conflict+aliases、manifest+fingerprint、扫描根失败策略+health.json（原子写）、原子写入+互斥锁、`-Check/-Rebuild/-ExportPreferences/-ImportPreferences`
5. 初始化本机 `%LOCALAPPDATA%\skill-catalog\`（config.json 从 example 生成）、`overrides.json`（§7.2 显式名单）
6. 全量 Rebuild，生成 catalog.json + health.json + INDEX.md
7. 查询行为：列表/推荐/具体用法/source-only 应答/未纳管三组提醒；查询前 `-Check`；health 警告
8. **按 §11 完成核心验证后进入 1.1**

### 阶段 1.1：网页面板（无收编）
1. `server.py` + 1.1 API + 安全约束（§9.3）
2. `index.html`（功能 §9.2 的 1.1 部分 + 设计语言 §9.4）
3. 联调：面板改标签 → overrides → rebuild → 列表更新
4. 面板验证（§11.4）

### 阶段 1.2：收编与入口治理
1. `sync-index.ps1` 增加 `-AdoptPlan/-AdoptCommit`（§8.3：计划持久化、copy_manifest 白名单、两阶段事务、回滚）
2. 面板增加 adopt/plan、adopt/commit API 与收编按钮
3. 批量收编清单流程（§8.4）
4. 收编验证（§11.2 收编用例 + §11.3 话术 9）

### 阶段二：收尾
1. `quick_validate.py` 校验 skill 结构
2. 新开 Kimi/Codex 会话验证自动发现与触发
3. 结果登记 `skills-registry.md`；`GLOBAL_SKILLS_INVENTORY.md` 写入废止说明

---

## 11. 验证方案

### 11.1 结构验证
- frontmatter 只含 name/description；name = 目录名 = skill-catalog
- `quick_validate.py` 通过

### 11.2 扫描与收编验证（全部用临时 fixture 目录，不动真实 Skill）

| 用例 | 预期 |
|---|---|
| 标准/引号/裸单行 description | 正确提取 |
| 多行 `|` `>` `>-` `|-` | 正确拼接为单行 |
| 带 BOM 文件（构造样本） | 兼容，不影响识别 |
| CRLF 文件 | 正确解析 |
| 目录无 SKILL.md | 标记非标准，不计入有效 |
| Junction 多入口同一原件 | 一个 skill_id，保留全部入口 |
| 同名同 content_hash | 合并，其余 ID 进 aliases |
| 同名不同内容（两个 dws） | 两个 skill_id，互不串标签 |
| 同 SKILL.md、不同 scripts/ | 识别为 drift，不得合并 |
| Hub 原件未安装 | availability=source-only，不默认推荐 |
| 安装副本落后于 Hub | integrity=drift，推荐时附警告 |
| 修改 SKILL.md 或 scripts/ | `-Check` 退出码 2 |
| required 根失败 | Rebuild 终止，旧 catalog/INDEX 保留，health.json 记 failed 且会话/面板可见 |
| 可选根失败 | 保留该根上次数据，partial，health.json 同步 |
| 永久移除根 | config 禁用后 Rebuild，该根 skill 正常消失 |
| root_id 非法/重复 | 首次加载即报错，拒绝扫描 |
| skill_id 跨机器稳定 | 模拟不同盘符/用户名的同名根，root_id+相对路径相同则 skill_id 相同 |
| overrides 导入回退 | skill_id → aliases → logical_name+root_id+相对路径；未匹配列入报告 |
| **无来源证据的第三方 skill** | source_kind=unknown、review-required，永不进批量默认（不误判 local-authored） |
| 外部 skill（上游 URL/License 证据） | source_kind=external、review-required |
| plugin-generated 特征 | adoptability=blocked，无收编入口 |
| AdoptPlan | 不改 Skill/Hub/registry；计划文件落盘且含 copy_manifest/expected_content_hash/过期时间 |
| 敏感项命中（.env/私钥 fixture） | 阻断且不可放行；清理源后重新 Plan 才可通过 |
| `.git`/`node_modules` 在源目录 | 永久排除，不在 copy_manifest 中 |
| Reparse Point 指向目录外 | 永久阻断 |
| AdoptCommit 正常 | 仅复制 manifest 文件；复制后哈希校验通过；备份移出扫描根；Junction 验证；registry 更新；managed=true；标签经 aliases 跟随 |
| Commit 时内容已变化 | hash 不等，中止，要求重新 Plan |
| 重复提交同一 plan | 计划已终结，拒绝 |
| 事务中途失败 | 逆序回滚，无残留；只删本 transaction_id 目标 |
| 收编后扫描 | adopt-backups 在扫描根之外，不被识别为新 skill |
| 重复执行 Rebuild | 除 generated_at 外结果一致（幂等） |
| 写入过程人为中断 | 旧 INDEX 仍可用 |
| 并发 -Check | health.json 原子写+Check 锁，无撕裂 |
| 重建后 | overrides 人工标签保持不变 |
| 性能 | 当前规模 `-Check` ≤ 3 秒 |

### 11.3 会话验证

1. "我有哪些 Skill？"（含覆盖范围提示；未纳管按三组提醒）
2. "列出高频 Skill。"
3. "排期应该用哪个 Skill？"
4. "finance-testcase-reviewer 怎么触发？"
5. "有没有能做完全无关任务的 Skill？"（应明确说无高置信匹配）
6. "刷新 Skill 索引。"
7. "把 khazix-writer 标成高频。"
8. 查询一个 source-only 的 Hub skill（"只有原件，未安装"，只给安装建议）
9. "检查有没有没纳管的 Skill" → "收编 XX"（先 plan 清单，确认后 commit）

### 11.4 面板验证

- 功能：分组/搜索/筛选/详情/标签编辑/刷新（1.1）；收编 plan/commit（1.2）
- 状态：空状态、加载状态、错误状态、长列表滚动、health 警告条
- 键盘与焦点：键盘可操作、焦点可见、Esc 关闭抽屉
- 安全：恶意 HTML 样本（原样转义显示）；无 token 的 POST 被拒；`?id=../../etc` 被拒；未知路径 404 无目录列表；安全响应头齐全
- 设计语言抽查：按压反馈、抽屉方向一致、reduced-motion 降级

---

## 12. 风险与控制

| 风险 | 控制 |
|---|---|
| 扫描范围过大 | 每根目录显式配置 layout/max_depth，插件缓存默认关闭 |
| 同名串标签/串详情 | skill_id 主键（root_id+相对路径，12 位哈希），name 仅展示用 |
| 换电脑 skill_id 全变、标签丢失 | skill_id 不含本机路径成分；aliases + 三级导入匹配链 |
| 未知来源被误判本地自建 | 证据导向判定：无正面证据一律 unknown → review-required；eligible 需 local-authored 证据+预检通过 |
| 外部 skill 被误收编、掐断更新链 | external 逐项确认；plugin-generated 一律 blocked |
| 收编带入敏感信息/大依赖 | copy_manifest 白名单：.git/node_modules 永久排除；敏感凭证阻断不可放行；复制后哈希校验 |
| 收编中途失败留残局 | 计划持久化 + 两阶段事务 + 扫描根外备份 + 按 transaction_id 逆序回滚 + 计划防重 |
| 扫描失败状态无法持久显示 | health.json 独立记录，原子写入；会话/面板实时读取 |
| 扫描根临时失败误判删除 | required/optional 分级失败策略 + scan_health 三态 + 显著警告 |
| Junction/副本重复、drift 误判 | 真实路径规范化 + metadata/content 双指纹 |
| 重建覆盖人工标签 | 文件级分离 + 写前备份 + 互斥锁 |
| 读全部正文撑爆上下文 | 索引只读 frontmatter；查具体 skill 才读正文 |
| 自动统计不准 | 一期不自动统计，二期只给建议 |
| 低频被误读为可删 | 频率与生命周期分离，删除必须单独确认 |
| 换电脑路径失效 | 配置环境变量化（含 CODEX_HOME 回退）+ $PSScriptRoot 反解 + 首跑健康检查 |
| 面板本地攻击面 | §9.3 全量约束 |
| 扫描中断留半份索引 | 原子写入，失败保旧 |
| Hub 被运行数据污染 | 运行数据全部落 %LOCALAPPDATA%，Hub 只放原件 |
| 设计规范依赖临时文件 | 实施时迁入 references/apple-design.md |

---

## 13. 明确不做（一期）

- Skill 删除、迁移、批量安装；面板启用/禁用；**自动建立安装入口**（只给建议和命令）
- **自动收编**：检测和提醒自动，执行必须确认；项目级 Skill 不收编；blocked/unknown 永不收编
- 根据低频自动建议删除
- 后台常驻监听/定时任务（"定期"= 每次查询前 -Check 检测；面板按需启动）
- 跨客户端统一调用统计
- 修改其他 Skill 的任何文件（§8.3 收编事务除外，且必须用户确认）

---

## 14. 生效与日常使用

阶段一完成并建 Junction 后，新开会话即可用查询功能；面板和收编随 1.1/1.2 交付。

常用话术："我有哪些 Skill？""列出高频 Skill。""这个任务该用哪个 Skill？""XX 怎么用？""刷新索引并告诉我变化。""把 XX 标为高频/低频。""检查有没有没纳管的 Skill。""收编 XX（先给我看预检清单）。"

面板：`python panel/server.py`（或让 Agent 代启动），浏览器打开提示端口，用完即关。

日常原则：**Hub 只存原件，运行数据留在本机；扫描事实与人工标签文件级分离；skill_id 才是主键且跨机器稳定；扫描根失败不是删除；来源不明不是本地自建；有本地自建证据的收编进 Hub，外部 Skill 保留更新链；低频只代表少用，不代表应删；只推荐 active，drift 附警告，source-only 明说未安装。**
