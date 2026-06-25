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

$version = "0.5.8"
$configPy = Join-Path $here "vectortrack\config.py"
if (Test-Path $configPy) {
    if ($configPy -match 'APP_VERSION\s*=\s*"([^"]+)"') { }
    $match = Select-String -Path $configPy -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($match) {
        $version = $match.Matches[0].Groups[1].Value
    }
}

$setupName = "VectorTrack-$version-Setup.exe"

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

$setupExe = Join-Path $installerOut $setupName
if (-not (Test-Path $setupExe)) {
    $fallback = Get-ChildItem -Path $installerOut -Filter "VectorTrack-*-Setup.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($fallback) {
        $setupExe = $fallback.FullName
    }
}

if (-not (Test-Path $setupExe)) {
    Write-Host "Build finished but setup exe not found at expected path." -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
$releaseCopy = Join-Path $releaseRoot (Split-Path -Leaf $setupExe)
Copy-Item $setupExe $releaseCopy -Force
Write-Host "Installer built: $setupExe" -ForegroundColor Green
Write-Host "Release copy: $releaseCopy" -ForegroundColor Green
