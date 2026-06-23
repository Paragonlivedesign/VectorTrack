param(
    [string]$InnoCompilerPath = "",
    [string]$AppSource = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$spec = Join-Path $here "installer.iss"
$releaseRoot = Join-Path $here "release"
if (-not $AppSource) {
    $AppSource = $releaseRoot
}

if (-not (Test-Path $spec)) {
    Write-Host "Missing installer.iss at $spec" -ForegroundColor Red
    exit 1
}

$distExe = Join-Path $AppSource "VectorTrack.exe"
if (-not (Test-Path $distExe)) {
    Write-Host "Build the app first: .\build.ps1" -ForegroundColor Yellow
    exit 1
}

$candidates = @()
if ($InnoCompilerPath) {
    $candidates += $InnoCompilerPath
}
$candidates += @(
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    Write-Host "Inno Setup 6 is not installed on this machine." -ForegroundColor Yellow
    Write-Host "Download: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}

$installerOut = Join-Path $here "dist\installer"
New-Item -ItemType Directory -Force -Path $installerOut | Out-Null

Write-Host "Using ISCC: $iscc" -ForegroundColor Cyan
Write-Host "App source: $AppSource" -ForegroundColor Cyan
& $iscc "/DAppSource=$AppSource" $spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installer build failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

$setupExe = Join-Path $installerOut "VectorTrack-0.5.0-Setup.exe"
if (-not (Test-Path $setupExe)) {
    Write-Host "Build finished but setup exe not found at expected path." -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
Copy-Item $setupExe (Join-Path $releaseRoot "VectorTrack-0.5.0-Setup.exe") -Force
Write-Host "Installer built: $setupExe" -ForegroundColor Green
Write-Host "Release copy: $(Join-Path $releaseRoot 'VectorTrack-0.5.0-Setup.exe')" -ForegroundColor Green
