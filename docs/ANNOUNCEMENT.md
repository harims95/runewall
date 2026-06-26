# Runewall v0.9.0

I've been building Runewall - a local-first safety/runtime layer for AI agents before they take real-world actions.

Agents are moving from answering to acting.

Before an agent touches files, APIs, tools, or external systems, I think we need a local boundary layer that can:

- preview the action
- explain the policy decision
- block risky behavior
- log what happened
- rollback where possible

Runewall currently includes:

- CLI-first safety runtime
- dry-run before mutation
- local SQLite action log
- policy explain/test/audit
- snapshots and rollback
- local MCP stdio surface
- Python SDK preview
- community package verification
- trusted key lifecycle
- package readiness checks
- 60-second local demo

It is safe by default:

- real execution disabled by default
- dry-run does not call external APIs
- tokens only from env vars
- tokens are never printed, stored, or logged
- community map execution remains disabled
- no hosted backend required

GitHub:
https://github.com/harims95/runewall
