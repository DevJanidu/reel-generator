$ErrorActionPreference = 'Stop'
if ($env:ODD_EPISODE_WORKER -eq '1') { throw 'Development setup is forbidden inside episode production.' }
Set-Location (Split-Path -Parent $PSScriptRoot)
function Run-Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw 'Setup command failed.' } }
foreach ($tool in @('python','node','npm.cmd','ffmpeg','ffprobe')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Required tool missing from PATH: $tool" }
}
if (-not (Test-Path '.venv/Scripts/python.exe')) { Run-Checked { python -m venv .venv } }
Run-Checked { ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt }
Run-Checked { npm.cmd ci }
Run-Checked { npm.cmd run build }
Run-Checked { npm.cmd run typecheck }
Run-Checked { node scripts/check-browser.mjs }
Run-Checked { ./.venv/Scripts/python.exe scripts/setup_media_runtime.py }
Run-Checked { ./.venv/Scripts/python.exe -c "from services.api.core import init_db; from services.api.skills import load_skills; init_db(); load_skills(); print('All four full skills validated')" }
if (-not (Test-Path '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Write-Host 'Setup complete. Run .\scripts\start.ps1' -ForegroundColor Green
