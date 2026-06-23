# Runewall MCP Client Examples

Runewall exposes a local stdio MCP-compatible surface so agents can call safety tools before taking real-world actions.

## Supported modes

- `runewall mcp serve --once`
- `runewall mcp serve`

## Supported JSON-RPC methods

- `initialize`
- `tools/list`
- `tools/call`

## Supported tools

- `runewall.policy_test`
- `runewall.policy_audit`
- `runewall.dry_run`
- `runewall.release_check`
- `runewall.doctor`
- `runewall.maps_list`
- `runewall.maps_show`

## PowerShell smoke examples

Initialize:

```powershell
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | runewall mcp serve --once
```

Tools list:

```powershell
'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | runewall mcp serve --once
```

Policy test:

```powershell
'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"runewall.policy_test","arguments":{"action_type":"map.execute"}}}' | runewall mcp serve --once
```

Dry-run preview:

```powershell
'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"runewall.dry_run","arguments":{"site":"github","flow":"create_issue","inputs":{"repo":"user/repo","title":"Bug"}}}}' | runewall mcp serve --once
```

Continuous loop:

```powershell
@'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
'@ | runewall mcp serve
```

## Safety notes

- local stdio only
- no HTTP server
- no hosted backend
- no token storage
- no token printing
- dry-run does not call external APIs
- execute is not exposed through MCP

## Agent integration idea

Agents should call `runewall.dry_run` before any real tool action, inspect the policy decision and preview, then only proceed through future guarded execution flows when explicitly allowed.
