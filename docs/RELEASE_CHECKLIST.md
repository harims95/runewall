# Release Checklist

This is the recommended local release flow before tagging or publishing anything.

## Before bump

1. run tests
2. run release checklist
3. run release check
4. run release json-check
5. run package status
6. run package build-check
7. run package pypi-check
8. run local artifact build
9. run local artifact verification
10. run community package verify
11. run MCP status
12. run SDK status
13. confirm `git status`

## PowerShell

```powershell
python -m pytest tests -v
runewall release checklist
runewall release check
runewall release json-check
runewall package status
runewall package build-check
runewall package pypi-check
python -m build
python -m twine check dist/*
runewall package dist-check --json
runewall maps community package verify examples/community-maps --json
runewall mcp status --json
runewall sdk status --json
git status
```

## Version bump

1. update version
2. run `runewall version`
3. confirm MCP initialize version

## After bump

1. commit
2. push
3. tag
4. push tag
5. create GitHub release
6. update `CHANGELOG.md` if needed

## Notes

- PyPI is future work and not published yet.
- Publish only after package artifacts are verified.
- `runewall package pypi-check` is local-only and does not upload anything.
- `runewall package dist-check` only checks local artifact presence.
- See [docs/RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md) for a reusable GitHub release template.
