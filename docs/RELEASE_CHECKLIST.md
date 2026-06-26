# Release Checklist

This is the recommended local release flow before tagging or publishing anything.

## Release flow

1. run tests
2. run release checks
3. run package checks
4. run community package verify
5. check MCP and SDK status
6. confirm `git status` is clean
7. bump version
8. tag
9. push
10. create GitHub release

## PowerShell checklist

```powershell
python -m pytest tests -v
runewall release check
runewall release json-check
runewall package status
runewall package build-check
runewall maps community package verify examples/community-maps --json
runewall mcp status --json
runewall sdk status --json
git status
```

## Notes

- PyPI is future work and not published yet.
- Publish only after package artifacts are verified.
- Update `CHANGELOG.md` or prepare release notes before tagging.
- See [docs/RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md) for a reusable GitHub release template.
