$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $RepoRoot "dist"
$OutputDir = Join-Path $DistRoot "agentdeck-windows"
$PyInstallerOutput = Join-Path $DistRoot "agentdeck"
$BuildDir = Join-Path $RepoRoot "build/pyinstaller-windows"
$SpecDir = Join-Path $RepoRoot "build/pyinstaller-spec"

Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $PyInstallerOutput -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue

# The project is a uv virtual root and is never installed, so the version comes
# from pyproject.toml via _current_version()'s fallback. A stale *.egg-info left
# by the old setuptools build makes importlib.metadata resolve first and win,
# and PyInstaller bakes that older version into the exe. A fresh CI checkout has
# no egg-info, so this only ever goes wrong on the machine that cuts releases.
foreach ($stale in Get-ChildItem -Path $RepoRoot -Filter "*.egg-info" -Directory -ErrorAction SilentlyContinue) {
    Write-Host "removing stale metadata: $($stale.Name)" -ForegroundColor Yellow
    Remove-Item $stale.FullName -Recurse -Force
}

# packaged_resource_path asks for "windows/...", "critters/..." and "personas"
# without an assets/ prefix, so those subtrees are declared under those names as
# well as under assets/ — see tests/test_packaged_resources.py.
Push-Location $RepoRoot
try {
    # Without this the shipped exe has no product name and no version: the file
    # properties dialog is blank and a downloaded binary cannot be identified
    # without running it.
    $VersionFile = Join-Path $SpecDir "agentdeck-version-info.txt"
    uv run --no-sync python scripts/make_version_file.py $VersionFile

    uv run --no-sync python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --version-file $VersionFile `
        --name agentdeck `
        --distpath $DistRoot `
        --workpath $BuildDir `
        --specpath $SpecDir `
        --add-data "$(Join-Path $RepoRoot 'i18n.json');." `
        --add-data "$(Join-Path $RepoRoot 'pyproject.toml');." `
        --add-data "$(Join-Path $RepoRoot 'assets');assets" `
        --add-data "$(Join-Path $RepoRoot 'assets/windows');windows" `
        --add-data "$(Join-Path $RepoRoot 'assets/critters');critters" `
        --add-data "$(Join-Path $RepoRoot 'personas');personas" `
        --add-data "$(Join-Path $RepoRoot 'usage_statusline.py');." `
        --add-data "$(Join-Path $RepoRoot 'usage_statusline_forwarder.py');." `
        --add-data "$(Join-Path $RepoRoot 'usage_session_resume.py');." `
        --add-data "$(Join-Path $RepoRoot 'usage_terse_mode.py');." `
        --add-data "$(Join-Path $RepoRoot 'usage_terse_reminder.py');." `
        --hidden-import wintray `
        --hidden-import pystray `
        --hidden-import webview `
        --hidden-import webview.platforms.edgechromium `
        --hidden-import tui `
        --hidden-import session_hooks `
        --hidden-import setup_hook `
        --hidden-import adapters.registry `
        --hidden-import analyzer.reporter `
        --hidden-import ui.html_report `
        --collect-all pystray `
        --collect-all webview `
        main.py

    Move-Item $PyInstallerOutput $OutputDir
} finally {
    Pop-Location
}

$Executable = Join-Path $OutputDir "agentdeck.exe"
if (-not (Test-Path $Executable -PathType Leaf)) {
    throw "PyInstaller did not produce $Executable"
}

# AGPL-3.0 §4 requires every copy of the program to carry the license text, and
# §5a requires a notice that this is a modified version. PyInstaller only bundles
# the *dependencies'* license files, so ship ours next to the executable.
foreach ($doc in @("LICENSE", "NOTICE.md", "README.md")) {
    $source = Join-Path $RepoRoot $doc
    if (-not (Test-Path $source -PathType Leaf)) {
        throw "Required distribution document is missing: $doc"
    }
    Copy-Item $source (Join-Path $OutputDir $doc)
}

# Ask the executable what version it thinks it is. Reading pyproject.toml here
# would only re-check the input; the failure this guards against is the built
# artifact disagreeing with the tree it was built from.
$declared = (Select-String -Path (Join-Path $RepoRoot "pyproject.toml") -Pattern '^version = "(.+)"' |
    Select-Object -First 1).Matches[0].Groups[1].Value
$doctor = & $Executable --doctor 2>&1 | Out-String
if ($doctor -notmatch "agentdeck v([0-9]+\.[0-9]+\.[0-9]+)") {
    throw "agentdeck.exe --doctor did not report a version. Output:`n$doctor"
}
$reported = $Matches[1]
if ($reported -ne $declared) {
    throw "Version mismatch: pyproject.toml says $declared but the built exe reports $reported."
}
Write-Host "version check: exe reports $reported, matching pyproject.toml" -ForegroundColor Green
