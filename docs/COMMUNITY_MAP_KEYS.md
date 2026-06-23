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

## 6. Commands

`keys status`, `keys list`, and `keys inspect` are implemented. All three are read-only — they do not trust new keys, verify signatures, or call external APIs. Trust and revoke are future work.

```
runewall maps community keys status
runewall maps community keys status --json
runewall maps community keys list
runewall maps community keys list --json
runewall maps community keys inspect <key-id>
runewall maps community keys inspect <key-id> --json
```

`keys status` — shows the key store mode, storage path, implemented features, and safety posture.

`keys list` — reads local key records from `.runewall/trusted-keys/` and lists key ids, algorithms, and status. Returns an empty list if the folder does not exist. Invalid key records produce a warning and are skipped.

`keys inspect <key-id>` — finds and shows details for a single key record by key id. Does not include the public key in output. Returns `key_not_found` if the key id is not in the local store.

Future (not yet implemented):

```
runewall maps community keys trust <key-file>
runewall maps community keys revoke <key-id>
```

`keys trust <key-file>` — add a public key file to the local trust store.

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
