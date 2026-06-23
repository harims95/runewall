# Runewall Python SDK Examples

The Python SDK is a local-only preview wrapper for calling Runewall safety checks from agent scripts.

## Available functions

- `policy_test`
- `policy_audit`
- `release_check`
- `mcp_status`
- `dry_run`

## Not exposed yet

- `execute`
- `approve`
- `reject`
- `rollback`
- `log`

## Safety

- local-only
- `dry_run` does not call external APIs
- no token storage
- no token printing
- `execute` not exposed

## Result shape

Success:

```python
{"ok": True, "...": "..."}
```

Normal validation error:

```python
{"ok": False, "error": "site is required", "error_code": "missing_site"}
```

## Dry-run parity

- SDK `dry_run` is intended to match CLI dry-run semantics.
- Both are local preview paths.
- Neither should call external APIs.
- SDK is easier for agent scripts, and the CLI is easier for terminal workflows.

## Example: policy test

```python
from runewall.sdk import policy_test

result = policy_test("map.execute")
print(result)
```

## Example: dry-run GitHub issue

```python
from runewall.sdk import dry_run

result = dry_run(
    "github",
    "create_issue",
    {
        "repo": "user/repo",
        "title": "Bug",
    },
)

print(result)
```

## Example: release check

```python
from runewall.sdk import release_check

print(release_check())
```

## Example: MCP status

```python
from runewall.sdk import mcp_status

print(mcp_status())
```

## Agent usage pattern

Agents should call `dry_run` before any real-world action, inspect the returned policy and preview data, and only proceed through future guarded execution flows when explicitly allowed.
