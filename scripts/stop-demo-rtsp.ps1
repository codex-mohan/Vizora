$ErrorActionPreference = "Stop"

$running = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq "vizora-mediamtx" }
if ($running) {
  docker rm -f vizora-mediamtx | Out-Null
  Write-Host "Stopped vizora-mediamtx."
} else {
  Write-Host "vizora-mediamtx is not running."
}
