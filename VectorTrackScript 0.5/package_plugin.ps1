# ============================================================================
# VectorTrackScript 0.5 - Plugin Packaging Script
# ============================================================================
# 1. Create the menu command in Vectorworks Plug-in Manager (name must match
#    folder: "VectorTrackScript 0.5"). Paste VSM_WRAPPER.py into the script.
# 2. Copy the generated .vsm from your Plug-ins folder to this directory.
# 3. Run: .\package_plugin.ps1
# ============================================================================

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginSrc = $base
$outZip = Join-Path $base "VectorTrackScript_0.5.zip"
$vsmName = "VectorTrackScript 0.5.vsm"
$vsmPath = Join-Path $base $vsmName
$zipFolderName = "VectorTrackScript 0.5"

$includeFiles = @(
    "vectortrackscript_main.py",
    "vectortrack_log.py",
    "vectortrack_rates.py",
    "vectortrack_dialog.py",
    "vectortrack_config.py",
    "vectortrack_sync.py",
    "vectortrack_sync_dialog.py",
    "VSM_WRAPPER.py",
    "README.md"
)

if (-not (Test-Path $vsmPath)) {
    Write-Host "WARNING: $vsmName not found in $base" -ForegroundColor Yellow
    Write-Host "Create the plugin in Vectorworks, then copy the .vsm here before distributing." -ForegroundColor Yellow
}

$tempDir = Join-Path $env:TEMP "VectorTrackScript_0.5_build"
if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
$folder = Join-Path $tempDir $zipFolderName
New-Item -ItemType Directory -Path $folder -Force | Out-Null

if (Test-Path $vsmPath) {
    Copy-Item $vsmPath (Join-Path $folder $vsmName) -Force
    Write-Host "  $vsmName" -ForegroundColor Gray
}

foreach ($file in $includeFiles) {
    $src = Join-Path $pluginSrc $file
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $folder $file) -Force
        Write-Host "  $file" -ForegroundColor Gray
    }
}

if (Test-Path $outZip) { Remove-Item $outZip -Force }
Compress-Archive -Path $folder -DestinationPath $outZip -Force
Remove-Item $tempDir -Recurse -Force

Write-Host ""
Write-Host "Created: $outZip" -ForegroundColor Green
Write-Host "Install: Tools > Plug-ins > Plug-in Manager > Third-party Plug-ins > Install..." -ForegroundColor Cyan
