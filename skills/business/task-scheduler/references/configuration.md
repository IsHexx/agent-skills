# Configuration

Use `config.local.json` for installation-specific values. Keep it out of version control.

## Required values

| Section | Key | Purpose |
|---|---|---|
| `source` | `kind` | `lark_base` or `local_file` |
| `source` | source identifier | The live task table or source file to update |
| `board` | `system_dir` | Directory containing sync and generator tools |
| `board` | `sync_command` | Refreshes the local task mirror from the source |
| `board` | `generate_command` | Generates board outputs from the local mirror |
| `field_map` | IDs, people, state, phase, and date fields | Maps the team's real schema to the generic workflow |

## Adaptation rules

- Use JSON arrays for commands. Do not store a shell pipeline in a command string.
- Keep `base_token`, paths, member IDs, and organization-specific select options only in `config.local.json`.
- Set `source.kind` to `local_file` only when the file is truly the source of record. Otherwise use the remote system as the source and treat local files as generated mirrors.
- Add optional values such as `member_allowlist`, `root_copy_command`, or alternate output paths only when the host workflow needs them.
- Validate all configured paths and commands with a read-only check before the first write.
