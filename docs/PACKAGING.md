# Runewall Packaging Notes

## Current status

- local editable install is supported
- `package status` command exists
- `package build-check` command exists
- PyPI publishing is future work
- do not publish yet unless the release process is ready

## Local readiness commands

```powershell
runewall package status
runewall package build-check
python -m pytest tests -v
```

## Local artifact build

Optional local build commands:

```powershell
python -m pip install build
python -m build
```

This creates:

- `dist/*.whl`
- `dist/*.tar.gz`

## Install local wheel example

```powershell
python -m pip install dist/<wheel-file>.whl
```

## Safety note

Building artifacts does not call external APIs and does not require tokens.

## Future PyPI checklist

- confirm version
- tests pass
- release check passes
- build-check passes
- inspect wheel and sdist
- create GitHub release
- publish only when ready
