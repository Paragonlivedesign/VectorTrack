param(
    [string]$InnoCompilerPath = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$spec = Join-Path $here "installer.iss"

if (-not (Test-Path $spec)) {
    Write-Host "Missing installer.iss at $spec" -ForegroundColor Red
    exit 1
}

$distExe = Join-Path $here "dist\VectorTrack\VectorTrack.exe"
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
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    Write-Host "Inno Setup compiler not found. Install Inno Setup 6 or pass -InnoCompilerPath." -ForegroundColor Red
    exit 1
}

Write-Host "Using ISCC: $iscc" -ForegroundColor Cyan
& $iscc $spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installer build failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Installer built in dist\installer\" -ForegroundColor Green
