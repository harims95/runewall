# Runewall MCP Server Plan

## Goal

Runewall MCP server should expose Runewall as a local safety/runtime layer that agents can call before taking real-world actions.

## Why MCP matters

Agents and tools need a standard way to route actions through Runewall:

`agent -> MCP tool call -> Runewall policy/dry-run/execute/log`

## Initial MCP tools to expose

Implemented now for local stdio:

- continuous `runewall mcp serve` loop
- single-message `runewall mcp serve --once`

- `runewall.policy_test`
- `runewall.policy_audit`
- `runewall.dry_run`
- `runewall.release_check`
- `runewall.doctor`
- `runewall.maps_list`
- `runewall.maps_show`

## Later MCP tools

- `runewall.execute`
- `runewall.approve`
- `runewall.reject`
- `runewall.rollback`
- `runewall.log`

## Safety rules

- MCP server must be local-first
- no hosted backend
- no token storage
- no token printing
- dry-run must not call external APIs
- execute must respect `maps.allow_execute`
- execute must respect `rules.map_execute`
- policy block must prevent execution before external API calls
- all outputs should be JSON-compatible

## Suggested CLI command later

```bash
runewall mcp serve
```

Current local modes:

- `runewall mcp serve`
- `runewall mcp serve --once`

## Out of scope for v0.3

- dashboard
- browser automation
- Playwright
- hosted service
- TypeScript SDK
- community registry

## Acceptance criteria for v0.3

- local MCP server starts
- exposes `policy_test`
- exposes `dry_run`
- exposes `release_check`
- no external APIs called during dry-run
- tests pass
- docs updated
