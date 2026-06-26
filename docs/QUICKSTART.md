# Quickstart

This is a safe first walkthrough for trying Runewall locally in a few minutes.

## 1. Apply the safe profile

```powershell
runewall config profile safe
```

This resets local config to guarded defaults.

## 2. Audit the current policy

```powershell
runewall policy audit
```

This shows whether any local policy settings are risky.

## 3. Dry-run a GitHub issue action

```powershell
runewall act github create_issue --dry-run --json --input repo=user/repo --input title="Bug"
```

This previews a mapped action without calling GitHub and without mutating anything.

## 4. Verify a community package

```powershell
runewall maps community package verify examples/community-maps --json
```

This checks manifest validation, SHA-256 checksums, signing status, trusted key status, and execution safety posture.

## 5. Check MCP status

```powershell
runewall mcp status --json
```

This confirms the local MCP surface is available and reports its current status.

## 6. Check SDK status

```powershell
runewall sdk status --json
```

This confirms the local Python SDK preview surface is available.

## Safety notes

- dry-run does not call external APIs
- real execution is disabled by default
- community maps are non-executable
- package verify does not import or execute maps
