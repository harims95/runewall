# Runewall agent JSON schema

This document describes the stable JSON shapes produced by `runewall act` when `--json` is used.

All other commands that support `--json` are documented in the main README.

---

## General rules

- `--json` prints valid JSON only. Nothing else is written to stdout.
- Token values are never printed, stored, or logged in any mode.
- Dry-run never calls external APIs. It only reads the map and builds a plan.
- Real execution is disabled by default.

Enable real execution:

```bash
runewall config set maps.allow_execute true
```

Disable again:

```bash
runewall config set maps.allow_execute false
```

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
    "title": "Bug report",
    "body": "Details"
  },
  "missing_inputs": [],
  "api_path": {
    "method": "POST",
    "url": "/repos/{repo}/issues"
  },
  "ui_steps_count": 0
}
```

`executed` is always `false` for dry-run. No external API is called.

### Error — missing required input

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

### Error — unknown site

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

### Error — unknown flow

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

### Success — GitHub create_issue

```json
{
  "ok": true,
  "executed": true,
  "site": "github",
  "flow": "create_issue",
  "result": {
    "issue_url": "https://github.com/user/repo/issues/1",
    "issue_number": 1
  }
}
```

### Success — Vercel list_projects

```json
{
  "ok": true,
  "executed": true,
  "site": "vercel",
  "flow": "list_projects",
  "result": {
    "project_count": 2,
    "projects": [
      { "id": "proj_1", "name": "my-app", "framework": "nextjs" }
    ]
  }
}
```

### Success — Netlify list_sites

```json
{
  "ok": true,
  "executed": true,
  "site": "netlify",
  "flow": "list_sites",
  "result": {
    "site_count": 1,
    "sites": [
      { "id": "site_1", "name": "my-site", "url": "https://my-site.netlify.app" }
    ]
  }
}
```

### Success — Supabase list_projects

```json
{
  "ok": true,
  "executed": true,
  "site": "supabase",
  "flow": "list_projects",
  "result": {
    "project_count": 1,
    "projects": [
      { "id": "proj_1", "name": "my-db", "region": "us-east-1", "status": "ACTIVE_HEALTHY" }
    ]
  }
}
```

### Error — execution blocked by config

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
  "error_code": "EXECUTION_DISABLED"
}
```

### Error — missing token

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "VERCEL_TOKEN is required to execute vercel:list_projects.",
  "error_code": "MISSING_TOKEN"
}
```

### Error — unsupported execution

```json
{
  "ok": false,
  "executed": false,
  "site": "slack",
  "flow": "send_message",
  "error": "Execution is not supported for slack:send_message.",
  "error_code": "UNSUPPORTED_EXECUTION"
}
```

### Error — API failure

```json
{
  "ok": false,
  "executed": false,
  "site": "vercel",
  "flow": "list_projects",
  "error": "Vercel list_projects failed: 401 Unauthorized",
  "error_code": "API_ERROR"
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
| `UNKNOWN_SITE` | The site key does not match any bundled map |
| `UNKNOWN_FLOW` | The flow name does not exist in the site map |
| `INVALID_INPUT` | One or more required inputs are missing |

Error codes are stable. They will not change without a version bump.

---

## Required tokens

Each real-execution map requires its own environment variable.

| Site | Token variable |
|---|---|
| GitHub | `GITHUB_TOKEN` |
| Vercel | `VERCEL_TOKEN` |
| Netlify | `NETLIFY_TOKEN` |
| Supabase | `SUPABASE_ACCESS_TOKEN` |

Tokens are read only from environment variables. They are never echoed, stored in config, or written to the action log.
