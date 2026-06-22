# Copy VectorTrack v4 sources and build to _2 Beta Testing.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$devRoot = Split-Path (Split-Path $root -Parent) -Parent
$betaRoot = Join-Path (Split-Path $devRoot -Parent) "_2 Beta Testing"
$betaRoot = [System.IO.Path]::GetFullPath($betaRoot)

$standaloneSrc = $root
$standaloneDst = Join-Path $betaRoot "VectorTrack v4"
$scriptSrc = Join-Path (Split-Path $root -Parent) "VectorTrackScript v3"
$scriptDst = Join-Path $betaRoot "VectorTrackScript v4"
$buildSrc = "C:\Temp\VectorTrackBuild\VectorTrack"

function Sync-Folder {
    param([string]$Source, [string]$Destination, [string[]]$Exclude = @())
    if (-not (Test-Path $Source)) {
        throw "Missing source: $Source"
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    robocopy $Source $Destination /MIR /XD .pytest_cache build dist __pycache__ logs reports .git /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed for $Source -> $Destination (exit $LASTEXITCODE)"
    }
}

Write-Host "Beta root: $betaRoot" -ForegroundColor Cyan
Sync-Folder -Source $standaloneSrc -Destination $standaloneDst
Sync-Folder -Source $scriptSrc -Destination $scriptDst

if (Test-Path $buildSrc) {
    $releaseDst = Join-Path $standaloneDst "release"
    New-Item -ItemType Directory -Force -Path $releaseDst | Out-Null
    robocopy $buildSrc $releaseDst /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    Write-Host "Copied build to $releaseDst" -ForegroundColor Green
} else {
    Write-Host "Build not found at $buildSrc - run build.ps1 first." -ForegroundColor Yellow
}

Write-Host "Beta deployment complete." -ForegroundColor Green
