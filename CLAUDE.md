# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`agentdeck` is a Windows system tray (and TUI) app that pins Claude Code, Codex, and Antigravity quota usage to the screen and also provides AI Council, persona installation, and local usage reports. Python 3.13, pystray + pywebview (WebView2) for the tray UI, `rich` for the TUI. **No Anthropic/OpenAI usage APIs are ever called** — Claude Code and Codex numbers come from files on disk (a statusLine hook Claude Code writes, and Codex's `~/.codex/sessions/*.jsonl` logs).

## Commands

Environment is managed with `uv`; `uv.lock` is the source of truth. This is a flat application bundled with PyInstaller, not a wheel/PyPI package, so `[tool.uv] package = false` is intentional.

```powershell
# Setup (one-time)
uv sync --frozen --group dev --extra windows

# Run (system tray mode, default)
uv run --no-sync python main.py
uv run --no-sync python main.py --mock        # preview with fake data
uv run --no-sync python main.py --tui         # terminal TUI mode
uv run --no-sync python main.py --setup       # install Claude Code statusLine hook
uv run --no-sync python main.py --unsetup     # uninstall Claude Code statusLine hook
$env:AGENTDECK_DEBUG=1; uv run --no-sync python main.py

# Pre-PR checks — runs the same six gates as CI
pwsh tools/dev_check.ps1

# Single test
uv run pytest tests/test_usage_client.py::test_name -v

# Build the Windows bundle (output: dist/agentdeck-windows/agentdeck.exe)
pwsh scripts/build_windows.ps1
```

Tests **must not** touch real `~/.claude/` or `~/.codex/` files — patch the path constants with `monkeypatch` (see existing tests for the pattern). CI gates lock freshness, ruff, mypy, bilingual document parity, guarded file sizes, and pytest in `.github/workflows/check.yml`.

## Architecture

### Data flow — how quota numbers get on screen

Two separate input channels feed one UI:

```
Claude Code ──stdin──> usage_statusline.py (hook) ──write──> ~/.claude/agentdeck-status.json
                                                                       │
~/.codex/sessions/*.jsonl  (Codex writes these natively) ──┐           │
                                                            ▼           ▼
                                              providers/codex_loader  usage_client.py
                                                            └────┬──────┘
                                                                 ▼
                                                   wintray.py  /  tui.py
```

- **Claude Code side**: `usage_statusline.py` is installed into `~/.claude/agentdeck-statusline.py` by `setup_hook.py` and wired into `~/.claude/settings.json`'s `statusLine`. Every time Claude Code refreshes its status line, it pipes the session JSON to the hook on stdin; the hook atomically writes it to `~/.claude/agentdeck-status.json`. The UI reads that file — never the network.
- **Codex side**: every Codex path goes through `codex_paths.codex_home()`, which honours `CODEX_HOME` and falls back to `~/.codex` — someone running a second account or a containerised Codex previously got a blank Codex card with no error. The constants are computed at import, so a changed `CODEX_HOME` takes effect on restart. `providers/codex_loader.py` scans `sessions/**/*.jsonl` and pulls `rate_limits` straight from the conversation logs. This used to be documented as "no hook is possible"; that is no longer true — Codex CLI 0.129 ships `codex plugin` with a marketplace, plugins can register `SessionStart` / `Stop` hooks, and `codex app-server` exposes rate-limit notifications locally. The log scan stays for now because it needs nothing installed on the user's side, but an event-driven path exists and is worth evaluating; see the reference table in the README.
- **Read priority** in `usage_client.py`: the newest usable data from `agentdeck-status.json` → `usag-status.json` (v0.1.x legacy) → `tt-status.json` (compat fallback for users migrating from the third-party tool `stormzhang/token-tracker`) or Claude Code's `~/.claude.json` `cachedUsageUtilization` fallback; **no `token-tracker` module or source exists in this repository**.

### Package layout

Root modules were grouped in v0.32.0: data loaders into `providers/`, the AI
Council into `council/`, pure state projections into `state/`. Imports read
`from providers import codex_loader`, so the module names are unchanged and still
greppable.

**Five files must stay at the root and stay stdlib-only**: `usage_statusline.py`,
`usage_statusline_forwarder.py`, `usage_session_resume.py`, `usage_terse_mode.py`
and `usage_terse_reminder.py`. They are copied into `~/.claude/` and executed by
whatever `python3` the user's Claude Code finds. Moving them into a package
breaks every installed hook, and nothing in the test suite would notice.

### Module map

| Module | Role |
|---|---|
| `main.py` | argparse + entry point; dispatches to `wintray.run_app`, `run_tui`, or `setup_hook.setup/unsetup`. |
| `usage_client.py` | Reads the Claude Code status JSON, builds a `UsageSnapshot`. Async interface preserved for the polling loop even though reads are sync. |
| `codex_paths.py` | `codex_home()` — the single source of truth for Codex's data directory (`CODEX_HOME`, else `~/.codex`). Every Codex path in the app derives from it. |
| `providers/codex_loader.py` | Parses Codex JSONL session logs for both rate-limits and per-message token usage. Also reads `state_5.sqlite` (read-only) for thread→model mapping. Its `logs_2.sqlite` query for `target = 'codex_otel.trace_safe'` is a **legacy fallback**: measured on the maintainer's machine 2026-08-10, that target accounts for 47 of 35,250 rows, all inside one 52-minute window on 2026-08-05, while the table itself is still being written to. Current Codex CLI does not produce them; the query stays for anyone still holding that history. |
| `providers/history_loader.py` | Parses Claude Code's per-project JSONL logs under `~/.claude/projects/` for token totals and cost. |
| `pricing.py` | Cost estimation. Downloads LiteLLM's `model_prices_and_context_window.json` once, caches to `~/.agentdeck/pricing_cache.json` (TTL 7 days; 10-min TTL on fallback so offline-then-online recovers; `~/.claude/pricing_cache.json` is a legacy read-only fallback). |
| `service_status.py` | Reads Claude and Codex **public service-status pages** (`status.claude.com/api/v2/summary.json`, `status.openai.com/api/v2/summary.json`) so the panel can flag outages; caches to `~/.agentdeck/anthropic_status_cache.json` and `~/.agentdeck/openai_status_cache.json` (TTL 5 min, 60s backoff after a failure), mirroring `pricing.py`'s fetch/cache shape. Inspects **only** Claude's `Claude Code` and `Claude API (api.anthropic.com)`, plus Codex's `Codex API` — never either page's overall `indicator` or OpenAI shared components, which can reflect unrelated incidents and would false-alarm. A status page is **not a usage API**; this does not violate the no-LLM-usage-API invariant. |
| `usage_rate.py` | Burn-rate classifier (Idle/Normal/Active/Heavy) — drives sprite animation speed in TUI. Burn rate deliberately excludes `cache_read` (see `UsageEntry.active_tokens`): cache reads are near-free re-sends of the whole context and would pin every heavy user at Heavy. |
| `panels/registry.py` | Which panels exist, which are themes, and the placeholder height each opens at. `available_panels()` is the theme list; `renderable_panels()` adds the talent market, which the same window renders but which is reached from the tray menu. |
| `assets/panels/panel_core.js` | The behaviour every panel shares — state application, i18n, the menu, project rows. Injected into each panel at `{{CORE_SCRIPT}}` by `panels/payload.py`. A theme is its CSS and markup plus a few `window.PanelHooks`; nine near-identical copies of this logic is what the fork carried before v0.40.0. |
| `win_modal.py` | Native dialogs: one at a time, owned by the panel so it sits above an always-on-top window. |
| `win_tray_menu.py` | The tray icon's right-click menu. |
| `wintray.py` | pystray tray icon + pywebview (WebView2) panels — the primary UI. Win32 work areas are in physical pixels while pywebview's API is logical; convert with `_monitor_dpi_scale()` / `_to_logical_rect()` or the panel lands off-screen on scaled displays. |
| `burn_rate.py` | Burn-rate prediction core used by `wintray.py`. |
| `state/menubar_state.py` | Pure history/state projections consumed by `wintray.py`. The `menubar_` prefix is historical — these modules are platform-neutral and load-bearing; don't delete them by name. |
| `council/discussion_window_win.py` | pywebview host for the AI Council window, a second window on wintray's GUI loop. Neutral parsing/assets live in `council/discussion_assets.py`; session state lives in `council/discussion_session.py`. |
| `tui.py`, `tui_sprite.py` | `rich`-based terminal renderer. |
| `usage_cli.py` | Standalone terminal analytics CLI (`uv run --no-sync python usage_cli.py report`) — drives the `adapters/analyzer/ui` report subsystem without the tray UI. |
| `doctor.py` | Renders the `uv run --no-sync python main.py --doctor` environment/hook-state diagnostic report. |
| `usage_lang.py` | Detects `AGENTDECK_LANG` / system locale. |
| `setup_hook.py` | Idempotent install/uninstall of the Claude Code statusLine hook, including migration of v0.1.x `usag-*` artifacts. Backs up any pre-existing `statusLine` under `settings["usage"]["previousStatusLine"]`. Also owns the shared low-level settings/TOML editing helpers that `session_hooks.py` builds on. |
| `session_hooks.py` | Install/enable/disable/self-heal for the session companion hooks (session resume, terse mode, terse reminder, Codex terse) — split out of `setup_hook.py`. Depends one-way on `setup_hook.py`; never the reverse. |
| `usage_statusline.py` | The hook itself. **Stdlib-only** so it runs under whatever `python3` the user's Claude Code finds, not this project's venv. The `UP017` ruff exemption is a leftover of the old macOS 3.9 floor and can be revisited. |
| `usage_statusline_forwarder.py` | Multi-hook fan-out. **Stdlib-only** so it runs under whatever `python3` the user's Claude Code finds, not this project's venv. The `UP017` ruff exemption is a leftover of the old macOS 3.9 floor and can be revisited. |
| `usage_statusline_agy.py` | Antigravity CLI status line. **Stdlib-only**, same rule as the other hooks: Antigravity runs it with whatever interpreter `setup_hook._find_system_python()` resolved at install time. Upstream hardcodes `/usr/bin/python3`; on Windows that would install a command that can never run. |
| `usage_session_resume.py` | SessionStart hook script — injects "where you left off" context into a new Claude Code session. **Stdlib-only** so it runs under whatever `python3` the user's Claude Code finds, not this project's venv. The `UP017` ruff exemption is a leftover of the old macOS 3.9 floor and can be revisited. |
| `docs/SIGNING.zh-TW.md` | How to get the Windows executable code-signed through SignPath. Steps 1–3 need the maintainer personally (the OSS application is reviewed by a human); 4–5 are repo changes. |
| `update_checker.py` | GitHub Releases update check added in v0.11.0. |
| `adapters/`, `analyzer/`, `ui/` | HTML report subsystem. |

### Naming invariant

Everything user-facing and newly written on disk uses `agentdeck` / `AGENTDECK_*`: the executable, hook filename, status filename, settings key, and `~/.agentdeck/` cache directory. Internal Python module names such as `usage_client.py` remain historical and deliberately unchanged. The `usage-*` and `usag-*` on-disk forms are migration-only read fallbacks; never write new data under them.

### i18n rule

All user-visible strings in panels and UI **must** be looked up from `i18n.json` via the `_t()` helper (or the JS `t()` function in HTML panels). Never hardcode any language's text directly in Python, HTML, or TUI code. When adding a new panel or new UI strings, add the key to **both** language sections in `i18n.json` (`zh-TW`, `en`) before shipping; `tests/test_i18n_key_parity.py` fails the build otherwise.

**This fork ships two UI languages, not upstream's five.** `usage_lang._normalize_lang()` resolves every Chinese locale (Simplified included) to `zh-TW` and everything else to `en`, so a `zh-CN` / `ja` / `ko` section in `i18n.json` would be dead weight no locale can reach. The same two-language contract is duplicated in the stdlib-only hook scripts, which cannot import `usage_lang` — `usage_statusline.py`, `usage_session_resume.py`, `usage_terse_mode.py`, `usage_terse_reminder.py` each carry their own copy, and `session_hooks.py` lists the shipped set in `RESUME_LANGS` / `TERSE_LANGS`. Change one, change all of them.

### Release / changelog

- This project is **bilingual (Traditional Chinese + English)**, and every doc must be updated in both languages together. **Reader-facing document conventions in this fork:**
  - **README and ROADMAP**: Traditional Chinese is the default (`README.md`, `ROADMAP.md`); English lives at `*.en.md`.
  - **CONTRIBUTING and SECURITY**: Traditional Chinese is the default (`CONTRIBUTING.md`, `SECURITY.md`); English lives at `*.en.md`. GitHub links the suffix-less files from its own community and security tabs, so the maintainer's language is the useful default there. The upstream `README.zh-CN.md` / `README.ja.md` / `README.ko.md` variants have been **removed** — do not reintroduce them. The app UI was reduced to the same two languages; see the i18n rule above.
  - **CHANGELOG**: Traditional Chinese is the default (`CHANGELOG.md`); English lives at `CHANGELOG.en.md`. The tray menu's Changelog item opens it, so the maintainer's language is the useful default here too.
  - **`docs/DEVELOPMENT`** is the only doc that keeps the upstream convention — suffix-less `.md` is **English**, Traditional Chinese is `.zh-TW.md`. It is written for contributors rather than users.
  - `scripts/check_doc_parity.py` gates all of the above in CI by comparing `##` heading counts; its `DOC_PAIRS` tuple reflects the inverted README and ROADMAP pairs.
- Version is bumped in `pyproject.toml`; CI builds `agentdeck-windows.zip` and attaches it on `v*` tags (`.github/workflows/release.yml`).

### Versioning — Semantic Versioning 2.0.0 (required)

Every version this fork publishes **must** follow [Semantic Versioning 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH`, tagged `vX.Y.Z`. Never invent date stamps, build numbers, or arbitrary suffixes.

The project is currently in the `0.y.z` series, where SemVer designates the public API as unstable. Until a `1.0.0` is declared deliberately, apply the pre-1.0 rules:

| Change | Bump | Examples in this project |
|---|---|---|
| Breaking — users must act, or behavior they relied on disappears | **MINOR** (`0.29.x` → `0.30.0`) | Removing UI languages; changing a hook's on-disk filename or settings key; dropping a `usage-*.json` read path; renaming a CLI flag |
| New capability, backward compatible | **MINOR** | A new panel theme, a new CLI subcommand, a new quota source |
| Bug fix or internal change, no interface movement | **PATCH** (`0.29.7` → `0.29.8`) | The redaction length floor; a Windows path fix; a typo in a translation |

Post-1.0 the first row moves to MAJOR. Nothing else changes.

Rules that hold regardless:

- **`pyproject.toml`'s `version` is the single source of truth.** A `vX.Y.Z` tag must point at a commit whose `pyproject.toml` says exactly `X.Y.Z` — a tag whose code doesn't match its number is worse than no tag.
- Accumulate changes under `## [Unreleased]` in **both** `CHANGELOG.en.md` and `CHANGELOG.md`; at release time rename that heading to `## [X.Y.Z] - YYYY-MM-DD` in both. `scripts/check_doc_parity.py` compares the newest version heading across the two files and fails CI if they disagree.
- One version number per release, applied everywhere at once: `pyproject.toml`, both changelogs, the tag.
