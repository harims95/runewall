# Runewall

[![PyPI](https://img.shields.io/pypi/v/runewall.svg)](https://pypi.org/project/runewall/)
[![CI](https://github.com/harims95/runewall/actions/workflows/ci.yml/badge.svg)](https://github.com/harims95/runewall/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Local-first](https://img.shields.io/badge/local--first-yes-lightgrey.svg)
![CLI-first](https://img.shields.io/badge/cli--first-yes-lightgrey.svg)
![MCP-ready](https://img.shields.io/badge/MCP-ready-orange.svg)

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

Install and run:

```powershell
pip install runewall
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

For local development, use `pip install -e ".[dev]"` instead. See [docs/INSTALL.md](docs/INSTALL.md).

## Status

Runewall v1.0.0 is the stable local-first foundation: CLI safety runtime, dry-run, policy checks, local logs, snapshots/rollback, community package verification, MCP status/tools, and SDK preview. It is not a hosted service and does not yet include real signature verification, community map execution, or the full approve/execute lifecycle over MCP/SDK. Future security and integration features will ship as v1.x releases.

Included in v1.0.0:

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

```powershell
pip install runewall
```

See [docs/INSTALL.md](docs/INSTALL.md) for Windows PowerShell-first setup and editable installs.

## Install status

- `pip install runewall` for normal use
- `pip install -e ".[dev]"` for local development
- see [docs/PACKAGING.md](docs/PACKAGING.md) for local packaging notes
- `runewall package pypi-check` is a local readiness check only
- `runewall package dist-check` is a local artifact presence check only

## Demo

Run the 60-second local demo with:

```powershell
.\demos\runewall_60_second_demo.ps1
```

It shows: version, safe profile, policy audit, dry-run, community package verify, MCP status, SDK status.

See [demos/README.md](demos/README.md) for details.

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
- [docs/POLICIES.md](docs/POLICIES.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [demos/README.md](demos/README.md)
- [docs/COMMUNITY_MAPS.md](docs/COMMUNITY_MAPS.md)
- [docs/PYTHON_SDK_EXAMPLES.md](docs/PYTHON_SDK_EXAMPLES.md)
