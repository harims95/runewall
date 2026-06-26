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

## Manifest validation

`runewall maps community manifest validate` validates a manifest file and verifies local SHA-256 checksums for each listed map file. Map paths are resolved relative to the manifest file directory.

See [docs/COMMUNITY_MAP_MANIFEST.md](COMMUNITY_MAP_MANIFEST.md) for the manifest format.

## Package inspect

`runewall maps community package inspect <directory>` inspects a local community map package directory.

- Looks for `manifest.json` first, then `manifest.example.json`.
- Validates the manifest using the same logic as `manifest validate`.
- Verifies local SHA-256 checksums.
- Shows name, version, maps count, validation result, checksum status, and safety posture.
- Does not import, install, or execute anything.

## Package verify

`runewall maps community package verify <directory>` verifies a local community map package directory.

- Looks for `manifest.json` first, then `manifest.example.json`.
- Validates the manifest using the same logic as `manifest validate`.
- Verifies local SHA-256 checksums.
- Reports signing status.
- Reports trusted key status if the manifest includes a future `signing.public_key_id`.
- Does not import or execute anything.

## Package verify JSON contract

`runewall maps community package verify <directory> --json` returns a stable machine-readable contract intended for agents and CI.

Main keys:

- `ok`
- `package`
- `validation`
- `checksums`
- `signing`
- `trusted_key`
- `safety`

## Package import

`runewall maps community package import <directory>` imports map files from a local community map package.

- Looks for `manifest.json` first, then `manifest.example.json`.
- Validates the manifest and verifies local SHA-256 checksums before copying anything.
- If validation or checksum verification fails, nothing is copied.
- On success, copies map files listed in `manifest.maps` into `.runewall/community-maps/`.
- Preserves original map filenames.
- Does not import the manifest itself as an executable map.
- Does not execute anything. Imported community maps remain non-executable.

## Signing status

`runewall maps community signing status` shows which signing features are implemented and which are future work.

See [docs/COMMUNITY_MAP_SIGNING.md](COMMUNITY_MAP_SIGNING.md) for the signing design, key policy, and planned commands.

## Future signed manifests

v0.6.1 is signing design only. Signing verification is not yet implemented.

SHA-256 checksum verification is implemented. A future signing block will allow publishers to sign manifests for provenance and tamper detection.

A future local trusted key store (design in v0.6.3) will let users explicitly trust publisher public keys. See [docs/COMMUNITY_MAP_KEYS.md](COMMUNITY_MAP_KEYS.md).

`runewall maps community keys status` shows the key store mode, storage path, and safety posture.

Key revocation (`keys revoke`) is design-only. See [docs/COMMUNITY_MAP_KEYS.md](COMMUNITY_MAP_KEYS.md) for the revoke design.

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
runewall maps community package inspect examples/community-maps
runewall maps community package inspect examples/community-maps --json
runewall maps community package verify examples/community-maps
runewall maps community package verify examples/community-maps --json
runewall maps community package import examples/community-maps
runewall maps community package import examples/community-maps --json
runewall maps community signing status
runewall maps community signing status --json
```
