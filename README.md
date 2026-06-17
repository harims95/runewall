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

## GitHub create issue execution

Runewall can execute one real mapped action right now: `github create_issue`.

It uses the GitHub REST API, not browser automation.

It requires `GITHUB_TOKEN` from the environment, and it does not store or log the token.

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

## Not built yet

- human approval/reject flow
- browser/web translation
- website maps
- auth
- dashboard
- TypeScript SDK
