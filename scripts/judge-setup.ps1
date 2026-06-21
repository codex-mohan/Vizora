param(
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Ensure-File {
  param(
    [string]$Source,
    [string]$Destination
  )

  if (-not (Test-Path -LiteralPath $Destination)) {
    Copy-Item -LiteralPath $Source -Destination $Destination
    Write-Host "Created $Destination from $Source"
  }
}

Ensure-File -Source (Join-Path $repoRoot "backend\.env.example") -Destination (Join-Path $repoRoot "backend\.env")
Ensure-File -Source (Join-Path $repoRoot "frontend\.env.example") -Destination (Join-Path $repoRoot "frontend\.env.local")

if ($SkipInstall) {
  Write-Host "Skipping dependency install."
  exit 0
}

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
  throw "pnpm is required but was not found on PATH."
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv is required but was not found on PATH."
}

Write-Host "Installing root Node dependencies..."
Push-Location $repoRoot
try {
  pnpm install
}
finally {
  Pop-Location
}

Write-Host "Installing frontend Node dependencies..."
Push-Location (Join-Path $repoRoot "frontend")
try {
  pnpm install
}
finally {
  Pop-Location
}

Write-Host "Syncing backend Python dependencies..."
Push-Location (Join-Path $repoRoot "backend")
try {
  uv sync
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next: run `pnpm dev` from the repo root."
Write-Host "Optional: `pwsh .\scripts\start-demo-rtsp.ps1` to feed the live camera demo."
