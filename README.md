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

## Manual Demo

```bash
python examples/file_rollback_demo.py
type demo.txt
runewall rollback --last
type demo.txt
```

## Current working demo

1. Initialize Runewall:

```bash
runewall init
```

2. Create `demo.txt`:

```bash
echo "original content" > demo.txt
```

3. Use `protect_file_write`:

```python
from pathlib import Path
from runewall import protect_file_write

with protect_file_write("demo.txt"):
    Path("demo.txt").write_text("changed by interceptor")
```

4. View log:

```bash
runewall log
```

5. Rollback:

```bash
runewall rollback --last
```

6. Confirm file restored:

```bash
type demo.txt
```

In simple terms, Runewall snapshots the file before mutation, logs the action, marks it as `success` if the write completes, and `rollback` restores the original content.
