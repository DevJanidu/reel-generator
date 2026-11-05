param([switch]$Render,[switch]$Security,[switch]$CLI,[switch]$UI)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& $PSScriptRoot/build.ps1
& ./.venv/Scripts/python.exe -m pytest -q tests
if ($LASTEXITCODE -ne 0) { throw 'Backend verification failed' }
if ($Render) {
  & ./.venv/Scripts/python.exe scripts/render_smoke.py
  if ($LASTEXITCODE -ne 0) { throw 'Actual render verification failed' }
}
if ($Security) {
  & ./.venv/Scripts/python.exe scripts/isolation_smoke.py
  if ($LASTEXITCODE -ne 0) { throw 'Native isolation verification failed' }
}
if ($CLI) {
  & ./.venv/Scripts/python.exe scripts/cli_workflow_smoke.py
  if ($LASTEXITCODE -ne 0) { throw 'Real Codex creative workflow verification failed' }
}
if ($UI) {
  node scripts/ui-smoke.mjs
  if ($LASTEXITCODE -ne 0) { throw 'Browser verification failed' }
}
