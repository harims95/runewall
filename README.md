# Runewall

Runewall is a local-first runtime for recording agent actions safely.

This starter implements only the initial Python package skeleton and Week 1 core:

- package metadata via `pyproject.toml`
- SQLite bootstrap for `.runewall/runewall.db`
- core dataclasses for actions, snapshots, rules, and checkpoints
- a minimal `runewall init` CLI
- tests for storing and listing actions

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
runewall init
pytest tests -v
```
