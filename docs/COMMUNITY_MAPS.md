# Community Maps

Community maps are local files only for now.

## Current scope

- local community map files only
- remote registry and downloads are future work
- community maps must pass validation before use
- community maps are dry-run first
- execute is not enabled for community maps yet
- tokens must use environment variables only
- maps must never include secrets

## Safety notes

- validation does not install a map
- validation does not execute a map
- validation does not call external APIs
- bundled maps continue to work as before
- see [examples/community-maps](../examples/community-maps) for safe local examples

## Commands

```bash
runewall maps community status
runewall maps community status --json
runewall maps community validate path/to/map.json
runewall maps community validate path/to/map.json --json
runewall maps community validate examples/community-maps/github_create_issue.safe.json
runewall maps community validate examples/community-maps/github_create_issue.safe.json --json
```
