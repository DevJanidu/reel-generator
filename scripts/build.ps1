$ErrorActionPreference = 'Stop'
if ($env:ODD_EPISODE_WORKER -eq '1') { throw 'Application builds are forbidden inside episode production.' }
Set-Location (Split-Path -Parent $PSScriptRoot)
npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed' }
npm.cmd run typecheck
if ($LASTEXITCODE -ne 0) { throw 'Renderer typecheck failed' }
