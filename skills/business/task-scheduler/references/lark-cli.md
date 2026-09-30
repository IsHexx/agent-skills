# Lark Base adapter

Use this adapter only when `source.kind` is `lark_base` and `lark-cli` is available.

1. Resolve a supplied Wiki or Base URL with `lark-cli base +url-resolve --url <url> --as <identity>`; use the returned Base token, never a Wiki token.
2. Read table fields with `lark-cli base +field-list` before a write.
3. Locate known records with `+record-get`; locate title matches with `+record-search` using the configured title field.
4. Update one record with `+record-upsert --record-id <id> --json <field-map>`.
5. Create multiple records with `+record-batch-create`; resolve and write user IDs, not display names.
6. Clear unwanted default fields with `null` through `+record-upsert` or `+record-batch-update`, then read them back.

Use `--as user` unless the user explicitly requests an app identity. Handle authorization failures through the installed Lark authentication workflow; never simulate a successful remote write.
