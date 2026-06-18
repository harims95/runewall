# Contributing action maps to Runewall

This guide explains how to add a new action map to Runewall's bundled map library.

No Python knowledge is needed. Maps are plain JSON files.

---

## What is an action map?

An action map describes the actions a Runewall agent can take on a specific website or service.

Each map defines:

- which site it covers
- which flows (actions) are available
- what inputs each flow needs
- how risky each action is
- whether a real API path exists

Maps are used for **dry-run planning** — Runewall reads a map, builds a plan, and shows it to the user without doing anything real. Real execution is a separate step that is disabled by default and must be explicitly enabled.

---

## Where bundled maps live

```
runewall/maps/sites/
```

Each map is a single JSON file named after the site key:

```
runewall/maps/sites/cloudflare.json
runewall/maps/sites/discord.json
runewall/maps/sites/github.json
runewall/maps/sites/linear.json
runewall/maps/sites/netlify.json
runewall/maps/sites/slack.json
runewall/maps/sites/supabase.json
runewall/maps/sites/vercel.json
```

Most maps are dry-run and planning only. Only `github.json` has real API execution currently. Tokens and secrets are never stored in map files.

To add a new bundled map, create a new `.json` file in this directory.

---

## Map structure

Every map file follows this structure:

```json
{
  "schema_version": "1.0.0",
  "site": {
    "name": "...",
    "base_url": "...",
    "map_version": "0.1.0",
    "category": "...",
    "tags": ["...", "..."]
  },
  "flows": {
    "flow_name": {
      ...
    }
  }
}
```

### Required site fields

| Field | Description |
|---|---|
| `name` | Human-readable site name, e.g. `"GitHub"` |
| `base_url` | The site's base URL, e.g. `"https://github.com"` |
| `map_version` | The version of this specific map, e.g. `"0.1.0"` |

`schema_version` is always `"1.0.0"` for now.

### Optional site metadata

| Field | Type | Description |
|---|---|---|
| `category` | string | Broad grouping for discovery, e.g. `"deployment"`, `"communication"`, `"development"` |
| `tags` | array of strings | Keywords that help agents find relevant maps, e.g. `["chat", "team"]` |

Maps without `category` or `tags` are still valid. Adding them helps agents and tooling discover the right map for a task.

Current categories in use: `backend`, `communication`, `deployment`, `development`, `infrastructure`, `project_management`.

### Required flow fields

Each key under `flows` is the flow name. The value is an object with these fields:

| Field | Type | Description |
|---|---|---|
| `description` | string | Short plain-English description of what this flow does |
| `risk_level` | string | `"low"`, `"medium"`, or `"high"` |
| `reversible` | boolean | Whether the action can be undone |
| `requires_auth` | boolean | Whether the action needs a credential |
| `inputs` | object | Input definitions (may be empty `{}`) |

`api_path` is optional. Include it when the flow maps to a known API endpoint.

### Input field structure

Each key under `inputs` is the input name. The value has:

```json
{
  "type": "string",
  "required": true
}
```

Set `required` to `false` for optional inputs.

---

## Risk levels

Choose the risk level honestly. When in doubt, choose higher.

| Level | When to use |
|---|---|
| `low` | Read-only, list, or easily reversible actions |
| `medium` | Creates or changes external state (e.g. creates a post, updates a setting) |
| `high` | Destructive, payment, email, irreversible deletion, or anything that cannot be undone |

Examples:
- Listing projects → `low`
- Creating an issue → `low` (GitHub issues are reversible)
- Deleting a deployment → `high`
- Sending an email → `high`

---

## Dry-run first

New maps should support dry-run planning before real execution is considered.

Dry-run is free. It reads the map, validates inputs, builds a plan, and shows it to the user. Nothing is sent to any external service.

Real execution is a much larger commitment:

- It requires writing Python execution code in `runewall/maps/executor.py`
- It requires `maps.allow_execute = true` in config
- It requires credentials in the environment
- It requires careful review for safety and reversibility

**Do not add real execution unless it has been explicitly agreed on.**

A map without execution is still useful. Users and agents can use it for planning, inspection, and dry-run previews.

---

## Validating your map

After adding a map, run the validation command:

```bash
runewall maps validate
```

This checks all bundled maps for missing required fields and reports pass or fail.

For machine-readable output:

```bash
runewall maps validate --json
```

A passing result looks like:

```json
{
  "ok": true,
  "results": [
    { "key": "myservice", "site_name": "My Service", "ok": true, "error": null }
  ]
}
```

If `ok` is `false`, the `error` field explains what is missing.

---

## Inspecting maps

List all bundled maps:

```bash
runewall maps list
runewall maps list --json
```

Show a specific map:

```bash
runewall maps show myservice
runewall maps show myservice --json
```

Show where the bundled maps directory is:

```bash
runewall maps path
```

---

## Example: a fake service map

This is a complete example map for a fictional service called "Acme".

```json
{
  "schema_version": "1.0.0",
  "site": {
    "name": "Acme",
    "base_url": "https://acme.example.com",
    "map_version": "0.1.0"
  },
  "flows": {
    "list_widgets": {
      "description": "List all widgets in the account.",
      "risk_level": "low",
      "reversible": false,
      "requires_auth": true,
      "inputs": {},
      "api_path": {
        "method": "GET",
        "url": "/api/v1/widgets"
      }
    },
    "create_widget": {
      "description": "Create a new widget with a name and color.",
      "risk_level": "medium",
      "reversible": true,
      "requires_auth": true,
      "inputs": {
        "name": {
          "type": "string",
          "required": true
        },
        "color": {
          "type": "string",
          "required": false
        }
      },
      "api_path": {
        "method": "POST",
        "url": "/api/v1/widgets"
      }
    }
  }
}
```

Save this as `runewall/maps/sites/acme.json`, then verify:

```bash
runewall maps validate
runewall maps show acme
runewall act acme list_widgets --dry-run
```

---

## Contributor checklist

Before submitting a new map, confirm all of the following:

- [ ] Map file is valid JSON
- [ ] `runewall maps validate` passes with no errors
- [ ] `runewall maps show SITE` displays the map correctly
- [ ] Dry-run works: `runewall act SITE FLOW --dry-run` runs without errors
- [ ] All required inputs are marked `"required": true`
- [ ] Risk levels are accurate and err on the side of caution
- [ ] No secrets, tokens, or credentials are in the map file
- [ ] `description` is filled in for every flow
- [ ] Real execution has **not** been added unless explicitly reviewed and agreed on
- [ ] Tests have been added if any Python code was changed
