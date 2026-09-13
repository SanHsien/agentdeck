# 貢獻指南

繁體中文 · [English](CONTRIBUTING.en.md)

歡迎開 issue / PR。這份文件只描述硬性要求，不規定流程。

本 fork 由 maintainer（[@SanHsien](https://github.com/SanHsien)）獨立維護，採仁慈獨裁模式：所有 PR 由 maintainer 審查後決定是否合併，歡迎討論，最終決定權在 maintainer。

## 開 Issue

- **Bug report**：用 `.github/ISSUE_TEMPLATE/bug_report.md` 模板。請附 Windows 版本、Python 版本、`git rev-parse --short HEAD`、跑哪個模式（系統匣 / TUI / mock / doctor）。
- **Feature request**：用 `.github/ISSUE_TEMPLATE/feature_request.md` 模板。

## 開 PR 前的必跑檢查

```powershell
uv sync --frozen --group dev --extra windows
pwsh tools/dev_check.ps1
```

完整閘門要綠才能 merge；內容包含 lock freshness、ruff、mypy、雙語文件、AI 更新頁與 pytest，CI 會執行同一組檢查（`.github/workflows/check.yml`）。

## 改 code 的方針

- **改 prod 模組請順手補測試**：`tests/` 底下挑風格最接近的檔案模仿。新增測試禁止碰 `~/.claude/` 跟 `~/.codex/` 真實檔案，請用 `monkeypatch` 改路徑常數。
- **公開名稱使用 `agentdeck`**：binary、設定 key、落地檔名與環境變數使用 `agentdeck` / `AGENTDECK_*`。`usage_*.py` 等內部模組名稱是刻意保留的歷史名稱。
- **Windows UI 邏輯不要塞回 `wintray.py`**：新判斷放在可獨立測試的 leaf module，`wintray.py` 只保留薄 UI 外殼。

## CHANGELOG 與發版

- 改完一件事就把它寫進 `CHANGELOG.en.md`（英文，預設）的 `## Unreleased` 段，**同時更新 `CHANGELOG.md`** 對應段（這個專案的 README / CHANGELOG / release notes 全部雙語）。
- 發版由 maintainer 處理（`pyproject.toml` 版本 bump + `## Unreleased` → `## X.Y.Z — YYYY-MM-DD` + commit `Release vX.Y.Z` + tag）。

## Commit message 風格

跟現有 `git log` 一致：祈使句 + 簡短主旨，必要時加 body 解釋 why（不是 what，what 看 diff 就好）。範例：

```
Fix AttributeError: drop stale tracker.sample() call

072a088 removed UsageRateTracker.sample() but missed the lone caller in
wintray.py:435...
```
