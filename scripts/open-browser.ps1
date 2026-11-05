param([int]$Port = 8123, [string]$TokenFile)
for ($attempt = 0; $attempt -lt 60; $attempt++) {
  try {
    $status = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 2
    if ($status.brand -eq 'ODD FRAME' -and (Test-Path -LiteralPath $TokenFile)) {
      $capability = (Get-Content -Raw -LiteralPath $TokenFile | ConvertFrom-Json).token
      Start-Process "http://127.0.0.1:$Port/#controller=$capability"
      exit 0
    }
  } catch { }
  Start-Sleep -Milliseconds 1000
}
