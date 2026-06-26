# Community Package Verify in CI

`runewall maps community package verify <path> --json` can be used by agents, scripts, and CI jobs to check a local community map package before import or review.

## What verify checks

- manifest validation
- SHA-256 checksum verification
- signing status reporting
- trusted key status reporting if available
- execution safety posture

## What verify does not do

- does not import maps
- does not execute maps
- does not download remote files
- does not call external APIs
- does not verify cryptographic signatures yet

## Local PowerShell example

```powershell
runewall maps community package verify examples/community-maps --json
```

## PowerShell fail-fast example

```powershell
$result = runewall maps community package verify examples/community-maps --json | ConvertFrom-Json
if (-not $result.ok) {
  Write-Error "Community package verification failed"
  exit 1
}
```

## Python script example

```python
import json
import subprocess
import sys

result = subprocess.run(
    ["runewall", "maps", "community", "package", "verify", "examples/community-maps", "--json"],
    capture_output=True,
    text=True,
    check=False,
)

data = json.loads(result.stdout)
if not data.get("ok"):
    print("Community package verification failed")
    print(data.get("errors", []))
    sys.exit(1)

print("Community package verification passed")
```

## GitHub Actions example

```yaml
name: Community Map Verify

on:
  pull_request:
  push:

jobs:
  verify-community-maps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m pip install -e ".[dev]"
      - run: runewall maps community package verify examples/community-maps --json
```

## Safety note

Even if package verify passes, community map execution remains disabled.
