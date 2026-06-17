# Runewall Starter Folder

Open this folder in VS Code and ask Codex to build one slice at a time.

Start with this prompt:

```text
You are building Runewall.

Read:
- brain/runewall-brain-bundle.md
- brain/runewall-technical-spec.md

Build ONLY the initial Python package skeleton from the technical spec.

Do not build dashboard.
Do not build Playwright/browser translation.
Do not build maps yet.
Do not build TypeScript yet.
Do not add extra features.

Create:
- pyproject.toml
- LICENSE with MIT
- README.md placeholder
- runewall/__init__.py
- runewall/core/__init__.py
- runewall/core/models.py
- runewall/core/db.py
- runewall/core/log.py
- runewall/cli/__init__.py
- runewall/cli/main.py
- tests/conftest.py
- tests/core/test_log.py

Goal:
- `runewall init` creates `.runewall/runewall.db`
- SQLite schema includes actions, snapshots, rules, checkpoints
- A test can create an Action, save it, and list it back

Keep the implementation small, clean, typed, and tested.
```
