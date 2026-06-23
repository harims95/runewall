# Changelog

## v0.2.0 - Release candidate

Runewall v0.2.0 is a CLI-first, local-first release candidate focused on safe agent action planning, logging, policy control, and guarded execution.

Completed features:

- local-first CLI runtime
- SQLite action log
- `config validate`, `config reset`, and `config profile`
- custom auth token environment variable names
- custom safety rules
- `policy explain`, `policy list`, `policy test`, and `policy audit`
- policy decisions included in dry-run and execute JSON output
- `doctor` with policy audit
- `release check`, `release json-check`, `release examples`, and `release status`
- action maps registry
- `maps lint`, `maps search`, `maps stats`, and `maps export`
- universal read
- snapshots and rollback
- approval flow
- guarded real execution for:
  - Cloudflare `list_zones`
  - GitHub `create_issue`
  - Vercel `list_projects`
  - Netlify `list_sites`
  - Supabase `list_projects`
- dry-run-only maps:
  - Discord `send_message`
  - Linear `create_issue`
  - Slack `send_message`

Safety notes:

- real execution is disabled by default
- tokens are read only from environment variables
- dry-run does not call external APIs
- policy block prevents execution before any external API call
