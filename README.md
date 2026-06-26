# Runewall

Runewall is a local-first safety/runtime layer for AI agents before they take real-world actions.

## Why it exists

Agents are moving from answering to acting. Before they touch files, APIs, or tools, developers need a local layer that can preview, explain, block, log, and rollback actions.

## Architecture flow

`Agent -> Runewall -> policy check -> dry-run -> review/execute/block -> log/audit`

## What Runewall can do now

- CLI-first safety runtime
- dry-run before mutation
- local SQLite action log
- `policy explain`, `policy test`, and `policy audit`
- snapshots and rollback
- guarded real execution for selected services
- local MCP stdio surface
- Python SDK preview
- community map package verification

## 5-minute quickstart

```powershell
python -m pip install -e ".[dev]"
runewall version
runewall config profile safe
runewall policy audit
runewall act github create_issue --dry-run --json --input repo=user/repo --input title="Bug"
runewall maps community package verify examples/community-maps --json
runewall mcp status --json
runewall sdk status --json
```

What this gives you:

- confirms the CLI is installed
- applies safe local defaults
- audits current policy settings
- previews a mapped action without mutating anything
- verifies a local community package without importing it
- shows local MCP status
- shows local SDK status

## Safety defaults

- real execution is disabled by default
- dry-run does not call external APIs
- tokens only come from environment variables
- tokens are never printed, stored, or logged
- community maps are non-executable
- package verify does not import or execute maps

## Install

See [docs/INSTALL.md](docs/INSTALL.md) for Windows PowerShell-first setup.

## Quickstart

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a safe first walkthrough.

## MCP

Runewall includes a local MCP stdio surface for agent safety checks.

```powershell
runewall mcp status
runewall mcp serve --once
runewall mcp serve
```

See [docs/MCP_CLIENT_EXAMPLES.md](docs/MCP_CLIENT_EXAMPLES.md) for more MCP examples.

## Python SDK preview

```python
from runewall.sdk import policy_test, dry_run

print(policy_test("map.execute"))
print(dry_run("github", "create_issue", {"repo": "user/repo", "title": "Bug"}))
```

- `runewall sdk status`
- `runewall sdk status --json`
- SDK is local-only
- `execute` is not exposed yet
- `dry_run` does not call external APIs

## Community package verify

Use community package verify as the recommended local gate before community map import or review.

```powershell
runewall maps community package verify examples/community-maps
runewall maps community package verify examples/community-maps --json
```

Verify checks manifest validation, SHA-256 checksums, signing status, trusted key status, and execution safety posture.

Verify does not import maps, execute maps, download remote files, or call external APIs.

## More docs

- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/QUICKSTART.md](docs/QUICKSTART.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/COMMUNITY_MAPS.md](docs/COMMUNITY_MAPS.md)
- [docs/PYTHON_SDK_EXAMPLES.md](docs/PYTHON_SDK_EXAMPLES.md)
