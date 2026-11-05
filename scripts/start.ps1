param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path '.venv/Scripts/python.exe') -or -not (Test-Path 'apps/dashboard/dist/index.html')) { throw 'Run .\scripts\setup.ps1 first.' }
if (-not $env:ODD_PORT) { $env:ODD_PORT = '8123' }
$stationPort = [int]$env:ODD_PORT
$stateRoot = if ($env:ODD_DATA_ROOT) { $env:ODD_DATA_ROOT } else { (Get-Location).Path }
$tokenFile = Join-Path $stateRoot 'data/controller-access.json'
$existing = $null
try { $existing = Invoke-RestMethod -Uri "http://127.0.0.1:$stationPort/api/status" -TimeoutSec 2 } catch { }
if ($existing) {
  if ($existing.brand -ne 'ODD FRAME') { throw 'Port is occupied by a different application.' }
  if (-not $NoBrowser) {
    $capability = (Get-Content -Raw -LiteralPath $tokenFile | ConvertFrom-Json).token
    Start-Process "http://127.0.0.1:$stationPort/#controller=$capability"
  }
  Write-Host "Station already running at http://127.0.0.1:$stationPort"
  exit 0
}
if (-not $NoBrowser) {
  $openScript = Join-Path $PSScriptRoot 'open-browser.ps1'
  Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-File',"`"$openScript`"",'-Port',"$stationPort",'-TokenFile',"`"$tokenFile`"")
}
Write-Host "ODD FRAME station: http://127.0.0.1:$stationPort - Ctrl+C to stop."
& ./.venv/Scripts/python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port $stationPort --workers 1
exit $LASTEXITCODE
