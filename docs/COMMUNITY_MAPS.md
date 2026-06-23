# Community Maps

Community maps are local files only for now.

v0.5 community maps are local-only and non-executable.

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

## Local import preview

- `runewall maps community import PATH` validates a local file before copying it
- imported files are copied into `.runewall/community-maps/`
- imported community maps are not executable yet
- remote registry and downloads are still future work

## Inspect

- `runewall maps community inspect PATH` validates a local file and reports its safety posture
- inspect shows local metadata such as `site`, `flow`, and `action_type`
- inspect does not import a map
- inspect does not execute a map

## Quickstart

1. Validate the bundled example:
   `runewall maps community validate examples/community-maps/github_create_issue.safe.json`
2. Inspect the bundled example:
   `runewall maps community inspect examples/community-maps/github_create_issue.safe.json`
3. Import the validated example locally:
   `runewall maps community import examples/community-maps/github_create_issue.safe.json`
4. List imported maps:
   `runewall maps community list`

## Future signed manifests

Design-only in v0.5.1. Not implemented yet.

A future manifest format will let community map packages declare their identity, permissions, safety posture, and file checksums — enabling signing and verification without changing the map file format.

See [docs/COMMUNITY_MAP_MANIFEST.md](COMMUNITY_MAP_MANIFEST.md) for the proposed design.

## Commands

```bash
runewall maps community status
runewall maps community status --json
runewall maps community list
runewall maps community list --json
runewall maps community inspect path/to/map.json
runewall maps community inspect path/to/map.json --json
runewall maps community import path/to/map.json
runewall maps community import path/to/map.json --json
runewall maps community validate path/to/map.json
runewall maps community validate path/to/map.json --json
runewall maps community validate examples/community-maps/github_create_issue.safe.json
runewall maps community validate examples/community-maps/github_create_issue.safe.json --json
runewall maps community manifest validate examples/community-maps/manifest.example.json
runewall maps community manifest validate examples/community-maps/manifest.example.json --json
runewall maps community manifest inspect examples/community-maps/manifest.example.json
runewall maps community manifest inspect examples/community-maps/manifest.example.json --json
```
