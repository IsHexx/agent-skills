# 运行时数据约定

默认状态目录：`%LOCALAPPDATA%\skill-catalog`。可使用脚本的 `-StateRoot` 指定隔离目录进行验证。

| 文件 | 性质 | 说明 |
|---|---|---|
| `config.json` | 配置 | 从 `config.example.json` 首次生成；定义扫描根和排除规则。 |
| `catalog.json` | 可重建事实 | 成功扫描生成的统一目录，不存放个人偏好。 |
| `health.json` | 状态 | 最近扫描的时间、结果、错误及索引版本；原子写入。 |
| `INDEX.md` | 可读视图 | 按高频、未分类、低频以及异常状态生成。 |
| `overrides.json` | 个人偏好 | `skill_id` 到频率、标签、备注和置顶的映射。 |
| `platform-plan.json` | 可重建计划 | 中央目录到各终端的链接预检结果。 |
| `platform-health.json` | 状态 | 最近一次平台适配检查的健康度、冲突与待创建链接。 |

## 中央目录与平台适配

`config.json` 中的 `canonical.path` 是唯一的用户自建 Skill 源目录，默认 `~/.agents/skills`。`platforms` 定义各终端如何使用该目录：

| `mode` | 行为 |
|---|---|
| `native` | 终端直接发现中央目录，不创建副本或链接。 |
| `junction` | 对每个含 `SKILL.md` 的中央目录项，在该终端目录创建同名 Windows Junction。已有路径一律记为冲突。 |
| `manual` | 仅记录待适配状态，不创建目录或链接。 |

平台脚本先执行 `-Plan` 或 `-Check`；只有 `-Apply -Confirmed` 才会创建缺失的 Junction。它不会删除、覆盖或替换任何已有目录。

## `catalog.json` 关键字段

`skill_id` 为 `name + "_" + SHA256(root_id + "/" + relative_path_lower)[0:12]`。它仅用于偏好关联；同一个逻辑 Skill 的多个来源通过 `aliases` 和 `sources` 聚合。

| 字段 | 含义 |
|---|---|
| `name` / `description` | 从 `SKILL.md` frontmatter 解析的规范元数据。 |
| `availability` | `active`、`source-only` 或 `unavailable`。 |
| `integrity` | `ok`、`drift` 或 `conflict`。 |
| `source_kind` | `local-authored`、`external`、`plugin-generated` 或 `unknown`。 |
| `adoptability` | `eligible`、`blocked`、`review-required` 或 `not-applicable`。 |
| `sources` | 每个实际目录的根、路径、内容哈希、运行环境和可用状态。 |
| `aliases` | 同名同内容或同一路径的合并项。 |

扫描规则：`SKILL.md` 必须含 UTF-8 frontmatter，且 frontmatter 中包含 `name` 和 `description`。支持单行引号、未引号值与 `|` / `>` 块文本。发现不符合规范的目录只记录为异常，不会阻止其他 Skill 入库。`relative_path` 是 Skill 目录相对扫描根的路径；同名但内容不同的项保持独立记录，不共享标签。

## 偏好文件示例

```json
{
  "schema_version": 1,
  "updated_at": "2026-08-04T00:00:00Z",
  "skills": {
    "lark-base_0123456789ab": {
      "frequency": "high",
      "category": "general",
      "tags": ["飞书", "数据表"],
      "note": "日常维护",
      "pinned": true
    }
  }
}
```

允许的频率为 `high`、`low` 与 `unclassified`。`catalog.json` 重新生成时不会改写该文件。
