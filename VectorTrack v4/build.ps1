# Build chain for VectorTrack v4 standalone.
# Usage:
#   .\build.ps1                  # build executable only
#   .\build.ps1 -WithInstaller   # build executable + Inno Setup installer

param(
    [switch]$WithInstaller
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $here ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    $fallback = Join-Path (Split-Path $here -Parent) "VectorTrack v0 PY\.venv\Scripts\python.exe"
    if (Test-Path $fallback) {
        $venvPython = $fallback
        Write-Host "Using v0 venv: $venvPython" -ForegroundColor Yellow
    } else {
        Write-Host "Create a venv first: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt pyinstaller" -ForegroundColor Red
        exit 1
    }
}

# 1) Ensure PyInstaller is available.
& $venvPython -m pip install pyinstaller -q

# 2) Build VectorTrack.exe from build.spec (use temp dist to avoid Google Drive locks).
$distPath = "C:\Temp\VectorTrackBuild"
$workPath = "C:\Temp\VectorTrackWork"
New-Item -ItemType Directory -Force -Path $distPath, $workPath | Out-Null
& $venvPython -m PyInstaller (Join-Path $here "build.spec") --noconfirm --distpath $distPath --workpath $workPath --clean

$exe = Join-Path $distPath "VectorTrack\VectorTrack.exe"
if (Test-Path $exe) {
    Write-Host "Built: $exe" -ForegroundColor Green
} else {
    Write-Host "Build finished but exe not found at expected path." -ForegroundColor Yellow
    exit 1
}

# 3) Optional: compile installer via Inno Setup.
if ($WithInstaller) {
    $installerScript = Join-Path $here "build_installer.ps1"
    if (-not (Test-Path $installerScript)) {
        Write-Host "Missing build_installer.ps1" -ForegroundColor Red
        exit 1
    }
    & $installerScript
}
