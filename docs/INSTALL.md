# Install

This setup uses Windows PowerShell first because current development is happening on Windows.

## Clone the repo

```powershell
git clone <your-runewall-repo-url>
cd .\runewall-starter
```

## Create a virtual environment

```powershell
python -m venv .venv
```

## Activate it in Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

## Install editable dev dependencies

```powershell
python -m pip install -e ".[dev]"
```

## Future PyPI install

```powershell
pip install runewall
```

PyPI install is future work. Runewall is not published there yet.

## Check the install

```powershell
runewall version
```

If `runewall version` prints a version string, the local install is ready.

## Run tests

```powershell
python -m pytest tests -v
```

## Package readiness checks

```powershell
runewall version
runewall release check
python -m pytest tests -v
runewall package status
runewall package status --json
```

## Safe first commands

```powershell
runewall config profile safe
runewall policy audit
runewall maps community package verify examples/community-maps --json
```

## Run the demo

```powershell
.\demos\runewall_60_second_demo.ps1
```
