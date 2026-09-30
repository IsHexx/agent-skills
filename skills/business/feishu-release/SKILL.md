---
name: feishu-release
description: Create Caibao blue-green or downtime release forms, optional PDF defect documents, archive them in Feishu Wiki, and send release notifications when explicitly requested. Use for 发版单、蓝绿发布、停服发版、PDF缺陷单、发版通知、测试群通知等请求。
---

# Feishu Release

Use this skill for the Caibao release workflow on this Windows machine. The canonical workspace and configuration are:

- Workspace: `D:\财宝\AgentWorkspace\_workspace\发版通知`
- Config: `D:\财宝\AgentWorkspace\_workspace\发版通知\release_notifier_config.json`
- Runner: `scripts/create_release_package.ps1`

Before acting, read [references/release-policy.md](references/release-policy.md). Also read the relevant installed Lark skills before using `lark-cli`: `lark-shared`, `lark-drive`, `lark-wiki`, `lark-doc`, and `lark-im` when sending notifications.

## Route The Request

Extract four decisions from the user's current request:

1. Release date and time. Use today's date only when the user says 今天/上午/下午/晚上. Stop if the date or time is ambiguous.
2. Release mode. Use `blueGreen` by default. Use `majorDowntime` only for explicit 大版本、停服、停机 wording.
3. Documents. “发版单” means the spreadsheet only. “两个单子”, “PDF也要”, or an explicit PDF request means spreadsheet plus PDF defect document.
4. Notification. Send nothing unless the user explicitly asks to notify/send to a group or people. A clear request to send is authorization for that exact group, recipients, and wording.

If the user supplies release items, convert them to JSON and pass them through `-ItemsJson`; do not invent missing owners, validation results, numbers, or remarks.

## Run

From the skill directory:

```powershell
./scripts/create_release_package.ps1 \
  -ReleaseDate 20260928 \
  -ReleaseTime 10:30 \
  -Mode blueGreen \
  -IncludePdf
```

For an explicit downtime release, keep the full downtime workbook and route with `majorDowntime`:

```powershell
./scripts/create_release_package.ps1 \
  -ReleaseDate 20260928 \
  -ReleaseTime 20:00 \
  -Mode majorDowntime \
  -IncludePdf \
  -Notify \
  -AtAll
```

Downtime release requests must use the configured full release workbook. Preserve its `版本发布计划`, `版本发布申请单`, and `版本发布测试报告` sheets and existing formatting. Do not replace it with the simplified blue-green form.

Add `-Notify -AtAll` only when the user explicitly requests a test-group notification. Use `-NotificationText` for user-provided wording; it supports `{sheetUrl}`, `{pdfUrl}`, `{date}`, and `{time}` placeholders.

For release rows:

```powershell
$items = @(
  @{ number = "CRM_20"; module = "CRM"; description = "账套按期收费" }
) | ConvertTo-Json -Compress

./scripts/create_release_package.ps1 \
  -ReleaseDate 20260928 \
  -ReleaseTime 16:30 \
  -Mode blueGreen \
  -ItemsJson $items
```

Use `-DryRun` to validate interpretation without creating local or Feishu resources. Use `-LocalOnly` only for offline template verification.

## Completion Standard

Treat the operation as complete only when the runner returns structured JSON with:

- `sheet.wikiUrl` and a successful Wiki move;
- `pdf.wikiUrl` when PDF was requested;
- `notification.messageId` when notification was requested.

Report failures exactly. Never simulate uploads, moves, mentions, attachments, or messages. If notification was not requested, state that no notification was sent.
