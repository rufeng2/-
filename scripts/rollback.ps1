$ErrorActionPreference = "Stop"
$state = Join-Path $PSScriptRoot "..\.deploy"
$previous = Join-Path $state "previous-version"
if (-not (Test-Path $previous)) { throw "No previous version recorded" }
$version = (Get-Content $previous -Raw).Trim()
$env:IMAGE_TAG = $version
docker compose -p rag up -d --force-recreate
Invoke-RestMethod http://127.0.0.1:8080/api/health -TimeoutSec 20 | Out-Null
Copy-Item $previous (Join-Path $state "current-version") -Force
Write-Host "Rolled back to $version"