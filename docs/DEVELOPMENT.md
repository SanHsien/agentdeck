# Development

[Traditional Chinese](DEVELOPMENT.zh-TW.md) · English

agentdeck is Windows-only. Fork rules are in [`FORK.zh-TW.md`](FORK.zh-TW.md), the architecture in [`../CLAUDE.md`](../CLAUDE.md), and the method for porting macOS features in [`PORTING.zh-TW.md`](PORTING.zh-TW.md).

## Prerequisites

- **Python 3.13**. `pyproject.toml` requires `>=3.13` and mypy pins 3.13. The default `python` on the maintainer's machine is 3.14 — **do not build the environment with it**: CI runs 3.13, so developing on 3.14 verifies something else.
- **uv**. `uv.lock` is the single source of truth for dependencies.
- `pwsh` (PowerShell 7+).

```powershell
uv python install 3.13
```

## Set up the environment

```powershell
uv sync --frozen --group dev --extra windows
```

This is **exactly** what the CI job runs (`.github/workflows/check.yml`). None of the three parts is optional:

- `--frozen`: install from `uv.lock` without re-resolving.
- `--group dev`: ruff, mypy, pytest.
- `--extra windows`: `pystray`, `pillow`, `pywebview` — what the tray UI needs.

You end up with `.venv\` (Python 3.13, gitignored).

### If the checkout lives in a OneDrive folder

Set `UV_PROJECT_ENVIRONMENT` to a path outside it, for example:

```powershell
setx UV_PROJECT_ENVIRONMENT "C:	mpgentdeck"
```

Inside a OneDrive tree every directory is a Files On-Demand placeholder
(reparse tag `IO_REPARSE_TAG_CLOUD_E`), so the cloud filter driver sits in the
path of every file operation — pausing sync does not detach it. Removing many
package directories at once can then lose a race with that driver and leave the
environment half-uninstalled. Keeping the virtualenv outside also stops OneDrive
from syncing ~5,000 files that `uv.lock` can rebuild in seconds.

`uv run` and `tools/dev_check.ps1` both honour the variable. CI is unaffected —
it never sets it, so runners use `.venv` as before.

## Gates

```powershell
pwsh tools/dev_check.ps1
```

Runs six checks in one go: lock freshness, `ruff check`, `mypy .`, bilingual doc parity, AI updates page freshness, and `pytest`. All green before you commit. Separately:

```powershell
uv lock --check
uv run --no-sync ruff check
uv run --no-sync mypy .
uv run --no-sync python scripts/check_doc_parity.py
uv run --no-sync python scripts/build_ai_updates.py --check
uv run --no-sync pytest -q
```

`--no-sync` avoids re-checking dependencies on every run.

## Running it

```powershell
uv run --no-sync python main.py             # system tray (default)
uv run --no-sync python main.py --tui       # terminal TUI
uv run --no-sync python main.py --mock      # fake data, no real usage needed
uv run --no-sync python main.py --doctor    # environment and hook diagnostics
uv run --no-sync python usage_cli.py report # terminal analytics report
$env:AGENTDECK_DEBUG=1; uv run --no-sync python main.py   # surface swallowed exceptions
```

## Packaging

This is a flat application distributed with PyInstaller, not as a wheel or PyPI package; `[tool.uv] package = false` is intentional. Do not use `uv build` as the release check.

```powershell
pwsh scripts/build_windows.ps1      # produces dist/agentdeck-windows/agentdeck.exe
```

The build script copies `LICENSE`, `NOTICE.md`, and `README.md` next to the executable — AGPL-3.0 §4 requires every copy to carry the license text, and the build fails if any is missing.

After touching anything packaging-related, run `pytest tests/test_packaged_resources.py`. It checks that every resource the code requests through `packaged_resource_path()` is declared to PyInstaller with `--add-data`. A missing declaration raises nothing; it just becomes a file-not-found in the shipped build.

## Things that bite

- **stdlib-only files**: `usage_statusline.py`, `usage_statusline_forwarder.py`, `usage_session_resume.py`, `usage_terse_mode.py`, and `usage_terse_reminder.py` run under whatever `python3` the user's Claude Code finds — not this project's venv — so they **must not import third-party packages**.
- **DPI**: Win32 hands back physical pixels while pywebview's API takes logical ones. Convert with `wintray._monitor_dpi_scale()` / `_to_logical_rect()` or the panel opens off-screen (the bug fixed in v0.30.0).
- **Module filenames are still `usage_*`**: that is internal implementation, deliberately left out of the product rename (see [`DECISIONS.md`](DECISIONS.md) D-09). The names they **install under in `~/.claude/`** are `agentdeck-*`.

## Known local test failure

`test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink` always fails on a machine without symlink privilege (Developer Mode or administrator). That is an **environment limit, not a code bug**: `tools/dev_check.ps1` probes whether symlinks can be created and only then deselects that one test, saying so; CI's windows-latest has the privilege and runs it.
