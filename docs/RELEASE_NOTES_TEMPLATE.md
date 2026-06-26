# Runewall vX.Y.Z - short title

## Current status

- local-first CLI and devtool
- MCP stdio surface
- Python SDK preview
- community package verification

## What changed

- ...

## Safety

- local-first
- no hosted backend
- no token storage
- no token printing
- dry-run and package verify do not call external APIs unless explicitly stated

## Commands to try

```powershell
runewall version
runewall release checklist
runewall package build-check
runewall maps community package verify examples/community-maps --json
```

## Not included yet

- hosted backend
- dashboard
- remote registry
- real signature verification
- community map execution
