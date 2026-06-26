# Community Map Keys

Runewall has a local trusted key store for explicit trust decisions. Runewall does not yet verify signatures.

## 1. Purpose

The local trusted key store lets users explicitly trust publisher public keys for future community map signature verification.

## 2. Current status

- local trusted key store is implemented for `keys status`, `keys list`, `keys inspect`, `keys trust`, and `keys revoke`
- Runewall does not yet verify signatures
- Runewall does verify local SHA-256 checksums for manifest-listed map files
- see [docs/COMMUNITY_MAP_SIGNING.md](COMMUNITY_MAP_SIGNING.md) for the signing design
- see [docs/COMMUNITY_MAP_MANIFEST.md](COMMUNITY_MAP_MANIFEST.md) for the implemented checksum verification

## 3. Safety principles

- trust must be explicit
- trust must be local
- no automatic remote key trust
- no private keys in packages
- no private keys in the Runewall key store
- trusted keys do not enable execution
- signing must not imply execution
- community map execution remains disabled

## 4. Local storage path

Trusted keys are stored at:

```text
.runewall/trusted-keys/
```

One JSON file per trusted key, keyed by `key_id`.

## 5. Trusted key record

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

`status` may be `"trusted"` or `"revoked"`. A revoked key should fail future signature verification.

## 6. Commands

All trusted key commands are local-only.

```bash
runewall maps community keys status
runewall maps community keys status --json
runewall maps community keys list
runewall maps community keys list --json
runewall maps community keys inspect <key-id>
runewall maps community keys inspect <key-id> --json
runewall maps community keys trust <key-file>
runewall maps community keys trust <key-file> --json
runewall maps community keys trust <key-file> --force
runewall maps community keys revoke <key-id>
runewall maps community keys revoke <key-id> --json
runewall maps community keys revoke <key-id> --reason "reason"
runewall maps community keys revoke <key-id> --json --reason "reason"
```

`keys status` shows the key store mode, storage path, implemented features, and safety posture.

`keys list` reads local key records from `.runewall/trusted-keys/` and lists key ids, algorithms, and status.

`keys inspect <key-id>` shows details for a single local key record without printing the public key.

`keys trust <key-file>` validates a local JSON key file and stores it under `.runewall/trusted-keys/<key_id>.json`. Trust is local-only and does not enable signature verification or community map execution.

`keys revoke <key-id>` is local-only revoke. It does not delete the key record. Instead, it updates the stored record with `status: revoked`, adds `revoked_at`, and stores `revocation_reason`. Revoke does not enable or disable community map execution.

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

## 9. Trusted key revoke behavior

### Purpose

Revoking a trusted key lets a user locally mark a publisher key as no longer trusted, so future signature verification against that key fails.

### Safety rule

Revocation is local-only. Runewall must not depend on remote revocation lists yet.

### Revoked key record behavior

A revoked key record sets `"status": "revoked"` and may include optional fields:

```json
{
  "key_id": "example-author-key",
  "algorithm": "ed25519",
  "public_key": "base64-public-key-placeholder",
  "trusted_at": "2026-01-01T00:00:00Z",
  "revoked_at": "2026-06-01T00:00:00Z",
  "revocation_reason": "user_requested",
  "source": "local-file",
  "status": "revoked"
}
```

### Implemented behavior

- revoked keys still appear in `keys list` with `status: revoked`
- `keys inspect` shows `status: revoked`
- future signature verification should fail for revoked keys
- revocation does not delete the key record
- private keys must never be stored
- trusted keys do not enable community map execution
- revocation does not enable or disable community map execution
