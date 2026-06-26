# Runewall

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Local-first](https://img.shields.io/badge/local--first-yes-lightgrey.svg)
![CLI-first](https://img.shields.io/badge/cli--first-yes-lightgrey.svg)
![MCP-ready](https://img.shields.io/badge/MCP-ready-orange.svg)
![Tests](https://img.shields.io/badge/tests-local-blueviolet.svg)

Runewall is a local-first safety/runtime layer for AI agents before they take real-world actions.

## Why Runewall?

Agents are moving from answering to acting. Once agents touch files, APIs, tools, or external systems, developers need a boundary layer that can preview actions, explain policy decisions, block risky behavior, log what happened, and rollback where possible.

## What is it?

Runewall is a local-first CLI and developer tool that sits between an agent and a real action. It helps you inspect what an agent is about to do before you let it touch the outside world.

## Why does it matter?

When agents move beyond chat and start acting on files, services, and tools, mistakes get more expensive. A local safety/runtime layer gives you a clearer review point before that action happens.

## Architecture flow

`Agent -> Runewall -> policy check -> dry-run -> review/execute/block -> log/audit`

## How do I try it?

Start with the five-minute quickstart below, or run the 60-second local demo in [demos/README.md](demos/README.md).

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

Open this folder in VS Code, then run:

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

## Status

Runewall is currently a local-first CLI/devtool with:

- core safety runtime
- MCP stdio surface
- Python SDK preview
- community package verification

## Safe by default

- real execution is disabled by default
- dry-run does not call external APIs
- tokens only come from environment variables
- tokens are never printed, stored, or logged
- community maps are non-executable
- package verify does not import or execute maps
- no hosted backend is required

## What is not included yet?

- hosted service
- dashboard
- remote registry
- real signature verification
- community map execution

## Install

See [docs/INSTALL.md](docs/INSTALL.md) for Windows PowerShell-first setup.

## Install status

- local editable install is supported
- PyPI publishing is future work
- use [docs/INSTALL.md](docs/INSTALL.md) for setup
- see [docs/PACKAGING.md](docs/PACKAGING.md) for local packaging notes
- `runewall package pypi-check` is a local readiness check only
- `runewall package dist-check` is a local artifact presence check only

## Quickstart

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a safe first walkthrough.

## Demo

See [demos/README.md](demos/README.md) for a 60-second local-only, token-free demo.

## 60-second demo

Run the local demo with:

```powershell
.\demos\runewall_60_second_demo.ps1
```

It shows:

- version
- safe profile
- policy audit
- dry-run
- community package verify
- MCP status
- SDK status

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
- [docs/PACKAGING.md](docs/PACKAGING.md)
- [docs/QUICKSTART.md](docs/QUICKSTART.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [demos/README.md](demos/README.md)
- [docs/COMMUNITY_MAPS.md](docs/COMMUNITY_MAPS.md)
- [docs/PYTHON_SDK_EXAMPLES.md](docs/PYTHON_SDK_EXAMPLES.md)
