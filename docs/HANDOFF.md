# Runewall Handoff

## What Runewall is

Runewall is a local-first safety/runtime layer between AI agents and real-world actions.

It sits between an agent and the outside world so actions can be planned, audited, reviewed, logged, and rolled back safely.

## Core principles

- local-first
- CLI-first
- no hosted backend required
- dry-run before mutation
- execution disabled by default
- tokens only from environment variables
- never print, store, or log tokens
- tests before commit
- keep diffs small

## Current major features

- `init`, `status`, `log`, `version`, `doctor`
- local SQLite DB and local config
- snapshots and rollback
- review / pending / approve / reject / execute flow
- universal read
- action maps
- map search / filter / stats / export / lint / strict lint
- JSON output for agent-readable commands
- real guarded execution for:
  - Cloudflare `list_zones`
  - GitHub `create_issue`
  - Vercel `list_projects`
  - Netlify `list_sites`
  - Supabase `list_projects`
- dry-run-only maps:
  - Discord `send_message`
  - Linear `create_issue`
  - Slack `send_message`
- `config validate`, `config reset`, `config profile`
- custom auth token env names
- custom safety rules
- `policy explain`, `policy list`, `policy test`, `policy audit`
- policy fields in dry-run and execute JSON
- `release check`

## Current tags

- `v0.1.0-local-safety-and-maps`
- `v0.1.0-agent-readable-cli`
- `v0.1.1-map-registry-quality`
- `v0.1.2-safe-readonly-execution`
- `v0.1.3-agent-execution-json`
- `v0.1.4-readonly-execution-expanded`
- `v0.1.5-config-validation-and-auth-env`
- `v0.1.6-config-policy-profiles`
- `v0.1.7-config-safety-rules`
- `v0.1.8-policy-tooling`
- `v0.1.9-execution-policy-decisions`
- `v0.1.10-policy-audit`
- `v0.1.11-doctor-policy-audit`
- `v0.1.12-release-check`

There may also be an older `v0.1.8-policy-explain-and-list` tag, but `v0.1.8-policy-tooling` is the better checkpoint name.

## Standard Windows dev commands

```powershell
cd C:\Users\Asus\Desktop\runewall\runewall-starter
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
git status
```

## Safe release checklist

```powershell
runewall config profile safe
runewall config validate
runewall policy audit
runewall maps lint --strict
runewall doctor
runewall release check
python -m pytest tests -v
```

## Recommended next roadmap

- package polish / PyPI readiness
- CLI help polish
- JSON schema consistency audit
- docs examples
- GitHub Actions CI
- then Linear real execution only with review
- avoid Slack / Discord real execution until stronger review UX exists
- later MCP server
- later SDK
- later browser automation
- later local dashboard

## Important guardrails

Do not add browser automation, Playwright, dashboard, TypeScript, or hosted backend unless specifically scheduled.
