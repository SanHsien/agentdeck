# agentdeck Product Roadmap

[繁體中文](ROADMAP.md) · English

Updated: 2026-07-31

Planning baseline: `v0.31.2`

This roadmap describes the recommended product direction, milestone order, and exit criteria. Version numbers express dependency order, not fixed delivery dates. [`REVIEW_Claude.md`](REVIEW_Claude.md) remains the source of truth for current defects, while completed history belongs in [`CHANGELOG.en.md`](CHANGELOG.en.md).

## Product Judgment

The best direction for agentdeck is not to become "another token chart," nor to compete on provider count or theme count. It should become:

> **The local-first, explainable, actionable cockpit for AI coding work on Windows.**

The user's actual job has three steps:

1. **See**: know remaining quota, data age, and service health.
2. **Understand**: know where each number came from, why data is missing, and which link failed.
3. **Act**: repair a hook, adjust work cadence, generate a report, or start an AI Council without leaving the current workflow.

The twelve-month ideal:

```text
Today: broad capability with remaining release and UI edge cases
  │
  ├─ v0.31.x close known trust gaps first
  ├─ v0.32   explain every source's health and repair path
  ├─ v0.33   expose status and diagnostics to PowerShell and local tools
  ├─ v0.34   turn AI Council runs into reusable work products
  └─ v0.35   define maintainable source and release contracts
       │
       ▼
v1.0: users can trust the numbers, trust updates, and recover when something breaks
```

## Market Signals and Differentiation

Adjacent projects have already validated several needs:

| Project | Validated need | What agentdeck should learn |
|---|---|---|
| [CodexBar](https://github.com/steipete/codexbar) | Demand exists for multi-provider, live quota, and local cost views | Learn from its source contracts and status representation without chasing the same provider breadth |
| [ccusage](https://github.com/ccusage/ccusage) | Demand exists for CLI reports, time blocks, and cross-tool accounting | Make agentdeck's core state reliably available to scripts |
| [ccboard](https://github.com/florianbruniaux/ccboard) | Users want to move from quota into sessions, configuration, and diagnostics | Strengthen explanations and repair flows without cloning a large management console |
| [Usage Monitor for Claude](https://github.com/jens-duttke/usage-monitor-for-claude) | A portable, zero-config Windows executable with explicit stale state is attractive | Make first launch, missing data, and update failure more direct |

agentdeck should preserve four differentiators:

- **Windows-first**: the tray, WebView2, DPI, taskbar position, and Windows releases are first-class concerns.
- **Local-first**: Claude Code and Codex quota comes from local files, without Anthropic or OpenAI usage API calls.
- **Monitoring to action**: the product includes diagnostics, reports, workflow modes, personas, and AI Council, not just numbers.
- **Explainable trust**: every number can identify its source, update time, stale state, and next repair step.

## Existing Foundations, Do Not Rebuild

Future issues should reuse these working capabilities instead of creating parallel versions:

- Claude, Codex, and Antigravity quota sources all have stale hints and reset countdowns; Claude and Codex also have burn rate, forecasts, and quota system notifications.
- `--doctor`, the Rich TUI, HTML, CSV, and PNG reports, and `usage_cli.py report`.
- AI Council stop, between-round guidance, anonymous labels, consensus tallying, token estimates, and automatic JSON and Markdown archives.
- Local persona installation, backup, drift detection, and restore in the AI Talent Market.
- The six quality gates, CodeQL, ClusterFuzzLite, PyInstaller resource tests, release ZIP, and SHA-256.

Roadmap additions should close user loops around these capabilities, such as making existing discussion archives searchable, rather than inventing a second archive format.

## Priority Order

Future work should be ranked in this order:

1. **Release and data correctness**
2. **Visible, recoverable failures**
3. **Stable, testable, scriptable interfaces**
4. **AI Council work products and recovery**
5. **New providers, more themes, and other expansion**

A feature looking new does not make it more important than "the built executable reports the right version." The latter has little screenshot value, but it is the foundation of product trust.

## v0.31.x: Close the Trust Gaps

Goal: stop carrying known, reproducible product and release defects.

### Work

- Fix P6 in [`REVIEW_Claude.md`](REVIEW_Claude.md): make `scripts/build_windows.ps1` remove stale `agentdeck.egg-info` and `usage.egg-info` before building, then verify `agentdeck.exe --doctor` matches `pyproject.toml`. Add executable and tag version comparison to the existing clean Windows release workflow while preserving its SHA-256 flow.
- Fix P5: at 900×640, the AI Council participant area must fully show at least one card. The list may scroll, but model and persona controls must not be vertically clipped.
- Establish a real WebView2 matrix at 100%, 150%, and 225% DPI for 900×640 and 1280×800.
- Record Windows build, WebView2 Runtime version, DPI, logical and physical resolution, result checklist, and issue screenshots in versioned `docs/release-evidence/`. `REVIEW_Claude.md` links only the evidence for current open items.
- Remove documentation drift such as released content left under `Unreleased`, obsolete review filenames, and inaccurate feature comparisons.

### Exit Criteria

- Executables built locally and on a GitHub runner report the correct version.
- The `vX.Y.Z` tag, `pyproject.toml`, executable `--doctor`, and release asset all agree.
- The AI Council has no critical control clipping or unexpected horizontal scrollbar in the real-hardware matrix.
- All six gates pass, and P5 and P6 are removed from `REVIEW_Claude.md`.

## v0.32.0: Trustworthy Sources and Repair Flows

Goal: explain every `--`, stale value, and query failure so the user never has to guess.

### Work

- Create a shared `ProviderHealth` state model covering at least `ready`, `stale`, `missing`, `misconfigured`, `unavailable`, and `error`.
- Make Claude, Codex, and Antigravity cards share health states and repair guidance with `--doctor`, so UI and CLI cannot tell different stories.
- Extend the existing first-run and stale checks to consistently distinguish "tool never used," "hook missing," "file too old," "CLI not signed in," and "service temporarily failed."
- Evaluate Codex plugin and `app-server` event-driven inputs and record a decision. Keep JSONL scanning as the zero-install fallback rather than trading reliability for novelty.
- Establish performance baselines for cold start, 90-day history scanning, file-event refresh latency, and peak memory.

### Exit Criteria

- Every empty or stale state includes a reason, last update time, and next step.
- Offline mode, malformed JSONL, permission failures, no data, and old hooks all have tests.
- UI and `--doctor` produce the same classification for the same state.
- The Codex event-driven option has an adopt or reject decision backed by measurements.

Delivery order: health model → three provider projections → shared UI and doctor output → first-run repair → Codex event-source evaluation → benchmarks.

## v0.33.0: A Scriptable Local Cockpit

Goal: let PowerShell, scheduled jobs, and other local tools reuse agentdeck's trusted state.

### Work

- Add `agentdeck.exe --status --json` for release users, with `main.py --status --json` from source. Route it through `main.py` into a neutral leaf module and expose a versioned schema for provider quota, source health, update time, and service status.
- Add `main.py --doctor --json` for issue reports and automated diagnostics. Redact usernames, project paths, and tokens by default.
- Label provenance and estimation in reports and JSON, clearly separating official quota, local-log inference, and price-table estimates.
- Add read-only PowerShell examples, such as showing a local notification near a quota threshold. Do not switch accounts or execute model requests for the user.
- Define schema compatibility tests and a versioning policy.

### Exit Criteria

- Scripts never need to parse human-readable output.
- JSON output does not expose absolute paths, credentials, prompts, or conversation content by default.
- Breaking schema changes follow SemVer, with at least one PowerShell smoke test.
- Headless environments can complete status checks and problem reports.

Delivery order: neutral status projection → `--status --json` → `--doctor --json` → redaction and schema tests → PowerShell smoke.

## v0.34.0: Make AI Council a Reusable Work Product

Goal: discussions should be searchable, reusable, and actionable rather than one-off runs.

### Work

- Add history indexing, search, and "open in File Explorer" for existing `~/.agentdeck/discussions/*.json` and `*.md` archives.
- Preserve the existing behavior where one participant can fail while others continue, and guarantee persistence of completed results after failure or cancellation. Make interruption reasons understandable on reopen.
- Keep rounds as a hard limit. Pass native max-output arguments when a provider supports them, and check token budget at each turn boundary. State before launch that one turn may exceed the estimate.
- Inventory existing tests for missing CLIs, expired sign-in, partial failure, malformed output, and cancellation, then fill the gaps in the error and recovery matrix.
- Keep attachments read-only and clearly show allowed folders and images. Do not expand into arbitrary file writes or automatic command execution.

### Exit Criteria

- Historical discussions are searchable by date, topic, participant, and outcome.
- One participant failing never erases completed work from the others.
- Round hard limits and token-budget semantics are visible before start. Exceeding the budget at a turn boundary stops and archives safely.
- Archive migrations are tested so old discussions remain readable.

Delivery order: failure and cancellation persistence → history index and search → reopen view → budget boundaries → migration and recovery matrix.

### Follow-up Candidates (Not Required for v0.34.0)

- Reusable discussion templates for code review, architecture tradeoffs, incident retrospectives, and release decisions.
- Advanced summary structure for decisions, dissent, unresolved questions, and next actions, with links back to the originating round.

Only schedule these into a later MINOR after the history index and reopen flow demonstrate real use, so v0.34 does not carry too many new interactions at once.

## v0.35.0: Maintainable Expansion and Releases

Goal: add capabilities without continuously growing `wintray.py`, packaging risk, or source ambiguity.

### Work

- Extract a minimal `ProviderAdapter` contract only when duplication across the three existing sources is measurable. Do not build an abstract plugin framework first.
- Require new providers to pass an eligibility gate: Windows availability, lawful source, visible failures, offline degradation, and tests that never touch real credentials.
- Produce a dependency inventory or SBOM so the actual PyInstaller bundle can be audited.
- Consolidate the existing SHA-256 check with the executable and tag checks added in v0.31.x into one release evidence manifest rather than creating a parallel release path.
- Add preference, hook, and archive migration tests covering the latest two MINOR versions.
- Make the UI hardware matrix and release smoke a fixed checklist for every release.

### Exit Criteria

- A new provider does not require adding business logic to `wintray.py`.
- Release assets, checksum, SBOM, and the version evidence manifest can be recreated by one workflow.
- Upgrade and rollback cover at least the latest two MINOR versions.

## v1.0.0 Criteria

`1.0.0` is determined by a stable trust contract, not feature count.

- `REVIEW_Claude.md` contains no unresolved, reproducible product defects; environment limits have explicit detection and handling.
- Core flows pass real-hardware smoke on Windows 10, Windows 11, and 100%, 150%, and 225% DPI.
- Tags, source version, executable version, and release assets agree reproducibly.
- Claude, Codex, and Antigravity have clear UX for missing data, stale data, offline mode, and expired sign-in.
- `status --json` and `doctor --json` schemas are declared v1 and covered by compatibility tests.
- Settings, hooks, caches, and discussion archives can upgrade safely from the latest two MINOR versions.
- Every user-triggered action reports success or failure, with no known silent failures.
- Privacy boundaries, actual network scope, AGPL release contents, and the security-reporting flow all have automated or manual evidence.

## Measurement

This project does not add telemetry. Evidence for the following targets comes from tests, benchmarks, release workflows, and manual smoke checks:

| Metric | Target |
|---|---|
| First launch to valid data or a clear repair instruction | Within 5 minutes |
| Silent failures for user-triggered actions | 0 |
| Tag, pyproject, executable, and asset version agreement | 100% |
| Critical clipping at 900×640 on 100%, 150%, and 225% DPI | 0 |
| App crashes from malformed or incomplete local data | 0 known cases |
| Diagnostics required for an issue report | One `--doctor` command |

Performance should be baselined in v0.32 before numbers become gates. Do not invent an attractive millisecond target without a reproducible measurement method.

## Primary Risks, Dependencies, and Defenses

Windows 10, multiple DPI settings, and WebView2 visual acceptance require real maintainer hardware and cannot be replaced by a GitHub runner. Automated evidence belongs in CI and release artifacts, manual checklists and screenshots belong in versioned `docs/release-evidence/`, `REVIEW_Claude.md` links only evidence for current open items, and performance baselines belong in repository benchmark fixtures or reports.

| Risk or dependency | Possible outcome | Defense | Verification evidence |
|---|---|---|---|
| Claude or Codex changes a local file format | Quota disappears or parses incorrectly | Fixtures, schema detection, old-format fallbacks, and explicit health states | Parser tests and fuzz results |
| Windows 10 or 11, DPI, and WebView2 combinations differ | Controls clip or windows land off-screen | Pure-logic tests plus a three-DPI hardware matrix | `docs/release-evidence/` checklist and screenshots |
| Stale metadata or caches contaminate a build | The tag is right but the executable version is wrong | Pre-build cleanup, clean runners, and post-build executable version smoke | Release evidence manifest |
| Providers report usage only after a turn | Token budget can stop one turn late | Round hard limit, native max-output, turn-boundary checks, and explicit wording | Discussion budget tests |
| CLI sign-in and arguments keep changing | One AI Council participant fails | Capability detection, adapter isolation, per-turn failure, and archiving | Adapter and partial-failure tests |
| Discussion archive schema evolves | New versions cannot read old discussions | Schema version and fixtures for the latest two MINOR migrations | Archive migration tests |
| Diagnostics contain private paths or conversations | Data leaks into an issue report | Default redaction, sensitive-string tests, and explicit opt-in for more detail | Redaction tests |
| Feature growth blurs product focus | Maintenance rises while core reliability stalls | Fixed priorities, provider eligibility gates, and explicit non-goals | Roadmap and issue review |

## Explicit Non-Goals

- Do not restore macOS support; upstream owns macOS.
- Do not call Anthropic or OpenAI usage APIs for Claude Code or Codex quota.
- Do not build cloud accounts, a team console, or upload conversation content.
- Do not implement automatic multi-account switching, credential proxying, or model request routing.
- Do not optimize for the largest provider list; providers without reliable Windows sources do not qualify.
- Do not publish a wheel or PyPI package; the product remains a Windows PyInstaller bundle.
- Do not give AI Council arbitrary file-write or command-execution permissions.

## Execution Rules

Every milestone follows the same completion flow:

1. Write the verifiable user outcome as an issue.
2. Record tradeoff decisions in `docs/DECISIONS.md`.
3. Cover pure logic with automated tests, and WebView2, tray, and dialog behavior with real Windows smoke.
4. Pass all six gates with `pwsh tools/dev_check.ps1`.
5. Update English and Traditional Chinese docs and changelogs together.
6. After push, verify GitHub CI, CodeQL, and any required release workflow.
7. Mark roadmap work complete only when exit criteria have evidence.

## Next Three Actions

1. **P6 release-version guard**: clean egg-info in `build_windows.ps1` and smoke the executable version. This is the most direct supply-chain trust gap.
2. **P5 AI Council vertical clipping**: fix the container height or scrolling strategy, then verify 900×640 at three real DPI settings.
3. **ProviderHealth design and first implementation**: make Claude, Codex, and Antigravity speak the same language for ready, stale, unconfigured, and failed states before considering more providers.
