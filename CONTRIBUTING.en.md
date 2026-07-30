# Contributing

[繁體中文](CONTRIBUTING.md) · English

Issues, PRs are welcome. This document only spells out hard requirements; it does not dictate process.

This fork is independently maintained by [@SanHsien](https://github.com/SanHsien) under a benevolent-dictator model: every PR is reviewed and merged at the maintainer's discretion. Discussion is welcome, but the final call rests with the maintainer.

## Opening an Issue

- **Bug report**: use the `.github/ISSUE_TEMPLATE/bug_report.md` template. Include the Windows version, Python version, `git rev-parse --short HEAD`, and the mode you were running (system tray / TUI / mock / doctor).
- **Feature request**: use the `.github/ISSUE_TEMPLATE/feature_request.md` template.

## Required checks before opening a PR

```powershell
uv sync --frozen --group dev --extra windows
pwsh tools/dev_check.ps1
```

The full gate must be green to merge. It covers lock freshness, ruff, mypy, bilingual docs, the AI updates page, and pytest; CI runs the same checks (`.github/workflows/check.yml`).

## Code change guidelines

- **When changing prod modules, add tests alongside.** Pick the closest existing file under `tests/` as a style reference. Tests must never touch real `~/.claude/` or `~/.codex/` — use `monkeypatch` to redirect path constants.
- **Use `agentdeck` for public names.** The binary, settings keys, on-disk names, and environment variables use `agentdeck` / `AGENTDECK_*`. Internal module names such as `usage_client.py` are deliberately retained historical names.
- **Keep Windows UI logic out of `wintray.py`.** Put new decisions in independently testable leaf modules and keep `wintray.py` as a thin UI shell.

## CHANGELOG and releases

- For every change, add an entry to the `## Unreleased` section of `CHANGELOG.md` (English, the default), **and also update the corresponding section in `CHANGELOG.zh-TW.md`** (this project keeps the README, CHANGELOG, and release notes bilingual).
- Releases are cut by the maintainer (bump version in `pyproject.toml`, rename `## Unreleased` to `## X.Y.Z — YYYY-MM-DD`, commit `Release vX.Y.Z`, push tag).

## Commit message style

Match the existing `git log`: imperative subject line; add a body explaining *why* (not *what* — the diff already shows what) when useful. Example:

```
Fix AttributeError: drop stale tracker.sample() call

072a088 removed UsageRateTracker.sample() but missed the lone caller in
wintray.py:435...
```
