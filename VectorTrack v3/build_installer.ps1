param(
    [string]$InnoCompilerPath = "",
    [string]$AppSource = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$spec = Join-Path $here "installer.iss"

if (-not (Test-Path $spec)) {
    Write-Host "Missing installer.iss at $spec" -ForegroundColor Red
    exit 1
}

if (-not $AppSource) {
    $candidates = @(
        "C:\Temp\VectorTrackBuild\VectorTrack",
        (Join-Path $here "dist\VectorTrack")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate "VectorTrack.exe")) {
            $AppSource = $candidate
            break
        }
    }
}

if (-not $AppSource -or -not (Test-Path (Join-Path $AppSource "VectorTrack.exe"))) {
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
    Write-Host "After installing, run: .\build_installer.ps1" -ForegroundColor Yellow
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

$setupExe = Join-Path $installerOut "VectorTrack-v4-Setup.exe"
if (Test-Path $setupExe) {
    Write-Host "Installer built: $setupExe" -ForegroundColor Green

    $betaInstaller = "I:\My Drive\Software\Vectorworks\Custom Plug ins\_2 Beta Testing\VectorTrack v4\release"
    if (Test-Path (Split-Path $betaInstaller -Parent)) {
        New-Item -ItemType Directory -Force -Path $betaInstaller | Out-Null
        Copy-Item $setupExe (Join-Path $betaInstaller "VectorTrack-v4-Setup.exe") -Force
        Write-Host "Copied to beta: $betaInstaller\VectorTrack-v4-Setup.exe" -ForegroundColor Green
    }
} else {
    Write-Host "Build finished but setup exe not found at expected path." -ForegroundColor Yellow
}
