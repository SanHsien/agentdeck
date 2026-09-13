# Fork 維護指南

本倉庫 fork 自 [`aqua5230/usage`](https://github.com/aqua5230/usage)，但**獨立維護、不回貢上游**。這份文件講只有 fork 才需要知道的事：跟上游的關係、已經分叉了哪些地方、要撿上游更新時怎麼做。

專案本身怎麼運作看 [`CLAUDE.md`](../CLAUDE.md)；Windows 開發環境看 [`DEVELOPMENT.zh-TW.md`](DEVELOPMENT.zh-TW.md)；agent 工作規則看 [`AGENTS.md`](../AGENTS.md)。

## 定位

- **不打算送 PR 回上游**，所以不需要為了「保持可 PR 的乾淨度」而限制自己。
- `main` 是主線，可以自由發展、允許與上游分叉。
- 任何檔案都可以改，包含上游原有的 `.py`、`CLAUDE.md`、`README*`、`.github/`。
- 上游的更新是**選擇性**撿的，不是義務。

唯一持續有效的約束是授權：上游是 AGPL-3.0-only，本 fork 的所有修改同樣以 AGPL-3.0-only 釋出，`LICENSE` 與上游 attribution 不可移除。詳見 [`NOTICE.md`](../NOTICE.md)。

## Remote 配置

```
origin    https://github.com/SanHsien/agentdeck.git      (本 repo，可推)
upstream  https://github.com/aqua5230/usage.git      (上游，唯讀)
```

`upstream` 已設定好。若在新機器 clone，補上：

```powershell
git remote add upstream https://github.com/aqua5230/usage.git
```

**永遠不要 push 到 `upstream`**（`.claude/settings.json` 已 deny 這條指令）。

## 已與上游分叉之處

改到這些地方時，不要「照上游的樣子改回去」；撿上游更新撞到衝突時，以本欄為準：

| 項目 | 上游 | 本 fork |
|---|---|---|
| README 預設語言 | 英文（`README.md`） | **繁體中文**（`README.md`），英文在 `README.en.md` |
| 產品路線圖 | 無 | **繁體中文**（`ROADMAP.md`），英文在 `ROADMAP.en.md` |
| README 其他語言 | 另有 `README.zh-CN.md` / `README.ja.md` / `README.ko.md` | **已刪除**，不要重新加回 |
| `scripts/check_doc_parity.py` | `DOC_PAIRS` 比對 `README.md` ↔ `README.zh-TW.md` | README 改為 `README.en.md` ↔ `README.md`，另納入 ROADMAP、CONTRIBUTING、SECURITY、CHANGELOG、DEVELOPMENT |
| 產品名稱 | `usage` | **`agentdeck`**（見 `DECISIONS.md` D-09）；內部模組檔名仍是 `usage_*` |
| CONTRIBUTING / SECURITY | 英文為預設 `.md` | **繁體中文為預設 `.md`**，英文在 `*.en.md` |
| CHANGELOG / docs/DEVELOPMENT | 英文為預設 `.md`，中文為 `.zh-TW.md` | **維持上游慣例不變** |

新增檔案（上游沒有，不會有衝突）：`AGENTS.md`、`SKILL.md`、`NOTICE.md`、`ROADMAP.md`、`ROADMAP.en.md`、`REVIEW_Claude.md`、`REVIEW_Codex.md`、`persona_store.py`、`personas/`、`discussion_window_win.py`、`discussion_assets.py`、`docs/FORK.zh-TW.md`、`docs/DECISIONS.md`、`docs/DEVELOPMENT.zh-TW.md`、`docs/PORTING.zh-TW.md`、`docs/UPSTREAM.md`、`tools/`、`reference/`、`.pre-commit-config.yaml`、`.claude/settings.json`。

分叉背後的取捨記在 [`DECISIONS.md`](DECISIONS.md)，包含 D-01 獨立維護、D-11 雙語文件契約、D-12 uv virtual root，以及 D-13 先建立產品信任合約再擴張。

## Tag 政策

本 repo **只保留最新一個 tag**，上游那 160 多個歷史 tag 已全部刪除——需要舊版本時從上游查即可，沒必要在這裡重複一份。

`remote.upstream.tagOpt` 已設為 `--no-tags`，因為 `git fetch upstream` 預設會把上游所有可達的 tag 一起抓回本機，清完又長回來。新機器 clone 後要補上：

```powershell
git config remote.upstream.tagOpt --no-tags
```

發版時 tag 用 `vX.Y.Z`，且**必須指向 `pyproject.toml` 版號相符的 commit**（規則見 [`../CLAUDE.md`](../CLAUDE.md) 的 Versioning 段與 [`DECISIONS.md`](DECISIONS.md) D-05）。

## 撿上游更新

不是例行工作，想要某個上游修復時再做：

```powershell
git fetch upstream
git log --oneline HEAD..upstream/main     # 先看上游有什麼
```

**判斷某個分支或 commit 該不該吃，要比對「當前檔案內容」，不是看 commit 圖。** `git log main..branch` 顯示領先幾個 commit，只說明那些 commit 不在歷史中，不代表改動沒進去——上游可能 squash 合併或重新實作過。本 fork 就曾把兩個實際上已過時的分支誤判為「未合併的修復」（見 [`DECISIONS.md`](DECISIONS.md) D-06）。

決定要全部吃進來：

```powershell
git merge upstream/main
```

只想要某幾個 commit：

```powershell
git cherry-pick <sha>
```

**衝突多半會落在上表列的分叉點上**（尤其 README 與 `check_doc_parity.py`）。解衝突的原則：功能性的改動吃上游，語言／文件結構的決定保留本 fork 的。

合併完**一定要重跑閘門**：

```powershell
pwsh tools/dev_check.ps1
```

上游若動了 `uv.lock`，先重新同步相依：

```powershell
uv sync --frozen --group dev --extra windows
```

## 改動須知

- **改 README 要兩邊一起改**：`README.md`（繁中）與 `README.en.md`（英文）的 `##` 章節數必須一致，CI 的 `scripts/check_doc_parity.py` 會擋下不一致。內容也要互相對應翻譯，不要只補一邊。
- **改版號時不要跑 `uv lock`**：手動改 `uv.lock` 裡 `agentdeck` 那一行的 `version` 即可，零解析風險。`.claude/settings.json` 已 deny `uv lock`。
- **不要自己 bump 版本或打 `v*` tag**，除非真的要從本 fork 發版——那會觸發 `.github/workflows/release.yml`。
- **macOS 支援已於 2026-07-29 移除**（見 `DECISIONS.md`）。上游那些 macOS 檔案的唯讀副本留在 `reference/upstream-macos/`，移植功能時對照用。
