# Run VectorTrack from source for day-to-day development.
# No PyInstaller rebuild or installer reinstall needed — quit and re-run after code changes.
#
# Usage:
#   .\dev.ps1
#   .\dev.ps1 --portable

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $here ".venv\Scripts\python.exe"
$requirements = Join-Path $here "requirements.txt"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv (Join-Path $here ".venv")
}

& $venvPython -m pip install -r $requirements -q
& $venvPython -m pip install -e (Join-Path (Split-Path -Parent $here) "packages\vectortrack-core") -q

$running = Get-Process -Name "VectorTrack" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host ""
    Write-Host "VectorTrack is already running (installed build or another dev session)." -ForegroundColor Yellow
    Write-Host "Close it first — only one instance can run at a time." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Starting VectorTrack from source..." -ForegroundColor Green
Write-Host "Data folder: $env:LOCALAPPDATA\Paragon\VectorTrack (same as installed app)" -ForegroundColor Gray
Write-Host ""

Push-Location $here
try {
    if ($AppArgs) {
        & $venvPython -m vectortrack @AppArgs
    } else {
        & $venvPython -m vectortrack
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
