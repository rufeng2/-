param(
  [Parameter(Mandatory=$true)][string]$Version,
  [switch]$Canary
)
$ErrorActionPreference = "Stop"
$state = Join-Path $PSScriptRoot "..\.deploy"
New-Item -ItemType Directory -Force $state | Out-Null
$current = Join-Path $state "current-version"
if (Test-Path $current) { Copy-Item $current (Join-Path $state "previous-version") -Force }
Set-Content -Path $current -Value $Version -NoNewline
docker compose -p rag build backend celery_worker celery_beat
if ($Canary) {
  docker compose -p rag up -d --no-deps backend
  Start-Sleep -Seconds 10
  Invoke-RestMethod http://127.0.0.1:8000/api/health -TimeoutSec 15 | Out-Null
}
docker compose -p rag up -d
Invoke-RestMethod http://127.0.0.1:8080/api/health -TimeoutSec 20 | Out-Null
Write-Host "Deployment $Version is healthy"