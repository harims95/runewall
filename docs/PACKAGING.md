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
runewall package pypi-check
runewall package dist-check
python -m pytest tests -v
```

## Build artifacts locally

Use these local-only commands:

```powershell
python -m pip install build twine
python -m build
python -m twine check dist/*
```

- `python -m build` creates a wheel and sdist in `dist/`
- `python -m twine check dist/*` validates package metadata and README rendering
- this does not publish anything
- do not run `twine upload` yet

This creates:

- `dist/*.whl`
- `dist/*.tar.gz`

## Dist verification checklist

- `dist/` folder exists
- wheel exists
- sdist exists
- `python -m twine check dist/*` passes
- version matches `runewall version`
- tests pass before build
- GitHub release should exist before publishing

## Install local wheel example

```powershell
python -m pip install dist/<wheel-file>.whl
```

## Safety note

Building artifacts does not call external APIs and does not require tokens.

See [docs/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the local release flow before tagging or any future publish step.

## PyPI readiness

- run local tests
- run `runewall release checklist`
- run `runewall package status`
- run `runewall package build-check`
- run `runewall package pypi-check`
- build local artifacts
- inspect the `dist/` folder
- confirm the version is correct
- confirm the README renders cleanly
- confirm a GitHub release exists before publishing
- PyPI publishing is still future and manual

Future publish commands only:

```powershell
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

Do not run upload until the release is ready.

## Future PyPI checklist

- confirm version
- tests pass
- release check passes
- build-check passes
- pypi-check passes
- inspect wheel and sdist
- create GitHub release
- publish only when ready
