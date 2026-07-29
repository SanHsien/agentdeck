<p align="center">
  <img src="docs/readme-logo.png" alt="usage logo" width="128">
</p>

# usage

### Quota visibility for Claude Code, Codex, and Antigravity, built into the macOS menu bar and Windows system tray.

Keep Claude Code, Codex, and Antigravity quota in view while you work. `usage` puts session limits, weekly limits, and cost context in the macOS menu bar or Windows system tray, so you can manage usage before it interrupts a session.

[繁體中文](README.md) · English &nbsp;|&nbsp; [Landing page](https://sanhsien.github.io/usage/)

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](#install)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

> This is a fork of [`aqua5230/usage`](https://github.com/aqua5230/usage), maintained independently with no upstream contributions planned. The UI ships in Traditional Chinese and English only. Upstream's Discussions and star count belong to that project and are no longer mirrored here; **installers still come from upstream's Releases** (this fork publishes none). The landing page is served from this repo's `docs/`.

<p align="center">
  <img src="docs/showcase.en.png" alt="usage — Claude Code, Codex, and Antigravity quota pinned to the macOS menu bar" width="820">
</p>

`usage` keeps your **Claude Code, Codex, and Antigravity** quota pinned to the top-right of your screen, color-coded so warning levels read at a glance. Claude Code and Codex numbers are read passively from local files already on your machine, and reading them **never calls Anthropic or OpenAI's LLM APIs** — so watching your quota never adds to your token usage. Antigravity quota comes from Google's official quota endpoint, using the sign-in the Antigravity CLI already stores locally.

## Why usage?

Running out of quota mid-session is expensive — especially during a long refactor or debugging run that depends on Claude Code. `usage` surfaces 5-hour and weekly limits *before* you hit the wall, and keeps them visible the whole time. There's no command to run and no page to open; the answer is just there, where you already look.

## Quick Start

```bash
brew install --cask aqua5230/usage/usage
```

It lands in your Applications folder automatically. Right-click **Open** once to pass Gatekeeper, then click the menu bar icon. Prefer a direct download or want the full setup flow? See [Install](#install) below.

## What You Get

### Live Visibility

- **Always-on Monitor:** Your quota lives in the menu bar, color-coded from green to red. Click when you want the full session, weekly, and per-project breakdown.
- **Antigravity Support:** Antigravity (Gemini) session and weekly quota show up as a third card in every panel. Numbers come straight from the official quota API, using the sign-in the Antigravity CLI already keeps on your machine — refreshed every few minutes, with live reset countdowns.
- **Service Status Alerts:** An orange-red banner appears when Claude Code, Claude API, or Codex API has an outage or degraded performance, read from their public Statuspage.io pages — never an LLM usage API. Antigravity isn't covered; it has no public status page.
- **Context Nudges & Notifications:** When your context window hits 70%, the status line nudges you to `/clear` or `/compact` to prevent token waste. You can also opt-in to system notifications for quota limits and recoveries.
- **Hide Sections:** Only use one or two of the tools? Hide the Claude Code, Codex, or Antigravity section from the menu bar and panels completely with a single click.

### Workflow Helpers

- **Progress Concierge:** Open a new Claude Code session and `usage` hands your last progress straight to the AI, including your last request, uncommitted changes, and unfinished todos. No `/resume`, no recap. Fully local, off by default.
- **Token Saver:** A menu-bar toggle asks Claude Code and Codex to answer more tersely, saving output tokens while keeping code and error messages byte-exact. A light reminder keeps long conversations from drifting back to verbose — tested to keep late replies ~40% shorter.
- **Token-waste Health Check:** A daily background diagnosis scans your logs for waste, including repeated file reads, polluter directories, and noisy Bash output. If it finds issues, a one-line heads-up appears; say "show me" and the AI walks you through fixes.

### Reporting & Insight

- **Deep HTML Reports:** Shareable HTML reports of daily and weekly token trends, project rankings, and cost — including a Year in Review with a contribution heatmap and "Wrapped" summary. Export as .html, .csv, or .png, fully offline, with optional project-name masking.
- **TUI & CLI:** Prefer the terminal? Run the rich TUI dashboard with `python3 main.py --tui`, or generate deep analytics with `python3 usage_cli.py report`.

### Experience & Customization

- **10 Visual Themes:** Switch between panel styles including Classic, Matrix, Windows 95, Newspaper, Cloud Observation, Midnight Aquarium, Prism Arcade, Black Hole, World Cup 2026, and Lepidoptera (blueprint).
- **Drag to Reorder:** Grab any quota card and drag it up or down to swap the order — the arrangement is shared across every theme and survives restarts.
- **AI Talent Market:** Bring a ready-made AI team into Claude Code. Browse and install curated subagent personas into `~/.claude/agents/` instantly. Runs fully locally via the bundled CLI.
- **AI Council:** Open a dedicated window and run a multi-round discussion between Claude Code, Codex, and Antigravity — pick participants, models, and a debate style, with a token estimate up front. Steer it between rounds, see who dissents in the consensus tally, and let it stop early once everyone agrees. Seats can wear AI Talent Market personas and reference real files via an optional read-only folder.
- **AI Update Daily:** Opens a daily-updated public [page](https://aqua5230.github.io/ai-updates/) covering Claude Code, Codex, and Antigravity, with the full history kept. Reviewed items get a plain-language summary (that page carries its own set of languages, independent of this app's UI languages); unreviewed ones show the original source text.
- **Spirit Companions:** A small animated white silhouette lives beside your usage percentages — a phoenix for Claude, a dragon for Codex, a lion for Antigravity. Each accelerates dynamically as its own tool's token burn rate climbs.
- **Automatic Localization:** UI text is available in Traditional Chinese and English, automatically matching your system settings. Every Chinese locale (Simplified included) resolves to Traditional Chinese; everything else falls back to English.

## Privacy & Data Sources

- Claude Code and Codex numbers are read **only from local log files** on your machine; reading them **never calls Anthropic or OpenAI's LLM APIs**.
- Antigravity quota requires network access, and only if you use it: quota is fetched from Google's official quota endpoint using the OAuth credential the Antigravity CLI already stored after sign-in — read from macOS Keychain, Windows Credential Manager, or a local token file depending on CLI version. `usage` reads that credential without writing it back and keeps any refreshed access token in memory only; the call itself only reads quota metadata and never consumes your model quota.
- Background network activity: the Antigravity quota/token endpoints above, public Claude and Codex status pages to flag outages, a public model-pricing table to estimate cost (falls back to built-in prices offline), and occasionally checking GitHub for a new version. Claude Code and Codex log contents are never uploaded.

## Requirements

- macOS 12 (Monterey) or newer, or Windows 10/11
- Claude Code, Codex, or Antigravity has been used at least once (so local usage data exists).
- (Source runs only) Python 3.13.

## Install

### 1. Homebrew (Recommended)

Installing via Homebrew means a single `brew upgrade --cask usage` keeps it current.

```bash
brew install --cask aqua5230/usage/usage
```

*(First launch: right-click `usage.app` in Finder → **Open** to pass Gatekeeper).*

### 2. Download for macOS

1. Download the latest `usage.app.zip` from the [GitHub Releases page](https://github.com/aqua5230/usage/releases/latest).
2. Unzip it and drag `usage.app` into your Applications folder.
3. First launch: in Finder, right-click `usage.app` → **Open** → confirm Open.

## Windows Support

Windows has the full core experience: the TUI, Claude Code status-line hook, and Codex history parsing all work natively. Download `usage-windows.zip` from the [latest GitHub Release](https://github.com/aqua5230/usage/releases/latest), unzip it, then run `usage.exe`—no installer is needed. The tray UI requires Microsoft Edge WebView2 Runtime, which is normally included with Windows 10 and 11.

The system-tray icon updates with your Claude quota percentage; its tooltip summarizes the Claude and Codex windows. Left-click opens the same 10 quota themes available on macOS (Classic plus the other nine) in WebView2. Right-click provides panel switching, refresh, launch at login, check for updates, and quit.

Windows differences: the panel opens at the bottom-right of the working area rather than next to the tray icon; update prompts use a system Yes/No dialog; and the AI Talent Market and AI Council panels are macOS-only.

### First Launch: Set Up the Status Line

If you've used Codex, `usage` picks up its history automatically. For Claude Code, click the **"Set Up Status Line"** button in the app popover to install the sync hook.
Restart the relevant tool afterward (fully Cmd+Q Claude Code and re-open it).

Once set up, the bottom of the Claude Code window will show a status line like this:

<p align="center">
  <img src="docs/statusline.en.png" alt="Claude Code statusLine display (English)" width="640">
</p>

## Theme Gallery

Switch between **10 visual themes** directly from the UI:

<p align="center">
  <img src="docs/matrix.en.png" width="32%" alt="Matrix theme" />
  <img src="docs/win95.en.png" width="32%" alt="Windows 95 theme" />
  <img src="docs/world_cup.en.png" width="32%" alt="World Cup HUD theme" />
  <img src="docs/newspaper.en.png" width="32%" alt="Newspaper theme" />
  <img src="docs/aquarium.en.png" width="32%" alt="Aquarium theme" />
  <img src="docs/black_hole.en.png" width="32%" alt="Black Hole theme" />
</p>

## Troubleshooting

If the menu bar shows `--`, it's usually not broken — there's just no local data yet.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Menu bar shows `--` | No data yet, or Claude Code hook not refreshed | Run one Codex conversation. For Claude Code, click "Set Up Status Line" or run `python3 main.py --setup` |
| Accidentally hit "Quit" | Process terminated | Relaunch `usage.app` from Spotlight or Applications. (`launchctl start com.lollapalooza.usage` only works if you enabled Launch at Login.) |
| Status says "N minutes stale" | Claude Code isn't running | Open Claude Code and let it run |
| Codex section is empty | No Codex history found | Run a Codex conversation to generate logs |
| Today's cost shows $0.00 | Model pricing missing | Delete `~/.usage/pricing_cache.json` or check `USAGE_DEBUG=1` |
| Antigravity card is missing | Antigravity CLI not installed or not signed in | Install and sign in to the Antigravity CLI; the card appears automatically once a background quota fetch succeeds |
| App won't open | macOS Gatekeeper blocked it | Right-click `usage.app` in Finder → Open |
| App crashes immediately (arm64) | py2app bundling bug in older versions | Upgrade to **v0.11.1 or newer** |

## Comparison

| Feature | usage | ccusage | TokenTracker |
|---------|:-----:|:-------:|:------------:|
| Always on screen | ✅ | — | ✅ |
| macOS menu bar | ✅ | — | ✅ |
| Claude Code & Codex usage | ✅ | Claude only | ✅ |
| Antigravity (Gemini) usage | ✅ | — | — |
| Claude Code & Codex service-status alerts | ✅ | — | — |
| HTML deep reports & UI | ✅ | ✅ | — |
| AI Talent Market | macOS only | — | — |
| AI Council | macOS only | — | — |
| AI Update Daily | ✅ | — | — |
| Progress Concierge & Token Saver | ✅ | — | — |
| Token-waste Health Check | ✅ | — | — |
| No LLM API calls to read quota | ✅ | ✅ | ✅ |
| Open-source license | AGPL-3.0 | MIT | — |

## Development

Want to run the terminal TUI, configure custom agents, or build the app yourself? Check out the **[development docs](docs/DEVELOPMENT.md)**.

## Other Reference Projects

The projects below are **conceptual and workflow references only** — they are not runtime dependencies of `usage`, and none of their source code has been incorporated. A project with no declared license is legally all-rights-reserved and cannot be merged into this AGPL-3.0 repository, so it serves purely as a point of comparison.

| Name | License | What's worth referencing |
| --- | --- | --- |
| [karpathy/llm-council](https://github.com/karpathy/llm-council) | Undeclared | A three-stage pipeline for having several models answer one question together: each model answers independently → they rank each other's **anonymized** answers → a designated "chairman" model compiles the final answer. Same family of design as this project's AI Council (multi-round discussion, consensus tally); the **anonymized peer review** — hiding model identity so rankings aren't swayed by reputation — is the part most worth comparing against. Technically it runs on OpenRouter + FastAPI + React, unlike this project's offline, local-CLI-driven approach. |

## License

Licensed under **AGPL-3.0-only** (see [LICENSE](LICENSE)). Original copyright belongs to the upstream author, lollapalooza; the original project is at:
https://github.com/aqua5230/usage

All modifications in this fork are released under AGPL-3.0-only as well, preserving upstream's copyright notice and license terms. If you fork or redistribute a modified version, you must ship the corresponding complete source, keep it under AGPL-3.0, and credit the origin — and offering it as a network service carries the same source-availability obligation. See [`NOTICE.md`](NOTICE.md) for the full statement.
