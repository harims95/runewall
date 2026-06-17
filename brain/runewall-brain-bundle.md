# Runewall — Project Brain

This is the canonical context for the project "Runewall". It is a small set of source-of-truth files. Use it to ground your responses; don't restate it back to me unless asked.

---

# [OV] Overview

**What this project is:** Runewall is an open-source runtime that sits between AI agents and the real world — intercepting, protecting, translating, and standardizing every agent action so agents don't break and humans stay safe.

**Why it exists:** The entire internet (websites, forms, dashboards, APIs) was built for humans, not agents. Agents break constantly because of this mismatch — they can't navigate human interfaces reliably, they forget everything between sessions, and when they mess up there's no undo. Every major infra company (Visa, GoDaddy, Coinbase, Vercel) is building for agents, but nobody is building the runtime layer between agents and the world.

**Who it's for:** Solo developers and small companies (2-20 people) building with AI agents. NOT enterprises. The open-source community contributes and validates web maps.

**Current status:** Idea — architecture defined, competitive research done, name chosen. Pre-code.


---

# [GO] Goals & Non-Goals

## Goals

- Ship a fully working open-source product (not an MVP) that solo devs install and trust with real agent workflows
- Zero external dependencies — no API keys, no accounts, no internet required (except for websites agents visit)
- No vendor lock-in, no hidden API requirement, no "free but actually you need our paid tier"
- `pip install runewall` gives you the FULL product — safety, rollback, translation, maps, dashboard, everything
- Framework-agnostic — works with LangChain, CrewAI, OpenAI Agents SDK, Claude Code, AutoGen, or any custom agent
- Build all three layers (safety + translation + protocol) in a single product
- Community-driven web maps via GitHub — every developer using the SDK makes it smarter for everyone
- Support both Python and TypeScript (the two languages every agent framework uses)

## Non-Goals

- NOT building for enterprises or big companies with dedicated DevOps teams
- NOT building a browser automation tool (Browserbase does that)
- NOT building an agent framework (LangChain, CrewAI do that)
- NOT building a payment layer (x402, Visa VIC do that)
- NOT building an identity system (GoDaddy ANS does that)
- NOT requiring a hosted backend or API to function
- NOT charging for core features — ever
- NOT building a universal web crawler that handles every site on day one — starting with 20 priority sites for action maps, universal read mode for everything else


---

# [AR] Architecture

**Stack:** Python + TypeScript (dual SDK). SQLite for local action log. Playwright for headless browser. React for local dashboard.

**Key components:**

- **Action Interceptor** — middleware that wraps any agent framework, catches every outbound action (file ops, API calls, DB writes, shell commands, emails)
- **Rules Engine** — developer defines per-action-type rules: auto-approve, snapshot-and-execute, or pause-for-human-review
- **Snapshot Engine** — captures full state before every mutating action (file contents, DB rows, API state)
- **Action Log** — git-like timeline of every agent action with diffs, timestamps, and agent reasoning. Stored in local SQLite
- **Rollback Engine** — revert to any checkpoint in the timeline, not just the last action
- **Action Router** — determines the best path for each agent action: universal read, pre-mapped action, or on-the-fly mapping
- **Universal Read Mode** — extracts structured content from any URL using DOM analysis libraries (Readability, BeautifulSoup, Cheerio). No LLM needed. Works on every website
- **Action Mode (mapped sites)** — 20 pre-mapped high-priority websites with deep, reliable, community-validated JSON action maps bundled in the package
- **Action Mode (on-the-fly)** — heuristic DOM analysis to detect forms, buttons, inputs and generate basic action maps for unmapped sites. Optional LLM enhancement with developer's own key
- **Agent-Native Protocol** — open spec (MCP-compatible) for services to publish structured agent endpoints. Reference server and client included
- **Local Dashboard** — React web UI on localhost for reviewing action timeline, approving pending actions, inspecting diffs, triggering rollbacks
- **CLI** — `runewall log`, `runewall rollback`, `runewall approve`, `runewall maps update`

**How things connect:**

```
Agent → Runewall SDK (intercept) → Rules Engine → Snapshot
                                        |
                                   Action Router
                                   /          \
                          Translation      Agent-native
                          (read/act)        protocol
                               |               |
                          Real world        Services
                               \               /
                            Action Log (SQLite)
                                    |
                            Dashboard / CLI
                            (human review)
```

**Data model / important entities:**

- **Action** — one agent operation (type, target, params, timestamp, status, snapshot_id, result)
- **Snapshot** — pre-action state capture (files, DB rows, etc.)
- **Rule** — per-action-type policy (auto/snapshot/review)
- **SiteMap** — JSON action map for a website (URL, flows, steps, fields, outputs)
- **Checkpoint** — rollback target (action_id, snapshot references)

**External dependencies:**

- Playwright (headless browser for web translation)
- BeautifulSoup / Readability (DOM content extraction)
- SQLite (action log storage, bundled with Python)
- No external APIs required. Optional: developer's own LLM key for enhanced on-the-fly mapping

**Distribution:**

- PyPI: `pip install runewall`
- npm: `npm install runewall`
- GitHub: community maps repo (JSON files, updated via PRs, pulled via `runewall maps update`)


---

# [DC] Decisions

A log of choices made and why. Newest at the top. Never edit old entries.

## 2026-06-17 — MIT License
**Context:** Needed to choose open-source license
**Choice:** MIT
**Why:** Maximum adoption — what React, Next.js, and most developer tools use. No restrictions, no friction. Enterprise can come later.
**Alternatives considered:** AGPL (protects against cloud freeloaders but slows adoption), Apache 2.0 (patent protection but more complex)

## 2026-06-17 — CLI first, dashboard second
**Context:** Need to decide build order for user interfaces
**Choice:** CLI first, dashboard follows
**Why:** Faster to build, solo devs prefer terminal, can ship sooner. Dashboard adds visual layer later for teams.
**Alternatives considered:** Dashboard first (slower), both together (too much work upfront)

## 2026-06-17 — Python first, TypeScript follows
**Context:** SDK needs to support both Python and TypeScript
**Choice:** Build Python SDK first
**Why:** Most agent frameworks (LangChain, CrewAI, AutoGen) are Python. Larger initial user base. TypeScript follows once Python is solid.
**Alternatives considered:** TypeScript first, both simultaneously

## 2026-06-17 — Name: Runewall
**Context:** Needed a unique, brandable name for the project
**Choice:** Runewall
**Why:** "Rune" = ancient symbols of protection, "Wall" = barrier between two worlds. Metaphor fits perfectly — a magical protective barrier between agents and the human web. Clean on PyPI, GitHub, and domains.
**Alternatives considered:** Mantle (taken on PyPI), Ozone (taken on PyPI), Kova, Conduit (taken), Canopy (taken), Membrane, Airlock, Kavach

## 2026-06-17 — No API dependency, fully local
**Context:** Debated whether the SDK should call a hosted API for shared maps and LLM-powered site understanding
**Choice:** Fully local — no API, no accounts, no keys required
**Why:** Strongest open-source positioning. Developers trust tools that genuinely work offline. Community maps via GitHub repo (git pull, not API call). Optional LLM enhancement uses developer's own key. No vendor lock-in.
**Alternatives considered:** Hosted API for shared map registry (rejected — creates dependency), proxy LLM calls through our API (rejected — costs money and creates lock-in)

## 2026-06-17 — Universal read + mapped action (two-mode translation)
**Context:** Research agents visit hundreds of random websites. Can't pre-map the entire internet.
**Choice:** Two modes — universal read mode (any URL, content extraction via DOM analysis) and action mode (20 pre-mapped sites + on-the-fly heuristic mapping for new sites)
**Why:** Reading is simpler than acting — DOM extraction handles it without LLM. Action mapping needs deeper understanding, so start with 20 reliable maps and expand via community. Read mode also feeds action mode — frequently visited sites get gradually promoted.
**Alternatives considered:** LLM-powered universal mapping for everything (rejected — requires API key, costs money, breaks zero-dependency goal), only pre-mapped sites (rejected — too limiting)

## 2026-06-17 — Build all three layers simultaneously
**Context:** Considered building safety layer first, then translation, then protocol in separate phases
**Choice:** Build all three at once, but with different depth — safety at full depth, translation with 20 mapped sites + universal read, protocol as spec + reference implementation
**Why:** The three layers are deeply connected. Safety without translation just logs raw function calls without semantic meaning. Translation without safety lets agents break things. All three together = the complete product.
**Alternatives considered:** Sequential phases (rejected — shipping just safety feels incomplete, developers will ask "cool but my agent still breaks on websites")

## 2026-06-17 — Target solo devs and small companies, not enterprises
**Context:** Rubrik Agent Cloud targets enterprises with expensive pricing. Nobody serves the small developer.
**Choice:** Open-source, free, developer-first. Target solo devs and teams of 2-20.
**Why:** Developers are the hardest audience to market to — they ignore ads and hate sales pitches. Only thing that works is genuine trust from other developers. Free + good = organic growth. Enterprise can come later.
**Alternatives considered:** Enterprise-first (rejected — requires sales team, long cycles, not our strength), freemium (rejected — "free but actually paid" breaks trust)

## 2026-06-17 — Ship full product, not MVP
**Context:** Standard startup advice is "ship MVP fast"
**Choice:** Ship a full working product that solo devs trust with real agent workflows
**Why:** Developers have zero tolerance for half-working tools. If rollback doesn't work, they'll never come back. The safety layer especially must be bulletproof from day one.
**Alternatives considered:** MVP with just action logging (rejected — logging without rollback is useless, developers won't adopt)

## 2026-06-17 — 20 priority website maps, community-driven expansion
**Context:** Needed to decide scope for pre-mapped website action maps
**Choice:** 20 sites across 4 tiers — 8 easy (GitHub, Notion, Stripe, Vercel, Cloudflare, Shopify, Trello, Slack), 6 medium (Gmail/GWorkspace, HubSpot, Razorpay, Google Analytics, Search Console, Zoho), 4 hard (AWS, Jira, Amazon Seller Central, Netlify), 2 dropped (LinkedIn, Twitter/X — anti-bot/legal risk)
**Why:** These 20 cover the full workflow of a solo dev or small company: deploy code, manage business, handle money, track data, manage infra. Easy tier ships first to prove the product. Medium tier shows translation layer's real power (filling API gaps). Community adds more via GitHub PRs.
**Alternatives considered:** Universal LLM-powered crawler for all sites (rejected — breaks zero-dependency goal), only 5 sites (rejected — too limited to be useful)


---

# [ST] Current State

Snapshot of right now. Rewrite freely as things change.

**What works:**
- Product vision fully defined
- Competitive landscape researched
- Three-layer architecture designed
- 20 priority websites selected and ranked
- Name chosen: Runewall
- Project brain initialized
- Technical spec complete: code structure, package setup, JSON schema, snapshot strategy, auth handling, CLI design, SQLite schema, public API, testing strategy, 20-week build order
- All major decisions made: MIT license, Python first, CLI first

**In progress:**
- Nothing yet — ready to start writing code

**Broken / known issues:**
- No code written yet
- No GitHub repo created
- No PyPI name reserved
- runewall.dev domain not registered
- Developer's background not confirmed

**Next 3 things to do:**
1. Set up GitHub repo, reserve PyPI name
2. Build Week 1-2: core models, SQLite schema, action log
3. Build Week 3-4: interceptor, rules engine, snapshot engine


---

# [GL] Glossary

Project-specific terms an AI won't know from general knowledge. One sentence per term.

- **Runewall** — the product name; an open-source runtime between AI agents and the real world
- **Action Interceptor** — middleware that catches every outbound agent action before it reaches the real world
- **Action Map / SiteMap** — a JSON file describing a website's structure, flows, forms, and actions in a format agents can consume
- **Universal Read Mode** — content extraction from any URL using DOM analysis, no LLM needed, works on every website
- **Action Mode** — deep interaction with websites using pre-mapped action maps or on-the-fly heuristic mapping
- **On-the-fly mapping** — heuristic DOM analysis that generates a basic action map for unmapped sites in real time
- **Checkpoint** — a point in the action timeline that can be rolled back to, consisting of snapshots taken before each mutating action
- **Community Maps** — website action maps contributed by developers via GitHub PRs, bundled into the SDK on updates
- **Agent-Native Protocol** — Runewall's open spec for services to publish structured endpoints agents can interact with directly, no translation needed
- **x402** — HTTP-native payment protocol by Coinbase using HTTP 402 status code for agent-to-service stablecoin payments
- **KYA (Know Your Agent)** — term coined by Ribbit Capital for agent identity verification, predicted to be bigger than KYC
- **ANS (Agent Name Service)** — GoDaddy's trust layer for AI agents, connecting agent identity to domain names with cryptographic verification
- **VIC (Visa Intelligent Commerce)** — Visa's framework for agent-initiated secure payments across their network
- **MCP (Model Context Protocol)** — Anthropic's protocol for connecting AI models to external tools and data sources
- **A2A (Agent-to-Agent)** — Google's protocol for standardized agent-to-agent communication


---

# [OQ] Open Questions

Things I'm unsure about. When a question is resolved, move it to DC as a decision.

- What is the developer's technical background and what languages are they comfortable with?
- Solo founder or is there a team? This affects build order and code structure.
- Should the CLI be the primary interface or the dashboard? Solo devs might prefer CLI, small teams might prefer dashboard.
- How should credential/auth handling work for the translation layer? Agents need to log into sites — where do credentials live securely?
- What's the JSON schema for action maps? Need to design this before building the 20 site maps.
- Should the agent-native protocol be a superset of MCP or a separate spec that's MCP-compatible?
- How do we handle sites that change their UI frequently? Auto-staleness detection? Community flagging?
- What's the right granularity for snapshots? File-level? Line-level? How do we snapshot API state or database state?
- Should on-the-fly mapping cache its results locally only, or also offer to contribute back to community maps?
- What license? MIT (maximum adoption) or AGPL (prevents cloud providers from hosting without contributing back)?
- Replace LinkedIn/Twitter with Supabase/Firebase in the 20-site list, or find better alternatives?
- How do we handle rate limiting when translation layer interacts with websites? Per-site configurable delays?


---

