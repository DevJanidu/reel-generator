param([ValidateRange(1024,65535)][int]$Port = 5173)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$stateRoot = if ($env:ODD_DATA_ROOT) { $env:ODD_DATA_ROOT } else { $projectRoot }
$tokenFile = Join-Path $stateRoot 'data/controller-access.json'
if (-not (Test-Path -LiteralPath $tokenFile)) { throw 'Start the FastAPI station using scripts/start.ps1 first.' }
# Session storage is origin-scoped: the Vite browser needs its own authorized launch.
# Do not print the capability or send it to a provider.
$launchCapability = (Get-Content -Raw -LiteralPath $tokenFile | ConvertFrom-Json).token
Start-Process "http://127.0.0.1:$Port/#controller=$launchCapability"
