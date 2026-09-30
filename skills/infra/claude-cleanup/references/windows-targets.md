# Windows Cleanup Targets

## Remove By Default

| Category | Pattern |
|---|---|
| Claude Code npm package | global `@anthropic-ai/claude-code` |
| Claude Code companion npm packages | global `ccusage`, `ccstatusline`, `clawdhub` |
| Command shims | `%APPDATA%\npm\claude*`, `ccusage*`, `ccstatusline*`, `clawdhub*` |
| User config | `%USERPROFILE%\.claude`, `.claude.json`, `.claude.json.backup` |
| Installer archive | `%USERPROFILE%\anthropic-ai-claude-code-*.tgz` |
| Local cache | `%LOCALAPPDATA%\claude-cli-nodejs`, `%TEMP%\claude*` |
| VS Code extension | `%USERPROFILE%\.vscode\extensions\anthropic.claude-code-*` |
| VSIX cache | `%APPDATA%\Code\CachedExtensionVSIXs\anthropic.claude-code-*` |
| VS Code logs | `%APPDATA%\Code\logs\**\Anthropic.claude-code` |
| npx cache | `_npx` folders containing `ccusage`, `ccstatusline`, `clawdhub`, `claude-agent-acp`, or `@anthropic-ai` |

## Preserve By Default

| Category | Examples |
|---|---|
| Workspace rules | project `.claude`, `CLAUDE.md` |
| Other AI tools | `@openai/codex`, Lark CLI, `opencode-ai`, `agent-browser` |
| Third-party providers | OpenCode Anthropic provider files |
| Design tool templates | `getdesign/templates/claude.md`, `designlang/.claude` |

## Manual Review

If a scan finds `anthropic` under another actively installed tool, do not delete it automatically. Report it as optional and explain which parent tool owns it.
