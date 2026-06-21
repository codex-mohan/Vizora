param(
  [string]$VideoPath = "data\samples\live-demo\traffic-demo-h264.mp4",
  [string]$StreamName = "traffic-demo",
  [int]$RtspPort = 8554,
  [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$resolvedVideo = Resolve-Path -LiteralPath $VideoPath
$rtspUrl = "rtsp://127.0.0.1:$RtspPort/$StreamName"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker is required for the RTSP server but was not found on PATH."
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  throw "FFmpeg is required for video looping but was not found on PATH."
}

Write-Host "Demo video: $($resolvedVideo.Path)"
Write-Host "RTSP URL:   $rtspUrl"

if ($PrintOnly) {
  Write-Host ""
  Write-Host "Commands that will run:"
  Write-Host "docker run -d --name vizora-mediamtx -p ${RtspPort}:8554 bluenviron/mediamtx:latest"
  Write-Host "ffmpeg -re -stream_loop -1 -i `"$($resolvedVideo.Path)`" -an -c:v copy -bsf:v h264_mp4toannexb -f rtsp -rtsp_transport tcp `"$rtspUrl`""
  exit 0
}

$running = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "vizora-mediamtx" }
if (-not $running) {
  $existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq "vizora-mediamtx" }
  if ($existing) {
    docker rm -f vizora-mediamtx | Out-Null
  }

  Write-Host "Starting MediaMTX RTSP server on port $RtspPort..."
  docker run -d --name vizora-mediamtx -p "${RtspPort}:8554" bluenviron/mediamtx:latest | Out-Null
  Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "Publishing looped demo stream. Press Ctrl+C to stop FFmpeg."
Write-Host "Use this camera source URL in Vizora settings: $rtspUrl"
Write-Host ""

ffmpeg -re -stream_loop -1 -i "$($resolvedVideo.Path)" -an -c:v copy -bsf:v h264_mp4toannexb -f rtsp -rtsp_transport tcp "$rtspUrl"
