---
name: claude-cleanup
description: Audit and clean Claude Code global installs, npm packages, user config, caches, VS Code extension remnants, and Claude Code companion tools on Windows. Use when preparing another device for a clean Claude Code uninstall or troubleshooting leftover Claude-related files while preserving workspace files such as .claude and CLAUDE.md.
---

# Claude Cleanup

Use this skill to remove Claude Code global/user-level remnants from a Windows device while preserving project/workspace files.

## Safety Rules

- Do not reset device identifiers or bypass account enforcement.
- Audit first unless the user explicitly asks to clean.
- Preserve workspace folders by default; do not delete project `.claude` or `CLAUDE.md`.
- Delete only known user-level install/config/cache/log paths.
- Report OpenCode/design-tool Anthropic provider files as optional; do not delete them by default.

## Workflow

1. Read `references/windows-targets.md` for target categories.
2. Run audit mode:

```powershell
.\scripts\claude-cleanup.ps1 -AuditOnly -PreserveWorkspace "D:\财宝\AgentWorkspace","D:\财宝\AgentWorkspace\_workspace"
```

3. If cleanup is confirmed or already requested, run:

```powershell
.\scripts\claude-cleanup.ps1 -Clean -PreserveWorkspace "D:\财宝\AgentWorkspace","D:\财宝\AgentWorkspace\_workspace"
```

4. Re-run audit mode and report remaining items.

## Cleanup Scope

Default cleanup includes:

- global npm packages: `@anthropic-ai/claude-code`, `ccusage`, `ccstatusline`, `clawdhub`
- command shims: `claude`, `ccusage`, `ccstatusline`, `clawdhub`
- user config: `%USERPROFILE%\.claude`, `.claude.json`, `.claude.json.backup`
- local caches: `%LOCALAPPDATA%\claude-cli-nodejs`, `%TEMP%\claude*`
- VS Code extension remnants: `anthropic.claude-code-*`, VSIX cache, Claude extension logs
- npx caches clearly containing Claude Code companion tools

Default cleanup excludes:

- workspaces passed through `-PreserveWorkspace`
- `opencode` Anthropic provider dependencies
- design tools whose templates mention Claude
- unrelated tools such as Codex, Lark CLI, OpenCode, and browser agents
