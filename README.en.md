<p align="center">
  <img src="docs/readme-logo.png" alt="agentdeck logo" width="128">
</p>

# agentdeck — Windows AI Coding Cockpit

### Put Claude Code, Codex, and Antigravity quota, collaboration tools, and reports in the Windows system tray

[繁體中文](README.md) · English &nbsp;|&nbsp; [Project site](https://sanhsien.github.io/agentdeck/)

[![Release](https://img.shields.io/github/v/release/SanHsien/agentdeck?sort=semver&color=ff8c42)](https://github.com/SanHsien/agentdeck/releases/latest)
[![CI](https://github.com/SanHsien/agentdeck/actions/workflows/check.yml/badge.svg)](https://github.com/SanHsien/agentdeck/actions/workflows/check.yml)
[![CodeQL](https://github.com/SanHsien/agentdeck/actions/workflows/codeql.yml/badge.svg)](https://github.com/SanHsien/agentdeck/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4.svg?logo=windows11&logoColor=white)](#requirements-and-installation)
[![Local-first](https://img.shields.io/badge/architecture-local--first-2E7D32.svg)](#data-and-privacy)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

<p align="center">
  <img src="docs/hero.png" alt="agentdeck — Windows AI coding cockpit" width="820">
</p>

**agentdeck** is a Windows-only AI coding cockpit. It keeps Claude Code, Codex, and Antigravity quota visible in the system tray and puts multi-model council sessions, deployable subagent personas, workflow handoff, and local usage reports in the same tool.

Claude Code and Codex quota data comes from **files already on your machine**; agentdeck does not call Anthropic or OpenAI usage APIs. Antigravity quota is fetched from Google's official quota endpoint using the login state already maintained by the Antigravity CLI.

> **Windows-only fork.** This repository is derived from [`aqua5230/usage`](https://github.com/aqua5230/usage) and independently maintained under AGPL-3.0-only. macOS support has been removed; use upstream if you need the macOS menu-bar app.

## What it is

When several AI coding CLIs are part of the same workflow, the painful failure mode is often not a missing model — it is discovering mid-task that a provider is near its quota, context has become too large, or the previous session's state is scattered across tools.

agentdeck brings that operational state back into the Windows desktop workflow:

- **See quota** — keep Claude Code, Codex, and Antigravity quota, reset times, and warning levels in the tray.
- **Resume work** — optional Progress Concierge, Token Saver, and post-reset auto-resume reduce repeated context handoff.
- **Let models collaborate** — AI Council can run installed Claude Code, Codex, and Antigravity CLIs in a multi-round discussion with voting.
- **Reuse roles** — the Persona Market installs the same role set into Claude Code, Codex, and Cursor, backing up name collisions first.
- **Review long-term usage** — HTML / CSV / PNG reports summarize daily, weekly, project, and cost trends.

## Core capabilities

| Capability | What it does |
|---|---|
| **Quota cockpit** | System-tray quota, reset countdowns, burn rate, Context Window warnings, and public Claude/Codex service status. |
| **Local Claude Code / Codex data** | Claude reads a local statusLine snapshot or Claude Desktop's local plan-usage history; Codex reads session / state data under `~/.codex/`. Viewing quota does not consume LLM usage. |
| **Antigravity quota** | Uses the Antigravity CLI's existing local login state to query Google's official quota endpoint; the quota check itself does not consume model usage. |
| **AI Council** | Choose participants, models, personas, and debate style; run multiple rounds, intervene between rounds, count consensus, and optionally attach a read-only folder. |
| **Persona Market** | Open persona definitions live in [`personas/`](personas/); install them into Claude Code, Codex, and Cursor with backup-before-overwrite behavior. |
| **Workflow helpers** | Progress Concierge, Token Saver, token-waste diagnostics, and optional Windows-scheduled resume after quota reset. |
| **Local reports** | Rich HTML reports, CSV / PNG export, project trends, and Year in Review; project names can be hidden. |
| **Tray + TUI + CLI** | WebView2 tray panels are the primary UI, with a Rich TUI and terminal report CLI as alternatives. |

Four visual themes ship with the app: Classic, Catppuccin, Stained Glass, and Origami. Themes share one behavior core and only change presentation.

<p align="center">
  <img src="docs/classic.png" width="24%" alt="Classic theme" />
  <img src="docs/catppuccin.png" width="24%" alt="Catppuccin theme" />
  <img src="docs/stained_glass.png" width="24%" alt="Stained Glass theme" />
  <img src="docs/origami.png" width="24%" alt="Origami theme" />
</p>

## Quick start

1. Download `agentdeck-windows.zip` from the [Latest Release](https://github.com/SanHsien/agentdeck/releases/latest).
2. Extract it and run `agentdeck.exe`; there is no installer.
3. **Codex** — existing local usage history is detected automatically.
4. **Claude Code** — terminal users can install the local hook with **Set Up Status Line** and restart Claude Code; Claude Desktop users are detected through the plan-usage history Desktop already writes locally.
5. **Antigravity** — install and sign in to the Antigravity CLI first; its quota card appears after a successful quota read.

Left-click the tray icon to open the panel and right-click for the menu. Panels are draggable floating windows that remember their position rather than transient popovers tied to the tray icon.

## Data and privacy

agentdeck is local-first, but local-first does not mean fully offline. Each data source has a different contract:

| Source | How agentdeck gets it | Network |
|---|---|---:|
| Claude Code | Reads `~/.claude/agentdeck-status.json`, Claude Desktop's `plan-usage-history.json`, and local project history | No |
| Codex | Read-only access to `~/.codex/sessions/` / local state | No |
| Antigravity | Uses local CLI auth to query Google's official quota endpoint | Yes |
| Service health | Public Claude / OpenAI Statuspage endpoints | Yes |
| Cost estimates | Public pricing data cached locally; built-in fallback when offline | Yes |
| Update check | This repository's GitHub Releases API | Yes, optional |

**Claude Code / Codex conversation logs are not uploaded to a project-operated backend; this project has no telemetry backend.** AI Council launches provider CLIs already installed on your machine. Those CLIs may send prompts or referenced file content according to each provider's own behavior and the instructions you give them.

Persona installation writes into the corresponding agent configuration directories and backs up same-name files before replacement. Claude statusLine setup changes the relevant entry in `~/.claude/settings.json` while preserving the previous value so uninstall can restore it.

See [`NOTICE.md`](NOTICE.md) and the [development guide](docs/DEVELOPMENT.md) for the full data-location, network-endpoint, and licensing boundaries.

## Requirements and installation

- Windows 10 / 11
- Microsoft Edge WebView2 Runtime (normally already present on Windows 10 / 11)
- Prior use of at least one of Claude Code, Codex, or Antigravity
- Python 3.13 and `uv` only if running from source

Releases provide a portable Windows zip plus `.sha256`. The [Latest Release](https://github.com/SanHsien/agentdeck/releases/latest) is the source of truth for the current downloadable version; the README intentionally does not hard-code a version number.

## Run from source

```powershell
uv sync --frozen --group dev --extra windows
uv run --no-sync python main.py            # Windows system tray
uv run --no-sync python main.py --tui      # Rich TUI
uv run --no-sync python main.py --mock     # preview with fake data
uv run --no-sync python main.py --doctor   # environment / hook diagnostics
uv run --no-sync python usage_cli.py report
```

Run the complete local validation set with:

```powershell
pwsh tools/dev_check.ps1
```

CI checks lockfile freshness, ruff, mypy, bilingual-document parity, guarded file sizes, and pytest. Development, packaging, and Windows-specific traps are documented in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Fork and upstream

agentdeck is a modified version of [`aqua5230/usage`](https://github.com/aqua5230/usage), not a from-scratch repository. Since 2026-07-29 this fork has developed as a **Windows-only, Traditional Chinese / English, independently maintained product**, while selectively reviewing upstream work.

Key divergences include:

- macOS menu-bar / `.app` paths removed; Windows tray + WebView2 is the product UI.
- Product-facing names and newly written user data use `agentdeck`.
- Antigravity, AI Council, open personas, Windows auto-resume, and multiple Windows compatibility fixes were added here.
- Shipped UI languages are Traditional Chinese and English.

See [`NOTICE.md`](NOTICE.md) for the AGPL-3.0 §5a modification statement, [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md) for fork mechanics, and [`docs/UPSTREAM.md`](docs/UPSTREAM.md) for adopted / skipped upstream commits.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Windows development environment, validation, packaging, and architecture details |
| [`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md) | Principles and examples for porting upstream behavior to Windows |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Durable product / architecture decisions |
| [`docs/UPSTREAM.md`](docs/UPSTREAM.md) | Upstream review, adopted commits, and skipped commits |
| [`ROADMAP.en.md`](ROADMAP.en.md) | Product direction and future work |
| [`CHANGELOG.en.md`](CHANGELOG.en.md) | User-visible release history |
| [`NOTICE.md`](NOTICE.md) | Fork attribution, modification statement, data, and licensing boundaries |
| [`SECURITY.en.md`](SECURITY.en.md) | Vulnerability reporting and support policy |

## License

**AGPL-3.0-only.** This repository is a derivative of `aqua5230/usage` and preserves upstream copyright and license notices. Modifications in this fork are also released under AGPL-3.0-only. See [`LICENSE`](LICENSE) for the license text and [`NOTICE.md`](NOTICE.md) for source and modification statements.
