# Release Policy

## Canonical Sources

Read `release_notifier_config.json` at execution time. Do not hard-code values that the config already owns. The current config selects:

- Blue-green template: `蓝绿发版申请单-模板.xlsx`
- Downtime template: `版本发布相关表单-模板.xlsx`
- PDF template: `pdfTemplateDocToken`
- Formal Wiki root: `wikiSpaceId` + `wikiParentToken`
- Test group: `releaseChat.chatId`

Never edit an Excel template directly. Always create a dated copy in the configured output directory.

## Mode Rules

| User intent | Mode | Default time when omitted |
|---|---|---|
| ordinary release, 发版, 蓝绿发布 | `blueGreen` | 16:30 |
| 大版本, 停服, 停机 | `majorDowntime` | 20:00 |

An explicit time always wins. Do not simplify or restructure the downtime template. Fill only dates, time, clear placeholders, and user-provided release content.

The downtime workflow is fully supported, not an exception path. It creates the complete configured release workbook, imports it as a Feishu Sheet, archives it under the formal Wiki root, optionally creates the PDF defect child document, and optionally sends the requested notification. The workbook must retain these sheets when present:

- `版本发布计划`
- `版本发布申请单`
- `版本发布测试报告`

## File And Wiki Rules

- Spreadsheet title includes `YYYYMMDDHHmm` so multiple releases on one day do not collide.
- Blue-green file: `YYYYMMDDHHmm蓝绿发布申请单.xlsx`.
- Downtime file: `YYYYMMDDHHmm版本发布相关表单.xlsx`.
- PDF document: `【YYYYMMDDHHmm缺陷发版】PDF缺陷目标文件`.
- Import Excel as a Feishu Sheet, never as a normal attachment.
- Move the Sheet under the formal Wiki root.
- Move the PDF defect document under that release Sheet's Wiki node.
- The PDF default contains only 版本信息、缺陷清单、签字确认, with one blank defect row.

Before creating, search for an exact same title under the target Wiki parent. If an exact match exists, inspect and reuse it instead of creating a duplicate unless the user explicitly asks for another copy.

## Release Content

Preserve the user's line breaks. One release item per row; do not combine multiple items into one cell when they are separately listed.

Supported item keys for the runner:

| Meaning | JSON key |
|---|---|
| 编号 | `number` |
| 模块 | `module` |
| 子模块 | `submodule` |
| 需求/BUG描述 | `description` |
| 参与人 | `participants` |
| 验证结果 | `validation` |
| 备注 | `notes` |

Leave unspecified fields blank. Never infer business owners or validation status.

## Notification Rules

- Send only when explicitly requested.
- Use bot identity for group messages; use user identity for Drive, Docs, Sheets, and Wiki operations.
- “通知到测试群” uses the configured test group and the established `@所有人` convention unless the user names specific recipients instead.
- Keep multiple release items on separate lines.
- Do not include wording such as `附：YYYYMMDD版本发布相关表单`.
- Include the Feishu Wiki link to the release Sheet.
- If the user requests a real file attachment, that is a separate IM upload/send operation. Do not claim a link is an attachment.
- Success requires an actual `message_id` from `lark-cli`.

## Failure Rules

Stop and report when:

- user authentication cannot refresh;
- required scopes are missing;
- date/time is ambiguous;
- templates or config are missing;
- Wiki move fails;
- bot is not in the target group;
- a requested mention lacks a resolvable open_id/user_id;
- the CLI does not return a success result.

The final result should include the release mode, date/time, local file, Sheet Wiki link, PDF Wiki link when applicable, notification recipients, message ID when applicable, and any failure summary.
