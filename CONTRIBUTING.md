# Contributing

Runewall is a local-first, open-source, CLI-first project. Please keep contributions small, focused, and easy to review.

## Local workflow

Run tests before commit:

```bash
python -m pytest tests -v
```

Run release checks:

```bash
runewall config profile safe
runewall release check
runewall release json-check
```

Maps must pass strict lint:

```bash
runewall maps lint --strict
```

## Project guardrails

- do not print, store, or log tokens
- do not add browser automation, Playwright, a dashboard, TypeScript, or a hosted backend unless that work is explicitly scheduled
- keep diffs small and directly related to the task
- add tests for CLI behavior when changing CLI behavior
- prefer local-first behavior and safe defaults
