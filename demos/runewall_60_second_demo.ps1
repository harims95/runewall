$ErrorActionPreference = "Stop"

if (-not (Get-Command runewall -ErrorAction SilentlyContinue)) {
    Write-Error "Runewall CLI is not installed or not on PATH. Activate your virtual environment and install the project first."
    exit 1
}

function Invoke-DemoStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
    Write-Host ("runewall " + ($Arguments -join " ")) -ForegroundColor DarkGray
    & runewall @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Demo stopped because the previous command failed."
        exit $LASTEXITCODE
    }
}

Invoke-DemoStep -Title "1. Version" -Arguments @("version")
Invoke-DemoStep -Title "2. Safe Profile" -Arguments @("config", "profile", "safe")
Invoke-DemoStep -Title "3. Policy Audit" -Arguments @("policy", "audit")
Invoke-DemoStep -Title "4. Dry-Run GitHub Issue" -Arguments @("act", "github", "create_issue", "--dry-run", "--json", "--input", "repo=user/repo", "--input", "title=Bug")
Invoke-DemoStep -Title "5. Community Package Verify" -Arguments @("maps", "community", "package", "verify", "examples/community-maps", "--json")
Invoke-DemoStep -Title "6. MCP Status" -Arguments @("mcp", "status", "--json")
Invoke-DemoStep -Title "7. SDK Status" -Arguments @("sdk", "status", "--json")

Write-Host ""
Write-Host "Demo complete." -ForegroundColor Green
