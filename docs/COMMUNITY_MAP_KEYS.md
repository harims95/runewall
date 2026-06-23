# Community Map Keys

Design document only. Not implemented.

No key store exists yet. Runewall does not yet verify signatures.

## 1. Purpose

The local trusted key store will let users explicitly trust publisher public keys for future community map signature verification.

## 2. Current status

- Design-only. No key store exists yet.
- Runewall does not yet verify signatures.
- Runewall does verify local SHA-256 checksums for manifest-listed map files.
- See [docs/COMMUNITY_MAP_SIGNING.md](COMMUNITY_MAP_SIGNING.md) for the signing design.
- See [docs/COMMUNITY_MAP_MANIFEST.md](COMMUNITY_MAP_MANIFEST.md) for the implemented checksum verification.

## 3. Safety principles

- trust must be explicit
- trust must be local
- no automatic remote key trust
- no private keys in packages
- no private keys in Runewall key store
- signing must not imply execution
- community map execution remains disabled

## 4. Proposed local storage path

Trusted keys would be stored at:

```
.runewall/trusted-keys/
```

One JSON file per trusted key, keyed by `key_id`.

## 5. Proposed trusted key record

```json
{
  "key_id": "example-author-key",
  "algorithm": "ed25519",
  "public_key": "base64-public-key-placeholder",
  "trusted_at": "ISO-8601 timestamp",
  "source": "local-file",
  "status": "trusted"
}
```

`status` may be `"trusted"` or `"revoked"`. A revoked key should fail signature verification.

## 6. Future commands

Not implemented. Planned for a future release:

```
runewall maps community keys status
runewall maps community keys list
runewall maps community keys trust <key-file>
runewall maps community keys inspect <key-id>
runewall maps community keys revoke <key-id>
```

`keys status` — show whether a local key store exists and how many keys are trusted.

`keys list` — list all locally trusted public keys with their ids and status.

`keys trust <key-file>` — add a public key file to the local trust store.

`keys inspect <key-id>` — show details for a single trusted key.

`keys revoke <key-id>` — mark a trusted key as revoked so it fails future verification.

## 7. Key rotation policy

- publishers may rotate keys by publishing a new key with a new `key_id`
- old keys can be revoked locally via `keys revoke`
- revoked keys should fail verification in a future release
- package verification should show which key signed the package

## 8. Out of scope

- private key generation
- signing
- signature verification
- remote key discovery
- hosted registry
- automatic trust
- community map execution
