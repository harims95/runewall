# Runewall

Runewall is a local-first runtime for recording agent actions safely.

This starter implements only the initial Python package skeleton and Week 1 core:

- package metadata via `pyproject.toml`
- SQLite bootstrap for `.runewall/runewall.db`
- core dataclasses for actions, snapshots, rules, and checkpoints
- a minimal `runewall init` CLI
- tests for storing and listing actions

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
runewall init
pytest tests -v
```

## Command overview

All commands support `--json` for machine-readable output. Human output is the default. Tokens are never printed or stored.

**Setup**

```
runewall init                  Initialize .runewall in the current directory
runewall init --json           Same, returns JSON with database_path and config_path
runewall version               Print version
runewall version --json        Print version as JSON
runewall doctor                Print a local health check
runewall doctor --json         Same, returns JSON
```

**Action history**

```
runewall status                Show total actions, counts by status, latest action
runewall status --json         Same, returns JSON
runewall log                   List all recorded actions
runewall log --json            Same, returns JSON array
runewall pending               List pending actions awaiting review
runewall pending --json        Same, returns JSON
```

**Safety control**

```
runewall approve ACTION_ID     Mark a pending action as approved
runewall approve ACTION_ID --json
runewall reject ACTION_ID      Mark a pending action as rejected
runewall reject ACTION_ID --json
runewall execute ACTION_ID     Execute an approved file.delete action
runewall execute ACTION_ID --json
runewall rollback ACTION_ID    Roll back a recorded action from its snapshot
runewall rollback ACTION_ID --json
runewall rollback --last       Roll back the most recent action
runewall rollback --last --json
```

**Config**

```
runewall config path           Show the config file path
runewall config path --json    Same, returns JSON with path and exists
runewall config show           Print the current config (secrets redacted)
runewall config show --json    Same, returns JSON
runewall config set KEY VALUE  Set a config value
runewall config set KEY VALUE --json
```

Real map execution is disabled by default. Enable it with:

```bash
runewall config set maps.allow_execute true
```

**Maps**

```
runewall maps list             List bundled site maps
runewall maps list --json      Same, returns JSON
runewall maps show SITE        Show flows for a site map
runewall maps show SITE --json Same, returns JSON
runewall maps validate         Validate bundled site maps
runewall maps validate --json  Same, returns JSON (ok true/false)
runewall maps path             Show the bundled maps directory
```

**Actions (dry-run and execute)**

Dry-run never calls any API. It only plans.

```
runewall act github create_issue --dry-run --input repo=user/repo --input title="Bug"
runewall act github create_issue --dry-run --json --input repo=user/repo --input title="Bug"
runewall act github create_issue --execute --input repo=user/repo --input title="Bug"
```

`--execute` requires `maps.allow_execute = true` and `GITHUB_TOKEN` in the environment.

**Read**

```
runewall read https://example.com         Fetch a URL without a browser
runewall read https://example.com --json  Same, returns JSON with title, headings, text
```

**Cleanup**

```
runewall cleanup snapshots         Delete old snapshot directories
runewall cleanup snapshots --json  Same, returns JSON with deleted_count and retention_days
```

## Manual Demo

```bash
python examples/file_rollback_demo.py
type demo.txt
runewall rollback --last
type demo.txt
```

## Current working features

- `runewall init`
- `runewall log`
- `runewall status`
- `runewall doctor`
- `runewall rollback --last`
- `protect_file_create`
- `protect_file_write`
- `protect_file_delete`

## Current working demo

1. Initialize Runewall:

```bash
runewall init
```

2. Create `demo.txt`:

```bash
echo "original content" > demo.txt
```

3. Use `protect_file_write`:

```python
from pathlib import Path
from runewall import protect_file_write

with protect_file_write("demo.txt"):
    Path("demo.txt").write_text("changed by interceptor")
```

4. View log:

```bash
runewall log
```

5. Rollback:

```bash
runewall rollback --last
```

6. Confirm file restored:

```bash
type demo.txt
```

In simple terms, Runewall snapshots the file before mutation, logs the action, marks it as `success` if the write completes, and `rollback` restores the original content.

## Simple example

1. Initialize Runewall:

```bash
runewall init
```

2. Create the original file:

```bash
echo "original content" > demo.txt
```

3. Change it with `protect_file_write`:

```python
from pathlib import Path
from runewall import protect_file_write

with protect_file_write("demo.txt"):
    Path("demo.txt").write_text("changed by interceptor")
```

4. Show the logged action:

```bash
runewall log
```

5. Restore the file:

```bash
runewall rollback --last
type demo.txt
```

## Review flow

Actions with `REVIEW` policy are logged as `pending` and do not execute immediately.

Users can inspect pending actions with:

```bash
runewall pending
```

Users can approve an action with:

```bash
runewall approve ID
```

`approve ID` changes a pending action to `approved`.

Users can execute an approved action with:

```bash
runewall execute ID
```

`execute ID` runs an approved action if it is supported.

Users can reject an action with:

```bash
runewall reject ID
```

Delayed execution currently supports only approved `file.delete`.

Execution snapshots the file before deleting it, and `rollback` can restore the deleted file.

## Universal Read Mode

Runewall can read a normal webpage without browser automation.

It uses `httpx` + `BeautifulSoup`, with:

- no Playwright
- no LLM
- no API key
- no external hosted service

CLI usage:

```bash
runewall read https://example.com
```

Python usage:

```python
from runewall import read_url

content = read_url("https://example.com")
```

Returned fields:

- `url`
- `title`
- `headings`
- `text`

## Action maps and dry-run planning

Runewall can load bundled site action maps without using browser automation.

Dry-run never calls any external API. It only reads the map, validates inputs, and builds a plan.

Currently bundled maps:

| Site | Flow | Execution |
|---|---|---|
| Cloudflare | `list_zones` | dry-run + real API |
| Discord | `send_message` | dry-run only |
| GitHub | `create_issue` | dry-run + real API |
| Linear | `create_issue` | dry-run only |
| Netlify | `list_sites` | dry-run + real API |
| Slack | `send_message` | dry-run only |
| Supabase | `list_projects` | dry-run + real API |
| Vercel | `list_projects` | dry-run + real API |

`Cloudflare`, `GitHub`, `Netlify`, `Supabase`, and `Vercel` maps have real API execution. `Discord`, `Linear`, and `Slack` are dry-run and planning only.

Real execution is disabled by default. To enable it:

```bash
runewall config set maps.allow_execute true
```

To disable again:

```bash
runewall config set maps.allow_execute false
```

Dry-run does not require tokens and never calls external APIs. Tokens are read only from environment variables and are never printed, stored, or logged.

List bundled maps with:

```bash
runewall maps list
```

Inspect a map with:

```bash
runewall maps show github
runewall maps show slack
runewall maps validate
runewall maps path
```

Filter maps by category or tag:

```bash
runewall maps list --category deployment
runewall maps list --tag chat
runewall maps list --category deployment --json
```

Categories group maps by purpose (`deployment`, `communication`, `development`, `infrastructure`, `backend`, `project_management`). Tags help agents discover maps by capability. Filtering and searching never execute anything — they only read map metadata.

Search across map key, site name, category, tags, flow names, and flow descriptions:

```bash
runewall maps search deploy
runewall maps search chat
runewall maps search unknown --json
```

`maps search QUERY --json` returns `{"query": "...", "count": N, "maps": [...]}`. Count is 0 and maps is empty if nothing matches. JSON output is available for automation.

Get a summary of the map registry:

```bash
runewall maps stats
runewall maps stats --json
```

`maps stats` shows total maps, total flows, maps by category, maps with real execution support, and dry-run-only maps. Most bundled maps are dry-run only. Only `github create_issue` has real execution currently.

Export the full registry for agents and tools that need all map data:

```bash
runewall maps export --json
```

This prints all maps as JSON including site metadata, category, tags, and full flow details. Export never executes anything.

Dry-run planning also never calls external APIs. It only reads the map, validates inputs, and shows a plan.

Plan a mapped action safely with:

```bash
runewall act github create_issue --dry-run --input repo=user/repo --input title="Bug report" --input body="Details"
```

This dry-run does not call GitHub, does not open a browser, and does not mutate anything.

If Runewall is initialized, the dry-run is logged as `map.dry_run`.

No browser automation is used for these maps.

## Local config

`runewall init` creates `.runewall/config.toml` in the current directory.

The default config looks like this:

```toml
[safety]
default_policy = "review"
max_snapshot_mb = 500

[retention]
snapshot_days = 30

[maps]
allow_execute = false

[auth]
github_token_env = "GITHUB_TOKEN"
```

Print the config file location:

```bash
runewall config path
```

Print the current config (secret-like values are redacted):

```bash
runewall config show
```

Set a config value:

```bash
runewall config set maps.allow_execute true
runewall config set maps.allow_execute false
runewall config set safety.max_snapshot_mb 100
runewall config set retention.snapshot_days 30
runewall config set auth.github_token_env GITHUB_TOKEN
```

`config set` behavior:

- If `.runewall/config.toml` does not exist, it is created with defaults first.
- Only known config keys are accepted. Unknown keys fail with a clear error.
- Invalid values (wrong boolean, non-integer) fail with a clear error.
- Secret-like values are not printed in the success output.

`maps.allow_execute` controls whether real map execution is allowed:

- `false` (default): real execution is blocked. Dry-run still works normally.
- `true`: real execution is permitted.

Dry-run map planning works without changing any config.

To run `github create_issue` for real, you need both:

1. `maps.allow_execute = true` in `.runewall/config.toml`
2. `GITHUB_TOKEN` set in the environment

If either is missing, execution fails with a clear error and nothing is sent to GitHub.

The config is local-first. It is never uploaded or sent anywhere.

`GITHUB_TOKEN` is always read from the environment only. It is never printed, stored in the config file, or written to the action log.

## Real map execution

Five bundled maps support real API execution. All others are dry-run and planning only.

Real execution is disabled by default. Enable it:

```bash
runewall config set maps.allow_execute true
```

Disable again when done:

```bash
runewall config set maps.allow_execute false
```

Each map requires its own token in the environment. Tokens are read only from environment variables and are never printed, stored in config, or written to the action log. Dry-run never requires tokens and never calls external APIs.

**Cloudflare list_zones** — requires `CLOUDFLARE_API_TOKEN`

```bash
set CLOUDFLARE_API_TOKEN=your_token_here
runewall act cloudflare list_zones --execute
```

**GitHub create_issue** — requires `GITHUB_TOKEN`

```bash
set GITHUB_TOKEN=your_token_here
runewall act github create_issue --execute --input repo=user/repo --input title="Bug" --input body="Details"
```

**Vercel list_projects** — requires `VERCEL_TOKEN`

```bash
set VERCEL_TOKEN=your_token_here
runewall act vercel list_projects --execute
```

**Netlify list_sites** — requires `NETLIFY_TOKEN`

```bash
set NETLIFY_TOKEN=your_token_here
runewall act netlify list_sites --execute
```

**Supabase list_projects** — requires `SUPABASE_ACCESS_TOKEN`

```bash
set SUPABASE_ACCESS_TOKEN=your_token_here
runewall act supabase list_projects --execute
```

All require `allow_execute = true` in `.runewall/config.toml`. See [Local config](#local-config).

If Runewall is initialized, execution is logged as `map.execute`.

If a token is missing, execution fails with a clear error and nothing is sent to the external service.

`runewall maps stats` shows which maps have real execution support and which are dry-run only.

Tests use mocks. Do not use real tokens unless you intentionally want to call the external API.

## Doctor

`runewall doctor` prints a simple local health check.

It checks:

- Python version
- whether `.runewall/runewall.db` exists
- whether required dependencies like `httpx` and `bs4` are installed
- whether `GITHUB_TOKEN`, `VERCEL_TOKEN`, `NETLIFY_TOKEN`, and `SUPABASE_ACCESS_TOKEN` are set without printing their values
- bundled maps count
- a final `OK`, `WARN`, or `FAIL` summary

`runewall maps stats` shows a breakdown of real-execution maps vs dry-run-only maps.

## Agent-readable JSON output

Runewall supports machine-readable JSON output for agents and automation.

Add `--json` to any supported command and it prints valid JSON only — no headers, no decorators, no human messages.

Human output is still available by omitting `--json`.

Key behaviors:

- JSON mode prints valid JSON only. Nothing else is written to stdout.
- Human output remains unchanged when `--json` is not used.
- Dry-run JSON never executes real actions. It only plans.
- Real execution is still guarded by config (`maps.allow_execute`) and environment tokens.
- Dry-run and execute JSON include policy fields so agents can explain the effective decision.
- Token values are never printed in any mode.

### Supported commands

**Initialize:**

```bash
runewall init --json
```

```json
{ "ok": true, "initialized": true, "database_path": "...", "config_path": "..." }
```

**Status:**

```bash
runewall status --json
```

```json
{ "initialized": true, "database_path": "...", "total_actions": 3, "pending_count": 1, "latest_action": { ... } }
```

**Action log:**

```bash
runewall log --json
```

```json
[{ "id": "...", "action_type": "file.write", "target": "demo.txt", "status": "success", "params": {}, "result": {} }]
```

**Pending actions:**

```bash
runewall pending --json
```

```json
{ "initialized": true, "pending": [{ "id": "...", "action_type": "file.delete", "status": "pending", ... }] }
```

**Maps:**

```bash
runewall maps list --json
runewall maps show github --json
runewall maps validate --json
```

`maps list --json` returns a list of bundled maps with flow names and counts.

`maps show github --json` returns the full site map including flow metadata and required inputs.

`maps validate --json` returns `{ "ok": true, "results": [...] }`. If any map is invalid, `ok` is `false` and the exit code is non-zero.

**Dry-run planning:**

```bash
runewall act github create_issue --dry-run --json --input repo=user/repo --input title="Bug" --input body="Details"
```

```json
{
  "ok": true,
  "executed": false,
  "site": "github",
  "flow": "create_issue",
  "description": "Create a GitHub issue",
  "risk_level": "low",
  "reversible": true,
  "requires_auth": true,
  "provided_inputs": {
    "repo": "user/repo",
    "title": "Test issue"
  },
  "missing_inputs": [],
  "api_path": {
    "method": "POST",
    "url": "/repos/{repo}/issues"
  },
  "ui_steps_count": 0,
  "policy": "auto",
  "decision": "allow",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_dry_run = \"auto\""
}
```

The policy fields tell agents why the dry-run is allowed or constrained:

- `policy`: `auto`, `snapshot`, `review`, or `block`
- `decision`: `allow`, `snapshot_required`, `review_required`, or `blocked`
- `policy_source`: where the policy came from
- `policy_reason`: a short explanation of the match

Dry-run still never calls external APIs.

If required inputs are missing, `ok` is `false`, `error` describes what is missing, and `error_code` is `INVALID_INPUT`.

**Real execution JSON:**

```bash
runewall act vercel list_projects --execute --json
```

Success:

```json
{
  "ok": true,
  "executed": true,
  "site": "vercel",
  "flow": "list_projects",
  "result": { "project_count": 2, "projects": [...] },
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

Error — blocked by config:

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
  "error_code": "EXECUTION_DISABLED",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

Error — missing token:

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "...",
  "error_code": "MISSING_TOKEN",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

Error â€” blocked by policy before any external API call:

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Execution blocked by policy for map.execute.",
  "error_code": "POLICY_BLOCKED",
  "policy": "block",
  "decision": "blocked",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"block\""
}
```

`--execute` is still disabled by default by `maps.allow_execute`. A `block` policy prevents execute before any external API call is made.

Stable `error_code` values: `EXECUTION_DISABLED`, `MISSING_TOKEN`, `UNSUPPORTED_EXECUTION`, `API_ERROR`, `POLICY_BLOCKED`, `UNKNOWN_SITE`, `UNKNOWN_FLOW`, `INVALID_INPUT`.

See [docs/agent-json-schema.md](docs/agent-json-schema.md) for the full JSON schema reference including all shapes and error codes.

**Config:**

```bash
runewall config path --json
runewall config show --json
```

`config path --json` returns `{ "path": "...", "exists": true }`.

`config show --json` returns the full config as a nested object. Secret-like values are redacted. If the config file is missing, defaults are returned and `"exists": false` is included.

**Doctor:**

```bash
runewall doctor --json
```

```json
{
  "python": { "version": "3.13.0", "ok": true },
  "database": { "present": true, "path": "..." },
  "config": { "present": true, "path": "...", "map_execution": "disabled" },
  "dependencies": { "httpx": true, "bs4": true },
  "auth": { "github_token": "present" },
  "maps": { "bundled_count": 4 },
  "summary": "OK"
}
```

`auth.github_token` is `"present"` or `"missing"` — the actual token is never printed.

**Cleanup:**

```bash
runewall cleanup snapshots --json
```

```json
{ "ok": true, "snapshots_directory_exists": true, "deleted_count": 2, "retention_days": 30 }
```

**Read:**

```bash
runewall read https://example.com --json
```

```json
{ "ok": true, "url": "https://example.com", "title": "...", "headings": [...], "text": "...", "logged": true }
```

`logged` is `true` if Runewall is initialized and the action was recorded, `false` otherwise.

If the read fails, `ok` is `false`, `error` describes the failure, and the exit code is non-zero.

## Not built yet

- human approval/reject flow
- browser/web translation
- website maps
- auth
- dashboard
- TypeScript SDK
