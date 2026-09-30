---
name: skill-catalog
description: 查询、搜索、刷新和维护本机 Skill 目录；当用户想找可用 Skill、区分高低频、核查安装或完整性、处理重复来源或管理 Skill 清单时使用。
---

# Skill 目录

维护本机 Skill 的可查询目录。用户自建 Skill 的唯一源目录为 `~/.agents/skills/`；Kimi Code 原生发现该目录，Codex 等终端通过受管目录链接复用同一份 Skill。目录只记录扫描到的事实；个人使用频率、备注和置顶等偏好保存在独立覆盖文件中。

## 先判断是否需要刷新

脚本路径：`scripts/sync-index.ps1`。

1. 先运行 `-Check`。退出码为 `0` 时可直接使用现有目录。
2. 退出码为 `2` 时运行 `-Rebuild`，再读取生成的 `INDEX.md` 或 `catalog.json`。
3. 退出码为 `1` 时保留旧目录，并将错误与时间写入 `health.json`；向用户说明目录可能过期，不要把空结果当成已卸载。

```powershell
& "$PSScriptRoot/scripts/sync-index.ps1" -Check
& "$PSScriptRoot/scripts/sync-index.ps1" -Rebuild
```

## 回答用户的检索请求

读取运行时目录下的 `catalog.json`、`overrides.json` 和 `health.json`：

- 按 `name`、`description`、`source_kind` 与标签筛选；先返回健康、可用、匹配度高的 Skill。
- 高频/低频由 `overrides.json` 的 `frequency` 决定，未标注则显示为“未分类”，不要依据名称猜测。
- 同名或相同内容的多个来源应合并显示，并列出主来源与别名；内容不一致时标记为“冲突”，不要静默挑一个。
- `availability=source-only` 表示目录来源存在、当前运行环境未安装；推荐前说明需先安装或采用。
- 外部/插件 Skill 默认只可索引和跳转，不能纳入自维护 Hub；本地自建 Skill 才进入后续“采用”流程。

## 可用命令

```powershell
# 仅检查索引是否过期：0=可用、2=需重建、1=检查异常
& "$PSScriptRoot/scripts/sync-index.ps1" -Check

# 全量扫描、生成 catalog.json / health.json / INDEX.md
& "$PSScriptRoot/scripts/sync-index.ps1" -Rebuild

# 查看跨终端适配计划（只读）
& "$PSScriptRoot/scripts/sync-platforms.ps1" -Plan

# 创建缺失的安全目录链接；同名冲突会中止，绝不覆盖
& "$PSScriptRoot/scripts/sync-platforms.ps1" -Apply -Confirmed

# 导出或导入个人偏好（频率、标签、备注）
& "$PSScriptRoot/scripts/sync-index.ps1" -ExportPreferences -Path .\skill-preferences.json
& "$PSScriptRoot/scripts/sync-index.ps1" -ImportPreferences -Path .\skill-preferences.json

# 只生成收编预检计划；确认计划内容后才可提交
& "$PSScriptRoot/scripts/sync-index.ps1" -AdoptPlan <skill_id>
& "$PSScriptRoot/scripts/sync-index.ps1" -AdoptCommit <plan_id> -Confirmed
```

运行时文件默认位于 `%LOCALAPPDATA%\skill-catalog\`。首次运行会由 `config.example.json` 生成 `config.json` 与空的 `overrides.json`；配置根目录、排除规则或深度前，先阅读 [schema.md](references/schema.md)。

## 修改边界

- 不能修改、搬迁或删除原始 Skill，除非用户明确授权。
- 不能因为一个扫描根不可用而清空旧索引；必须保留上一次成功结果。
- `catalog.json` 是可重建事实，个人分类只能写入 `overrides.json`。
- 导入偏好时仅合并符合格式的数据；无效条目保留原覆盖文件并报错。
- 收编预检不会改动任何 Skill；提交必须明确确认，且仅允许复制计划内白名单文件。来源变化、敏感文件或中央目录同名冲突时必须中止。
- 平台适配仅能从中央目录向平台目录创建缺失的目录链接；任何已有同名路径都视为冲突，不可自动覆盖。

## 本地面板

按需启动 `panel/server.py`，服务只绑定 `127.0.0.1`，会自动避开已占端口。面板支持检索、筛选、查看完整 `SKILL.md`、编辑个人标签、刷新索引、查看平台适配健康状态，以及对 eligible 项生成收编预检。

```powershell
python "$PSScriptRoot/panel/server.py"
```

面板中的“确认收编”相当于命令行的 `-Confirmed`；它不会自动选择 unknown、external 或 plugin-generated 条目。
