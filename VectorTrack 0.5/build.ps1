# Build chain for VectorTrack 0.5 standalone.
# Usage:
#   .\build.ps1                  # build executable only
#   .\build.ps1 -WithInstaller   # build executable + Inno Setup installer + release/ copies

param(
    [switch]$WithInstaller
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $here ".venv\Scripts\python.exe"
$distPath = "C:\Temp\VectorTrackBuild"
$workPath = "C:\Temp\VectorTrackWork"
$appSource = Join-Path $distPath "VectorTrack"
$releaseRoot = Join-Path $here "release"

if (-not (Test-Path $venvPython)) {
    Write-Host "Create a venv first: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt pyinstaller" -ForegroundColor Red
    exit 1
}

& $venvPython -m pip install pyinstaller -q

New-Item -ItemType Directory -Force -Path $distPath, $workPath | Out-Null
& $venvPython -m PyInstaller (Join-Path $here "build.spec") --noconfirm --distpath $distPath --workpath $workPath

$exe = Join-Path $appSource "VectorTrack.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but exe not found at expected path." -ForegroundColor Yellow
    exit 1
}
Write-Host "Built: $exe" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
robocopy $appSource $releaseRoot /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Host "Failed to copy portable build to release/" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Portable build copied to $releaseRoot" -ForegroundColor Green

if ($WithInstaller) {
    $installerScript = Join-Path $here "build_installer.ps1"
    if (-not (Test-Path $installerScript)) {
        Write-Host "Missing build_installer.ps1" -ForegroundColor Red
        exit 1
    }
    & $installerScript -AppSource $releaseRoot
}
