# Community Map Signing

Design document only. Not implemented in v0.6.

SHA-256 checksum verification is implemented. Signature verification is future work.

## 1. Purpose

Community map signing is intended to help users verify that a map package came from a known publisher and was not modified after publishing.

## 2. Current status

- Signing is design-only. Runewall does not yet verify signatures.
- Runewall does verify local SHA-256 checksums for manifest-listed map files.
- See [docs/COMMUNITY_MAP_MANIFEST.md](COMMUNITY_MAP_MANIFEST.md) for the implemented checksum verification.

## 3. Signing goals

- verify package provenance
- detect tampering
- support trusted publishers later
- keep local-first workflow
- avoid storing secrets in map files
- keep community maps non-executable by default

## 4. Proposed signing model

A future manifest may include a `signing` block:

```json
{
  "signing": {
    "algorithm": "ed25519",
    "public_key_id": "example-author-key",
    "signature": "base64-signature-placeholder",
    "signed_fields": [
      "manifest_version",
      "name",
      "version",
      "maps",
      "permissions",
      "safety",
      "checksums"
    ]
  }
}
```

The `signed_fields` list defines which manifest fields are covered by the signature. `checksums` is always included, so a valid signature also transitively covers the map file contents.

## 5. Key policy

- private keys must never be stored in map packages
- public keys may be distributed separately or referenced by key id
- Runewall should not auto-trust remote keys
- trust should be explicit and local
- key rotation should be supported later
- revoked keys should fail verification later

## 6. Commands

`signing status` is implemented. All other signing commands are future work.

```
runewall maps community signing status
runewall maps community signing status --json
```

`signing status` — shows which signing features are implemented and which are future work. Checksum verification is implemented; signature generation and verification are not yet implemented.

Future (not yet implemented):

```
runewall maps community verify <path>
runewall maps community keys list
runewall maps community keys trust <key-file>
runewall maps community keys revoke <key-id>
```

`verify` — validate a package manifest and verify its signature against a locally trusted key.

`keys list` — list locally trusted public keys.

`keys trust <key-file>` — add a public key to the local trust store.

`keys revoke <key-id>` — remove a key from the local trust store.

## 7. Out of scope

- real cryptographic signing
- signature verification
- remote key discovery
- hosted registry
- automatic trust
- community map execution

## 8. Safety stance

Even signed maps should remain dry-run first. A valid signature should not automatically mean execution is allowed. Execution policy must remain separate from package trust.
