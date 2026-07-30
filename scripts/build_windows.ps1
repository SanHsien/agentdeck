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

Push-Location $RepoRoot
try {
    uv run --no-sync python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --name agentdeck `
        --distpath $DistRoot `
        --workpath $BuildDir `
        --specpath $SpecDir `
        --add-data "$(Join-Path $RepoRoot 'i18n.json');." `
        --add-data "$(Join-Path $RepoRoot 'pyproject.toml');." `
        --add-data "$(Join-Path $RepoRoot 'assets');assets" `
        `# packaged_resource_path asks for "windows/..." and "critters/..." without
        `# an assets/ prefix, so those subtrees are declared under those names too.
        --add-data "$(Join-Path $RepoRoot 'assets/windows');windows" `
        --add-data "$(Join-Path $RepoRoot 'assets/critters');critters" `
        `# persona_store reads role definitions from personas/ at runtime.
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
