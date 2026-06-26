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

## Run tests

```powershell
python -m pytest tests -v
```

## Check the install

```powershell
runewall version
```

If `runewall version` prints a version string, the local install is ready.
