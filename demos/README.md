# Demos

## What the demo shows

The 60-second demo walks through safe local Runewall commands only.

It shows:

- version output
- guarded local config via the safe profile
- policy audit output
- a dry-run action preview
- community package verification
- local MCP status
- local SDK status

The demo is local-only, token-free, and does not call external APIs.

This is the fastest way to explain what Runewall does to a new developer.

## Run it in Windows PowerShell

```powershell
cd C:\Users\Asus\Desktop\runewall\runewall-starter
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
runewall version
.\demos\runewall_60_second_demo.ps1
```

## What each step means

- `version` confirms the CLI install
- `safe profile` resets guarded config
- `policy audit` checks safety posture
- `dry-run` previews an action without external API calls
- `package verify` checks community map package safety
- `MCP status` shows the agent-facing local MCP surface
- `SDK status` shows the Python SDK preview
