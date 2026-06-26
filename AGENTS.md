# AGENTS.md

> **Note:** This file is for repository contributors and AI coding assistants working on this codebase. It is not Runewall's runtime agent model, product spec, or MCP protocol spec.

Behavioral guidelines for Codex while building Runewall.

These instructions reduce common LLM coding mistakes. Follow them together with the project brain and technical spec.

Before coding, always read:

* `brain/runewall-brain-bundle.md`
* `brain/runewall-technical-spec.md`

Runewall is local-first, open-source, Python-first, CLI-first, and safety-first.

Do not build everything at once.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

* State your assumptions explicitly.
* If uncertain, ask or explain the uncertainty.
* If multiple interpretations exist, present them instead of silently choosing.
* If a simpler approach exists, say so.
* Push back when the request would make the system overcomplicated.
* If something is unclear, stop and name what is confusing.

---

## 2. Simplicity First

**Minimum code that solves the current task. Nothing speculative.**

* No features beyond what was asked.
* No abstractions for single-use code.
* No dashboard unless explicitly requested.
* No TypeScript SDK unless explicitly requested.
* No Playwright/browser translation unless explicitly requested.
* No website maps unless explicitly requested.
* No auth/credential layer unless explicitly requested.
* No agent-native protocol unless explicitly requested.
* No "future flexibility" unless the current task needs it.
* If you write 200 lines and it could be 50, rewrite it.

Ask yourself:

> Would a senior engineer say this is overcomplicated?

If yes, simplify.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

* Do not improve adjacent code, comments, or formatting unless needed.
* Do not refactor things that are not broken.
* Match the existing style.
* If you notice unrelated dead code, mention it but do not delete it.
* Remove imports, variables, or functions only if your changes made them unused.

Every changed line should directly trace to the current request.

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals.

Examples:

* "Add validation" means: write tests for invalid inputs, then make them pass.
* "Fix the bug" means: write a test that reproduces it, then make it pass.
* "Refactor X" means: ensure tests pass before and after.

For multi-step tasks, state a brief plan:

```txt
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Do not stop after writing code. Run or explain the verification.

---

## 5. Runewall Build Order

Build Runewall in this order:

```txt
1. Python package skeleton
2. Core models
3. SQLite schema
4. Action log
5. CLI init/log
6. Rules engine
7. File snapshot engine
8. File rollback engine
9. Interceptor
10. Universal read mode
11. Maps
12. Auth
13. Protocol
14. Dashboard
15. TypeScript SDK
```

Do not skip ahead.

Current priority:

```txt
Core models → SQLite schema → Action log → CLI init/log
```

---

## 6. Runewall Non-Negotiables

Runewall must remain:

* Local-first
* Open-source
* No required hosted backend
* No required API key
* No vendor lock-in
* Python-first
* CLI-first
* Framework-agnostic
* Safety-first
* Rollback-focused

Do not add external services.

Do not require internet except for websites agents intentionally visit.

Do not log secrets.

Do not hardcode credentials.

---

## 7. Testing Rules

For every feature:

* Add tests.
* Keep tests small and focused.
* Prefer temp directories for file-system tests.
* Do not depend on real websites in core tests.
* Do not require external API keys.
* Do not require network access for core tests.

Before finishing, run:

```bash
pytest tests/ -v
```

If tests fail, fix only the failing area.

---

## 8. Git / Diff Discipline

Before final response:

* Summarize changed files.
* Summarize tests run.
* Mention any tests not run.
* Mention any known limitations.
* Do not claim something works unless it was tested.

---

## 9. These Guidelines Are Working If

* Diffs are small.
* No unnecessary files are touched.
* No speculative systems are added.
* Tests exist for new behavior.
* Clarifying questions happen before wrong implementation.
* Runewall grows one safe layer at a time.
