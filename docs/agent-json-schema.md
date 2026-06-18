# Runewall agent JSON schema

This document describes the stable JSON shapes produced by `runewall act` when `--json` is used.

All other commands that support `--json` are documented in the main README.

---

## General rules

- `--json` prints valid JSON only. Nothing else is written to stdout.
- Token values are never printed, stored, or logged in any mode.
- Dry-run never calls external APIs. It only reads the map and builds a plan.
- Real execution is disabled by default by `maps.allow_execute`.
- Dry-run and execute JSON include policy fields so agents can explain the effective decision.
- A `block` policy prevents execute before any external API call is made.

Enable real execution:

```bash
runewall config set maps.allow_execute true
```

Disable again:

```bash
runewall config set maps.allow_execute false
```

---

## Policy fields

These fields are included in dry-run JSON success responses, execute JSON success responses, and execute JSON error responses when the policy can be resolved:

- `policy`: the effective policy for the action type
- `decision`: the effective decision label derived from the policy
- `policy_source`: where the policy came from
- `policy_reason`: a short explanation of the match

### Policy values

| Value | Meaning |
|---|---|
| `auto` | Runewall would allow the action automatically |
| `snapshot` | Runewall would require a snapshot before action |
| `review` | Runewall would require human review |
| `block` | Runewall would block the action |

### Decision values

| Value | Meaning |
|---|---|
| `allow` | Action is allowed |
| `snapshot_required` | Snapshot is required before action |
| `review_required` | Human review is required |
| `blocked` | Action is blocked |

---

## Dry-run JSON

```bash
runewall act SITE FLOW --dry-run --json --input key=value
```

### Success

```json
{
  "ok": true,
  "executed": false,
  "site": "github",
  "flow": "create_issue",
  "description": "Create a GitHub issue",
  "risk_level": "low",
  "reversible": true,
  "requires_auth": true,
  "provided_inputs": {
    "repo": "user/repo",
    "title": "Test issue"
  },
  "missing_inputs": [],
  "api_path": {
    "method": "POST",
    "url": "/repos/{repo}/issues"
  },
  "ui_steps_count": 0,
  "policy": "auto",
  "decision": "allow",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_dry_run = \"auto\""
}
```

`executed` is always `false` for dry-run. No external API is called.

### Error - missing required input

```json
{
  "ok": false,
  "executed": false,
  "site": "github",
  "flow": "create_issue",
  "error": "Missing required inputs: title",
  "error_code": "INVALID_INPUT"
}
```

### Error - unknown site

```json
{
  "ok": false,
  "executed": false,
  "site": "unknown",
  "flow": "create_issue",
  "error": "Unknown site: unknown",
  "error_code": "UNKNOWN_SITE"
}
```

### Error - unknown flow

```json
{
  "ok": false,
  "executed": false,
  "site": "github",
  "flow": "unknown_flow",
  "error": "Unknown flow: unknown_flow",
  "error_code": "UNKNOWN_FLOW"
}
```

---

## Execute JSON

```bash
runewall act SITE FLOW --execute --json
```

### Success

```json
{
  "ok": true,
  "executed": true,
  "site": "github",
  "flow": "create_issue",
  "result": {
    "issue_url": "https://github.com/user/repo/issues/1",
    "issue_number": 1
  },
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

### Error - execution blocked by config

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
  "error_code": "EXECUTION_DISABLED",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

### Error - missing token

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "VERCEL_TOKEN is required to execute vercel:list_projects.",
  "error_code": "MISSING_TOKEN",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

### Error - unsupported execution

```json
{
  "ok": false,
  "executed": false,
  "site": "slack",
  "flow": "send_message",
  "error": "Execution is not supported for slack:send_message.",
  "error_code": "UNSUPPORTED_EXECUTION",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

### Error - API failure

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Vercel list_projects failed: 401 Unauthorized",
  "error_code": "API_ERROR",
  "policy": "review",
  "decision": "review_required",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"review\""
}
```

### Error - blocked by policy before external execution

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Execution blocked by policy for map.execute.",
  "error_code": "POLICY_BLOCKED",
  "policy": "block",
  "decision": "blocked",
  "policy_source": "config_rule",
  "policy_reason": "rules.map_execute = \"block\""
}
```

---

## Error codes

| Code | When it appears |
|---|---|
| `EXECUTION_DISABLED` | `maps.allow_execute` is `false` or config is missing |
| `MISSING_TOKEN` | Required environment variable is not set |
| `UNSUPPORTED_EXECUTION` | Real execution is not implemented for this site/flow |
| `API_ERROR` | The external API returned a non-2xx response |
| `POLICY_BLOCKED` | The effective `map.execute` policy is `block` |
| `UNKNOWN_SITE` | The site key does not match any bundled map |
| `UNKNOWN_FLOW` | The flow name does not exist in the site map |
| `INVALID_INPUT` | One or more required inputs are missing |

Error codes are stable. They will not change without a version bump.

---

## Required tokens

Each real-execution map requires its own environment variable.

| Site | Token variable |
|---|---|
| Cloudflare | `CLOUDFLARE_API_TOKEN` |
| GitHub | `GITHUB_TOKEN` |
| Netlify | `NETLIFY_TOKEN` |
| Supabase | `SUPABASE_ACCESS_TOKEN` |
| Vercel | `VERCEL_TOKEN` |

Tokens are read only from environment variables. They are never echoed, stored in config, or written to the action log.
