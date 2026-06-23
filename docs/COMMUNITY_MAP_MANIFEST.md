# Community Map Manifest

Design document only. Not implemented in v0.5.

## 1. Purpose

A community map manifest describes a local/community action map package before it is trusted, installed, or executed.

The manifest is a single JSON file that travels with one or more community map files and declares their identity, permissions, safety posture, and file checksums.

## 2. Why manifests matter

Before Runewall supports remote registries or map downloads, each community map package needs metadata that can later support:

- validation
- signing
- verification
- provenance
- safety review

A manifest makes these future capabilities possible without changing the map file format itself.

## 3. Proposed manifest fields

Required fields:

| Field            | Type   | Description                                       |
|------------------|--------|---------------------------------------------------|
| manifest_version | string | Manifest schema version                           |
| name             | string | Unique package name                               |
| version          | string | Package version                                   |
| description      | string | Human-readable summary                            |
| author           | object | Author name and optional URL                      |
| maps             | array  | List of map file references with site/flow/action |
| permissions      | object | Declared API, token, and execution permissions    |
| safety           | object | Safety posture flags                              |
| checksums        | object | SHA-256 checksums keyed by filename               |

Example:

```json
{
  "manifest_version": "0.1",
  "name": "github-safe-issue-map",
  "version": "0.1.0",
  "description": "Safe GitHub issue dry-run map.",
  "author": {
    "name": "example-author",
    "url": "https://example.com"
  },
  "maps": [
    {
      "path": "github_create_issue.safe.json",
      "site": "github",
      "flow": "create_issue",
      "action_type": "map.dry_run"
    }
  ],
  "permissions": {
    "external_api_calls": false,
    "requires_tokens": false,
    "execute_enabled": false
  },
  "safety": {
    "secrets_in_files": false,
    "dry_run_first": true,
    "community_execution_allowed": false
  },
  "checksums": {
    "github_create_issue.safe.json": "sha256-placeholder"
  }
}
```

See [examples/community-maps/manifest.example.json](../examples/community-maps/manifest.example.json) for a full example.

## 4. Safety rules

- manifests must not contain secrets
- maps must not contain secrets
- tokens must come from environment variables only
- community map execution remains disabled
- `execute_enabled` and `community_execution_allowed` must both be `false`
- SHA-256 checksum verification is implemented: map files are read and hashed against `checksums` entries
- checksum mismatch, missing checksum, or missing map file fails validation
- remote downloads are future work
- signed verification is future work

## 5. Commands

`manifest validate` and `manifest inspect` are implemented in v0.5.1.

```
runewall maps community manifest validate <path>
runewall maps community manifest validate <path> --json
runewall maps community manifest inspect <path>
runewall maps community manifest inspect <path> --json
```

`manifest validate` — parse and check required fields, safety flags, and checksum field presence. Signing and checksum verification are not yet implemented.

`manifest inspect` — report manifest metadata (name, version, author, maps count, validation result) without importing or executing anything.

Future (not yet implemented):

```
runewall maps community verify <path>
```

`verify` — compare declared checksums against actual file hashes (requires checksum implementation).

## 6. Out of scope

The following are explicitly out of scope until a future release:

- real cryptographic signing
- signature verification
- remote registry
- map downloads
- automatic installation
- community map execution
