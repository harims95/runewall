# Runewall Policies

Policies are local rules Runewall uses to decide what happens before an agent action executes. They form the safety boundary between an agent and a real-world action.

## Action flow

```
Agent → Runewall → policy check → dry-run → review/execute/block → log/audit
```

Every action passes through a policy check before anything external is touched.

## Policy outcomes

| Outcome    | Decision label       | What it means                              |
|------------|----------------------|--------------------------------------------|
| `auto`     | `allow`              | Action is allowed without extra review     |
| `snapshot` | `snapshot_required`  | Action is allowed but a snapshot is taken first |
| `review`   | `review_required`    | Action requires human review before proceeding |
| `block`    | `blocked`            | Action is denied                           |

## Built-in defaults

These are the defaults when no config rule overrides them:

| Action type    | Default policy |
|----------------|----------------|
| `file.read`    | `auto`         |
| `file.create`  | `snapshot`     |
| `file.write`   | `snapshot`     |
| `file.delete`  | `review`       |
| `web.read`     | `auto`         |
| `map.dry_run`  | `auto`         |
| `map.execute`  | `review`       |
| `shell.exec`   | `review`       |
| `email.send`   | `review`       |
| unknown types  | `review`       |

## Config profiles

Apply a named policy profile with:

```powershell
runewall config profile safe
runewall config profile dev
runewall config profile agent
```

- `safe` — standard defaults, real execution disabled
- `dev` — `default_policy = "snapshot"`, execution still disabled
- `agent` — file writes and creates elevated to `review`, execution disabled

## Per-rule config

Override individual action type policies in `.runewall/config.toml` under `[rules]`:

```toml
[rules]
file_write = "snapshot"
file_create = "snapshot"
file_delete = "review"
web_read = "auto"
map_dry_run = "auto"
map_execute = "review"
unknown = "review"
```

Valid values for each rule: `auto`, `snapshot`, `review`, `block`.

Set a rule from the CLI:

```powershell
runewall config set rules.map_execute review
runewall config set rules.file_delete block
```

## Policy commands

### Audit current settings

```powershell
runewall policy audit
runewall policy audit --json
```

Flags any rules that allow risky actions without review (for example, `map_execute = "auto"` or `maps.allow_execute = true`).

### Test a specific action type

```powershell
runewall policy test file.delete
runewall policy test map.execute --json
```

Shows the effective decision for an action type under the current config.

### Explain a policy

```powershell
runewall policy explain file.write
runewall policy explain map.execute --json
```

Shows which policy applies, where it comes from (default rule, config rule, or fallback), and why.

### List all effective policies

```powershell
runewall policy list
runewall policy list --json
```

Shows the effective policy for every standard action type.

## Dry-run and policy together

A dry-run previews an action and reports the policy decision without calling any external API:

```powershell
runewall act github create_issue --dry-run --json --input repo=user/repo --input title="Bug"
```

The JSON output includes `policy`, `decision`, `policy_source`, and `policy_reason` fields so you can see exactly what Runewall would do before any execution happens.

## Safe-by-default behavior

- Real execution is disabled by default (`maps.allow_execute = false`)
- `dry-run` never calls external APIs
- Tokens are read from environment variables only
- Tokens are never printed, stored, or logged
- Community maps are not executable by default
- Unknown action types default to `review`, not `auto`

## Current limitations

The policy surface in v1.0.x is intentionally small:

- Policies are configured via TOML rules in `.runewall/config.toml`, not a full policy language
- No conditional logic or dynamic rule evaluation yet
- No user-authored policy files beyond the `[rules]` section
- Policy checks are local only — no remote policy server

## Future direction

- Clearer examples and policy cookbooks
- More named profiles
- Stronger safe-by-default tests in CI
- MCP/SDK approve-execute lifecycle integration
- Custom policy file support (if demand warrants it)
