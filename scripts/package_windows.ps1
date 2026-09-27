# SPDX-License-Identifier: AGPL-3.0-only
<#
.SYNOPSIS
    Zip the built Windows bundle and write its SHA-256.

.DESCRIPTION
    Local releases and the GitHub release workflow both call this, so the asset
    a maintainer uploads by hand is byte-for-byte the same shape as the one CI
    produces. They used to diverge: CI zipped the directory (nested folder) and
    the local step zipped its contents (flat), which meant the two paths shipped
    different layouts under the same filename.

    The bundle is zipped as a directory, so unzipping never sprays ~100 files
    into whatever folder the user downloaded to.
#>
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BundleDir = Join-Path $RepoRoot "dist/agentdeck-windows"
$Zip = Join-Path $RepoRoot "dist/agentdeck-windows.zip"
$Sha = "$Zip.sha256"

if (-not (Test-Path $BundleDir -PathType Container)) {
    throw "No bundle at $BundleDir. Run scripts/build_windows.ps1 first."
}
if (-not (Test-Path (Join-Path $BundleDir "agentdeck.exe") -PathType Leaf)) {
    throw "$BundleDir has no agentdeck.exe."
}

Remove-Item $Zip, $Sha -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $BundleDir -DestinationPath $Zip -CompressionLevel Optimal

$hash = (Get-FileHash $Zip -Algorithm SHA256).Hash.ToLower()
"$hash  agentdeck-windows.zip" | Out-File -FilePath $Sha -Encoding ascii -NoNewline

$size = [math]::Round((Get-Item $Zip).Length / 1MB, 1)
Write-Host "packaged agentdeck-windows.zip ($size MB)" -ForegroundColor Green
Write-Host "sha256: $hash"
