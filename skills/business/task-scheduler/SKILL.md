---
name: task-scheduler
description: Update a team's task schedule and regenerate a person-level task board or Gantt chart. Use when users ask to schedule, reschedule, cancel, complete, assign, or summarize work; update a task list; regenerate a personnel board; or fill team-member availability. Supports a configured live task source plus local HTML/Excel board generation without assuming a specific agent product.
---

# Task schedule and personnel board

Use this skill to keep one live task source, its local mirror, and the generated personnel board consistent.

## Load configuration first

Read `config.local.json` before taking action. Resolve it in this order:

1. Path in `TASK_SCHEDULER_CONFIG`, if the host supports environment variables.
2. `config.local.json` next to this `SKILL.md`.
3. `.agent/task-scheduler.config.json` in the current project.

If no usable configuration exists, copy `config.example.json` to one of those locations and ask only for the required values. Do not write secrets, user IDs, task data, or machine paths into `SKILL.md`, `config.example.json`, or `references/`.

Read [configuration.md](references/configuration.md) when creating or validating configuration. Read [lark-cli.md](references/lark-cli.md) only when `source.kind` is `lark_base`.

## Rules

- Treat the configured live source as authoritative. Never update a local `.xlsx` as the source of record.
- Before a write, read the real schema and target records. Use IDs returned by the platform; do not infer them from names.
- For fuzzy task-title matches, present the matched task(s) and get confirmation before modifying an existing one. Create a separate task when the user confirms a distinct item.
- Validate write results: task title, owner, state, dates, and cleared fields. If the platform fills unwanted default dates, explicitly clear them and verify again.
- Refresh the local mirror and both configured board outputs after a successful source update. If files are locked, stop and ask the user to close them.
- Report changed and newly created tasks separately, including title, owner, start/end dates, and status.
- When the user reports "the source was updated but the board did not change," re-run the sync and inspect the specific records in the fresh mirror before concluding anything is broken. Most often the source edit simply happened after the last sync. Verify by record ID, then regenerate.

## Workflow

### 1. Resolve intent and dates

Extract the task, owner, required phase, status, and duration. Resolve relative dates using the real current date and state the resolved dates in the handoff.

Use the configured field map:

| User intent | Configured date fields |
|---|---|
| Test / execution work | `execution_start` / `execution_end` |
| Test-case writing | `case_start` / `case_end` |
| Actual completed work | `actual_start` / `actual_end` |
| Estimated test or launch dates | `expected_test` / `expected_launch` |
| Cancel / unschedule | Set the configured pending state and clear execution dates |

Do not guess an owner, a date range, or a task match. If the user says “fill the gaps,” calculate the selected member's unoccupied dates from the live source or the freshly synchronized mirror, then show the intended allocation before writing whenever the target task is ambiguous.

### 2. Read the source

For a remote source, obtain the actual table/schema and use the configured identifier fields. Query only necessary fields for a specific match; paginate or use server-side filtering for whole-team availability calculations.

For a local-file source, make a timestamped backup before mutation and preserve formulas, formatting, merged cells, and identifiers.

### 3. Write and verify

Apply source updates first. For new tasks, use the configured default values only after checking that the configured state, domain, test type, and priority exist in the source schema.

Board bars use actual dates first for every task, not only completed ones: when both actual boundaries are available they define the execution segment; if either is absent, fall back to the configured planned execution range. Keep the board segment label configured as `execution_label`; do not expose implementation-specific labels such as "planned execution" or "actual execution" unless the user asks.

### 4. Synchronize and generate

Run the configured `sync_command`, then `generate_command`. These commands are arrays, not shell snippets; preserve argument boundaries and resolve paths from `board.system_dir`.

Validate that expected outputs exist and show the requested date range. Do not claim a board was updated until both the source write and output generation succeed.

## Board calendar conventions

- Weekends and holidays render with the gray rest-day fill; no special annotation is needed for ordinary weekends.
- Exception: when a task's end date falls on a Saturday, that Saturday keeps the task bar color — a Saturday deadline means the schedule deliberately includes it.
- Officially adjusted workdays (调休补班) are treated as workdays everywhere: headers, idle detection, and task bars. Keep the generator's holiday list and adjusted-workday list current against the official State Council annual holiday arrangement; verify dates with a web search instead of guessing.
- A task that falls entirely on rest days must still be drawn, so it does not vanish from the board.
- The board's custom-color feature must remap the bar color inside the per-day gradient, never overwrite the bar with a solid inline background; otherwise rest-day gray segments are silently hidden whenever a stored theme is applied.

## Default monthly-history policy

When `history.month_start_days` is configured, a generation run during those first calendar days shows only the preceding complete week as historical lookback. Completed tasks use actual dates first and fall back to estimated execution dates only when the actual range is incomplete.

Keep the policy in configuration so each team can change its own month-start window, completed states, and lookback period.
