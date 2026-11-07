param([switch]$NoBrowser,[switch]$Restart)
$ErrorActionPreference = 'Stop'
if ($env:ODD_EPISODE_WORKER -eq '1') { throw 'Station startup/restart is a development-only operation.' }
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
  if ($Restart) {
    $activeJobs = @(Invoke-RestMethod -Uri "http://127.0.0.1:$stationPort/api/activity" -TimeoutSec 5) | Where-Object { $_.status -in @('QUEUED','RUNNING') }
    if ($activeJobs) { throw 'Wait for active production jobs to finish before restarting the station.' }
    $listeners = @(Get-NetTCPConnection -LocalPort $stationPort -State Listen)
    if ($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1') { throw 'Cannot identify the loopback station process safely.' }
    $stationProcessId = $listeners[0].OwningProcess
    $stationProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$stationProcessId"
    if ($stationProcess.Name -notmatch '^python(w)?\.exe$' -or $stationProcess.CommandLine -notmatch 'uvicorn\s+services\.api\.main:app') { throw 'The listener is not the expected station backend.' }
    Stop-Process -Id $stationProcessId
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
      if (-not (Get-NetTCPConnection -LocalPort $stationPort -State Listen -ErrorAction SilentlyContinue)) { break }
      Start-Sleep -Milliseconds 100
    }
    if (Get-NetTCPConnection -LocalPort $stationPort -State Listen -ErrorAction SilentlyContinue) { throw 'The old station process did not release its port.' }
    Write-Host 'Restarting the station to load current backend source.'
  } else {
    if (-not $NoBrowser) {
      $capability = (Get-Content -Raw -LiteralPath $tokenFile | ConvertFrom-Json).token
      Start-Process "http://127.0.0.1:$stationPort/#controller=$capability"
    }
    Write-Host "Station already running at http://127.0.0.1:$stationPort"
    Write-Host 'After source upgrades, use scripts/start.ps1 -Restart to load the updated backend.'
    exit 0
  }
}
if (-not $NoBrowser) {
  $openScript = Join-Path $PSScriptRoot 'open-browser.ps1'
  Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-File',"`"$openScript`"",'-Port',"$stationPort",'-TokenFile',"`"$tokenFile`"")
}
Write-Host "ODD FRAME station: http://127.0.0.1:$stationPort - Ctrl+C to stop."
& ./.venv/Scripts/python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port $stationPort --workers 1
exit $LASTEXITCODE
