param(
  [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputPath) {
  $OutputPath = Join-Path (Split-Path -Parent $repoRoot) "vizora-submission-source.zip"
}

$excludePatterns = @(
  '^backend/models/',
  '^backend/runs/',
  '^backend/wandb/',
  '^backend/mlruns/',
  '^backend/.venv/',
  '^backend/venv/',
  '^frontend/node_modules/',
  '^frontend/.next/',
  '^node_modules/',
  '^training/',
  '^output/',
  '^outputs/',
  '^tmp/',
  '^graphify-out/',
  '^dist/',
  '^submission/',
  '\.(pt|pth|onnx|engine|bin|safetensors|ckpt|weights|tflite)$'
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git is required but was not found on PATH."
}

Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem

$trackedAndUntracked = git -C $repoRoot ls-files -co --exclude-standard
$files = $trackedAndUntracked | Where-Object {
  $rel = $_.Trim()
  if (-not $rel) { return $false }
  foreach ($pattern in $excludePatterns) {
    if ($rel -match $pattern) { return $false }
  }
  return $true
}

if (Test-Path -LiteralPath $OutputPath) {
  Remove-Item -LiteralPath $OutputPath -Force
}

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$stream = [System.IO.File]::Open($OutputPath, [System.IO.FileMode]::CreateNew)
try {
  $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
  try {
    foreach ($rel in $files) {
      $fullPath = Join-Path $repoRoot $rel
      if (-not (Test-Path -LiteralPath $fullPath)) {
        continue
      }
      [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $archive,
        $fullPath,
        $rel,
        [System.IO.Compression.CompressionLevel]::Optimal
      ) | Out-Null
    }
  }
  finally {
    $archive.Dispose()
  }
}
finally {
  $stream.Dispose()
}

Write-Host "Created submission zip: $OutputPath"
