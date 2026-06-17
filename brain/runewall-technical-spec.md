# Runewall — Technical Specification

## 1. Code Structure

```
runewall/
├── pyproject.toml
├── LICENSE                     # MIT
├── README.md
├── runewall/
│   ├── __init__.py             # Public API: protect(), configure()
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py           # Dataclasses: Action, Snapshot, Rule, Checkpoint
│   │   ├── interceptor.py      # Wraps agent, catches every outbound call
│   │   ├── rules.py            # Evaluates action against user-defined rules
│   │   ├── snapshot.py         # Captures state before mutation
│   │   ├── rollback.py         # Reverts state to any checkpoint
│   │   ├── log.py              # SQLite action log (read/write/query)
│   │   └── db.py               # SQLite setup, migrations, schema
│   ├── translate/
│   │   ├── __init__.py
│   │   ├── reader.py           # Universal read mode (any URL → structured content)
│   │   ├── mapper.py           # On-the-fly DOM analysis → action map
│   │   ├── executor.py         # Runs action map steps against a live site
│   │   └── browser.py          # Playwright wrapper (lazy-loaded, optional)
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── spec.py             # Agent-native endpoint spec
│   │   ├── server.py           # Reference server
│   │   └── client.py           # Reference client
│   ├── maps/
│   │   ├── __init__.py
│   │   ├── registry.py         # Load, cache, validate action maps
│   │   └── sites/              # Bundled JSON action maps (20 sites)
│   │       ├── github.json
│   │       ├── notion.json
│   │       ├── stripe.json
│   │       └── ... (20 total)
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py             # Base adapter interface
│   │   ├── langchain.py        # LangChain wrapper
│   │   ├── crewai.py           # CrewAI adapter
│   │   ├── openai_sdk.py       # OpenAI Agents SDK adapter
│   │   └── generic.py          # Wrap any callable
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py             # All CLI commands
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── store.py            # Encrypted credential storage
│   │   └── providers.py        # OAuth, API key, PAT handlers
│   └── utils/
│       ├── __init__.py
│       ├── diff.py             # Diff between snapshots
│       └── display.py          # Terminal formatting (rich)
├── tests/
│   ├── conftest.py
│   ├── core/
│   │   ├── test_interceptor.py
│   │   ├── test_rules.py
│   │   ├── test_snapshot.py
│   │   ├── test_rollback.py
│   │   └── test_log.py
│   ├── translate/
│   │   ├── test_reader.py
│   │   └── test_mapper.py
│   ├── maps/
│   │   └── test_registry.py
│   ├── cli/
│   │   └── test_cli.py
│   └── integration/
│       ├── test_file_rollback.py
│       └── test_full_workflow.py
└── docs/
    ├── quickstart.md
    ├── rules.md
    ├── maps-contributing.md
    └── protocol-spec.md
```

---

## 2. Python Package Setup (pyproject.toml)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "runewall"
version = "0.1.0"
description = "The runtime between AI agents and the real world. Every action — understood, protected, reversible."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "(fill in)" }]
keywords = ["ai", "agents", "safety", "rollback", "agentic"]

dependencies = [
    "beautifulsoup4>=4.12",
    "httpx>=0.27",
    "click>=8.1",
    "rich>=13.0",
]

[project.optional-dependencies]
browser = ["playwright>=1.40"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "pytest-cov>=4.1", "ruff>=0.3"]

[project.scripts]
runewall = "runewall.cli.main:cli"
```

Core deps: beautifulsoup4 (DOM), httpx (HTTP), click (CLI), rich (terminal UI). Playwright optional.

---

## 3. Action Map JSON Schema

```json
{
  "schema_version": "1.0.0",
  "site": {
    "name": "GitHub",
    "base_url": "https://github.com",
    "map_version": "1.0.0",
    "last_verified": "2026-06-17",
    "auth": {
      "methods": ["pat", "oauth"],
      "pat": { "header": "Authorization", "format": "Bearer {token}" },
      "oauth": { "provider": "github", "scopes": ["repo", "user"] }
    },
    "rate_limits": { "requests_per_minute": 60, "delay_ms": 500 }
  },
  "entities": {
    "repository": {
      "fields": ["owner", "name", "description", "visibility"],
      "identifier": "owner/name"
    },
    "issue": {
      "fields": ["title", "body", "labels", "assignees", "state"],
      "identifier": "owner/name#number"
    }
  },
  "flows": {
    "create_issue": {
      "description": "Create a new issue in a repository",
      "risk_level": "low",
      "reversible": true,
      "reverse_flow": "close_issue",
      "requires_auth": true,
      "inputs": {
        "repo": { "type": "string", "required": true, "format": "owner/name" },
        "title": { "type": "string", "required": true },
        "body": { "type": "string", "required": false },
        "labels": { "type": "array", "required": false }
      },
      "outputs": {
        "issue_number": { "type": "integer" },
        "issue_url": { "type": "string" }
      },
      "api_path": {
        "method": "POST",
        "url": "/repos/{repo}/issues",
        "body": { "title": "{title}", "body": "{body}", "labels": "{labels}" }
      },
      "ui_steps": [
        { "action": "navigate", "url": "https://github.com/{repo}/issues/new" },
        { "action": "fill", "selector": "#issue_title", "value": "{title}" },
        { "action": "fill", "selector": "#issue_body", "value": "{body}" },
        { "action": "click", "selector": "button[type='submit']" },
        { "action": "extract", "selector": ".gh-header-number", "output": "issue_number" }
      ]
    },
    "delete_repository": {
      "description": "Delete a repository permanently",
      "risk_level": "critical",
      "reversible": false,
      "requires_auth": true,
      "inputs": {
        "repo": { "type": "string", "required": true }
      },
      "api_path": { "method": "DELETE", "url": "/repos/{repo}" }
    }
  }
}
```

Design: each flow has both `api_path` (API-first) and `ui_steps` (browser fallback). SDK tries API first. Risk levels map to rules engine. Reversibility declared per flow.

---

## 4. Snapshot Strategy

| Action Type | What's Captured | Rollback Method | Reversible |
|---|---|---|---|
| file.write | Original file contents | Restore from snapshot | Yes |
| file.delete | Full file copy | Restore file | Yes |
| file.create | Record filepath | Delete created file | Yes |
| dir.delete | Recursive dir copy | Restore dir tree | Yes |
| db.write | Affected rows + original values | Reverse query | Yes |
| db.delete | Deleted rows stored | Re-insert | Yes |
| api.call (GET) | Nothing (read-only) | N/A | N/A |
| api.call (POST) | Request + response logged | Reverse API call if available | Maybe |
| shell.exec | Affected files snapshotted | Restore files | Partial |
| email.send | Content + recipients logged | Cannot unsend | No |

Storage layout:
```
.runewall/
├── runewall.db          # SQLite (actions, snapshots, rules, checkpoints)
├── config.toml          # User config
├── snapshots/
│   ├── {uuid}/
│   │   ├── meta.json    # What, when, why
│   │   └── files/       # Copied files (preserves relative paths)
│   └── ...
└── credentials.enc      # Encrypted credential store
```

Rules: incremental snapshots only. 500MB default cap (configurable). 30-day auto-prune (configurable). Non-reversible actions logged but marked.

---

## 5. Auth / Credential Handling

```toml
# .runewall/config.toml

[auth.github]
method = "pat"
token_env = "GITHUB_TOKEN"          # reads from env var

[auth.stripe]
method = "api_key"
key_env = "STRIPE_SECRET_KEY"

[auth.google]
method = "oauth"
client_id = "..."
client_secret_env = "GOOGLE_CLIENT_SECRET"
scopes = ["gmail.readonly"]
```

Principles:
- Env vars preferred — never hardcode secrets in config
- Never log credentials in action log
- Per-site isolation — credentials never shared across sites
- CLI prompts on first use: `runewall auth setup github`
- Encrypted local storage with Fernet (cryptography library)
- Key stored in OS keychain, fallback to `~/.runewall/key` with 600 permissions

---

## 6. CLI Commands

```
runewall init                    Initialize .runewall/ in current directory
runewall status                  Show pending actions + recent log
runewall log                     Action timeline (most recent first)
runewall log --filter file.delete Filter by action type
runewall approve ID              Approve pending action
runewall reject ID               Reject pending action
runewall rollback ID             Rollback to before action ID
runewall rollback --last         Undo most recent action
runewall maps list               List available site maps
runewall maps update             Pull latest community maps
runewall auth setup SITE         Configure credentials for a site
runewall auth list               List configured sites (no secrets)
runewall doctor                  Check health, deps, config
```

Built with click + rich.

---

## 7. SQLite Schema

```sql
CREATE TABLE actions (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    agent_id    TEXT,
    action_type TEXT NOT NULL,
    target      TEXT NOT NULL,
    params      TEXT,
    risk_level  TEXT DEFAULT 'low',
    status      TEXT DEFAULT 'pending',
    rule_applied TEXT,
    snapshot_id TEXT,
    result      TEXT,
    reversible  INTEGER DEFAULT 1,
    reasoning   TEXT
);

CREATE TABLE snapshots (
    id           TEXT PRIMARY KEY,
    action_id    TEXT NOT NULL REFERENCES actions(id),
    type         TEXT NOT NULL,
    target       TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    size_bytes   INTEGER
);

CREATE TABLE rules (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern  TEXT NOT NULL,
    policy   TEXT NOT NULL,
    priority INTEGER DEFAULT 0
);

CREATE TABLE checkpoints (
    id        TEXT PRIMARY KEY,
    name      TEXT,
    action_id TEXT NOT NULL REFERENCES actions(id)
);

CREATE INDEX idx_actions_ts ON actions(timestamp);
CREATE INDEX idx_actions_status ON actions(status);
CREATE INDEX idx_actions_type ON actions(action_type);
```

---

## 8. Public API

```python
# Two-line setup
from runewall import protect
agent = protect(your_agent)

# Custom rules
from runewall import protect, rules
agent = protect(your_agent, rules={
    "file.read": rules.AUTO,
    "file.write": rules.SNAPSHOT,
    "file.delete": rules.REVIEW,
    "shell.exec": rules.REVIEW,
})

# Rollback
from runewall import timeline
timeline.show()
timeline.rollback("id")
timeline.rollback_last()

# Universal read (any URL)
from runewall import web
content = web.read("https://any-site.com/page")

# Action mode (mapped site)
from runewall import web
result = web.act("github", "create_issue", {
    "repo": "user/repo", "title": "Bug", "body": "Details"
})

# Optional LLM enhancement
from runewall import configure
configure(llm_key="sk-...", llm_provider="openai")
```

---

## 9. Testing Strategy

- Unit tests: rules engine, models, diff generation (fast, no I/O)
- Integration tests: file snapshot + rollback, action log queries, CLI commands
- Scenario tests: full agent workflow → intercept → review → execute → rollback
- Map validation: every bundled JSON validates against schema
- Coverage target: 90%+ on core/ module
- Command: `pytest tests/ -v --cov=runewall`

---

## 10. Build Order (20 weeks)

```
Week 1-2:   Core models, SQLite schema, action log
Week 3-4:   Interceptor, rules engine, snapshot engine
Week 5-6:   Rollback engine, CLI (log, rollback, approve, status)
Week 7-8:   Universal read mode (BeautifulSoup extraction)
Week 9-10:  Action map schema, registry, first 8 site maps
Week 11-12: Adapters (LangChain, generic), auth/credential store
Week 13-14: Remaining 12 site maps, on-the-fly mapper
Week 15-16: Protocol spec, reference server/client
Week 17-18: Tests (90%+ coverage on core), docs, README
Week 19-20: Polish, dogfood with real agents, fix edge cases
```
