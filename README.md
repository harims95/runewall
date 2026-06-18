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

Currently bundled maps:

- `GitHub`: `create_issue`
- `Vercel`: `list_projects`
- `Netlify`: `list_sites`
- `Cloudflare`: `list_zones`

List bundled maps with:

```bash
runewall maps list
```

Inspect bundled maps with:

```bash
runewall maps show github
runewall maps show vercel
runewall maps show netlify
runewall maps show cloudflare
runewall maps validate
runewall maps path
```

Plan a mapped action safely with:

```bash
runewall act github create_issue --dry-run --input repo=user/repo --input title="Bug report" --input body="Details"
```

This dry-run does not call GitHub, does not open a browser, and does not mutate anything.

If Runewall is initialized, the dry-run is logged as `map.dry_run`.

Only `GitHub create_issue` has real API execution right now.

`Vercel`, `Netlify`, and `Cloudflare` are dry-run and planning maps only for now.

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

## GitHub create issue execution

Runewall can execute one real mapped action right now: `github create_issue`.

It uses the GitHub REST API, not browser automation.

It requires `GITHUB_TOKEN` from the environment, and it does not store or log the token.

It also requires `allow_execute = true` in `.runewall/config.toml`. See [Local config](#local-config).

If Runewall is initialized, execution is logged as `map.execute`.

If execution succeeds, the result includes issue number and issue URL when GitHub returns them.

If `GITHUB_TOKEN` is missing, execution fails safely and logs `failed` if Runewall is initialized.

Usage:

```bash
set GITHUB_TOKEN=your_token_here

runewall act github create_issue --execute --input repo=user/repo --input title="Bug report" --input body="Details"
```

Tests use mocks.

Do not use a real token unless you intentionally want to create a real GitHub issue.

## Doctor

`runewall doctor` prints a simple local health check.

It checks:

- Python version
- whether `.runewall/runewall.db` exists
- whether required dependencies like `httpx` and `bs4` are installed
- whether `GITHUB_TOKEN` is set without printing the token value
- bundled maps count
- a final `OK`, `WARN`, or `FAIL` summary

## Agent-readable JSON output

Runewall supports machine-readable JSON output for agents and automation.

Add `--json` to any supported command and it prints valid JSON only — no headers, no decorators, no human messages.

Human output is still available by omitting `--json`.

Key behaviors:

- JSON mode prints valid JSON only. Nothing else is written to stdout.
- Human output remains unchanged when `--json` is not used.
- Dry-run JSON never executes real actions. It only plans.
- Real execution is still guarded by config (`maps.allow_execute`) and environment tokens.
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
  "risk_level": "low",
  "reversible": true,
  "requires_auth": true,
  "provided_inputs": { "repo": "user/repo", "title": "Bug", "body": "Details" },
  "missing_inputs": [],
  "api_path": null,
  "ui_steps_count": 0
}
```

If required inputs are missing, `ok` is `false`, `error` describes what is missing, and the exit code is non-zero.

`--json` is only valid with `--dry-run`. Using `--json` with `--execute` exits non-zero with a clear error.

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
