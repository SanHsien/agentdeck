# AGENTS.md

本檔是 **SanHsien/agentdeck** 的 AI coding agent 主要維護規則。技術細節見 [`CLAUDE.md`](CLAUDE.md) 與 [`docs/DEVELOPMENT.zh-TW.md`](docs/DEVELOPMENT.zh-TW.md)；移植與 fork 流程分別見 [`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md)、[`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。

## 專案定位

**agentdeck** 是 Windows-only 的 AI coding cockpit：以系統匣 / WebView2 為主要介面，集中 Claude Code、Codex、Antigravity 額度狀態，並提供 AI Council、persona 安裝、工作續接與本機報告。

本 repo 是 [`aqua5230/usage`](https://github.com/aqua5230/usage) 的 fork，依 **AGPL-3.0-only** 獨立維護。上游來源、修改聲明與 attribution 以 [`NOTICE.md`](NOTICE.md) 為準。

## 硬性邊界

- **Windows-only**：不要把 macOS menu bar、PyObjC、`.app` 或 macOS build 路徑重新接回正式產品。需要對照上游行為時讀 `reference/upstream-macos/`。
- **不呼叫 Anthropic / OpenAI usage API**：Claude Code 與 Codex 額度讀本機資料。Antigravity 使用其 CLI 的本機登入身分查 Google 官方 quota endpoint，這是既有產品契約，不等同於 Claude / OpenAI usage API。
- **不碰真實使用者資料做測試**：測試不可寫入實際 `~/.claude/`、`~/.codex/`、`~/.cursor/` 或 Windows 排程；使用 fixture / temp path / monkeypatch。
- **保留 AGPL 與 attribution**：不得移除 `LICENSE`、`NOTICE.md` 或上游著作權聲明。
- **不提交私密資料**：token、OAuth credential、session、真實對話、個人專案紀錄、本機 cache / vendor binary 不得進 Git。
- **不把 local-first 說成 fully offline**：Antigravity quota、公開服務狀態、價格表與 GitHub 更新檢查會連網；AI Council 啟動的 provider CLI 也依 provider 自身行為連網。

## 重要相容性不變式

### 安裝到使用者環境的 hook

以下檔案會被複製到使用者環境並由系統 Python 執行，必須留在根目錄且維持 stdlib-only：

- `usage_statusline.py`
- `usage_statusline_forwarder.py`
- `usage_session_resume.py`
- `usage_terse_mode.py`
- `usage_terse_reminder.py`

`usage_statusline_agy.py` 也必須維持 stdlib-only。改動 hook 安裝 / 解除流程前，先讀 `setup_hook.py`、`session_hooks.py` 與對應測試；不得用真實設定做驗證。

### 語言

正式 UI 只出貨：

- `zh-TW`
- `en`

所有使用者可見字串走 `i18n.json`。新增 key 必須兩語一起補；中文 locale（含簡體）目前統一映射到 `zh-TW`。若改 locale normalization，要同步檢查 stdlib-only hook 中的複本與 `session_hooks.py`。

### 產品名稱

新寫入的使用者資料與對外名稱使用 `agentdeck` / `AGENTDECK_*`。內部仍有 `usage_*` 歷史模組名與 migration fallback，除非有完整遷移方案，不要只為了品牌一致性大規模改名。

## 架構地圖

- `main.py`：CLI / tray / TUI 入口
- `wintray.py`、`win_tray_menu.py`、`win_modal.py`：Windows tray / WebView2 UI 外殼
- `panels/`、`assets/panels/`：面板註冊、payload 與共享前端核心
- `providers/`：Claude / Codex / Antigravity 等資料來源
- `state/`：純狀態投影
- `council/`：AI Council session、CLI bridge、Windows 視窗
- `persona_store.py`、`personas/`：跨工具 persona 定義與安裝
- `setup_hook.py`、`session_hooks.py`：Claude / Codex companion hook 設定
- `adapters/`、`analyzer/`、`ui/`、`usage_cli.py`：報告子系統
- `scripts/`、`tools/`：建置、文件 parity、size gate、upstream 檢查
- `tests/`：pytest 回歸測試

逐模組陷阱不要堆在本檔；需要時讀 [`CLAUDE.md`](CLAUDE.md) 或 [`docs/DEVELOPMENT.zh-TW.md`](docs/DEVELOPMENT.zh-TW.md)。

## 開發原則

- 一般變更直接推 `origin/main`，不開功能分支、不開維護 PR（主人 2026-08-22 指示）。只有在需要他人審查、或改動風險高到值得先讓 CI 在 PR 上跑一輪時，才退回 **branch → PR → CI → merge**。
- 修 bug 先做最小修補並補對應測試；不要因為看見歷史命名或長檔案就順手大重構。
- 新 UI 行為的邏輯優先放可測試的 leaf module；`wintray.py` 維持 UI orchestration，不繼續堆難測判斷。
- 影響設定檔、persona、hook、排程或 provider credential 的寫入流程要特別檢查 backup / rollback / idempotency。
- 純文件、維護規則或 metadata 整理**不需要機械式 bump version 或發 Release**。
- 真正的使用者可見 runtime / binary 變更，依 [`CONTRIBUTING.md`](CONTRIBUTING.md) 與 release workflow 的 SemVer 規則決定版號。
- 不為了「更完整」新增新的 governance workflow；現有 CI、CodeQL、ClusterFuzzLite、Scorecard、Release 與 upstream-check 已足夠。
- **合併任何 PR 前先讀 diff**（包含 Dependabot 開的）：`gh pr diff <編號>`。CI 綠燈證明的是「測試沒紅」，不是「改了什麼、該不該進 main」——lockfile 的連鎖升級、transitive major、跨出宣告範圍的變更，只有讀 diff 看得到。核准或合併訊息要寫出讀到什麼、為什麼可接受。

## 上游更新

上游仍活躍。收到「上游更新檢查」issue 時：

1. 逐筆判斷 commit 是否符合 Windows-only 產品方向。
2. 採用時更新程式與 `docs/UPSTREAM.md` 的 reviewed / merged 狀態。
3. 不採用時在 `docs/UPSTREAM.md` 留下 skipped 理由。
4. 只有當取捨具有長期架構 / 產品意義時才補 [`docs/DECISIONS.md`](docs/DECISIONS.md)，不要每個 skipped commit 都製造決策文件噪音。

macOS-only commit 通常不採用，但可以作為 Windows 移植的行為參考。是否移植以**產品價值與 Windows 可行性**判斷，不需要為追平上游而自動搬完所有功能。

## 文件分工

- `README.md` / `README.en.md`：產品入口、下載、核心能力、必要資料 / fork 邊界
- `ROADMAP.md` / `ROADMAP.en.md`：產品方向與未來工作
- `CHANGELOG.md` / `CHANGELOG.en.md`：正式版本的使用者可見變更
- `docs/DEVELOPMENT*`：架構、環境、驗證、打包
- `docs/PORTING.zh-TW.md`：Windows 移植方法
- `docs/UPSTREAM.md`：上游審視狀態
- `docs/DECISIONS.md`：耐久性的產品 / 架構決策
- `NOTICE.md`：fork attribution、AGPL 修改聲明、資料與第三方來源
- `SECURITY*`：漏洞回報與支援政策
- `REVIEW_Claude.md` / `REVIEW_Codex.md`：特定時間點的專案覆核，不是每個 bug 的強制流水帳

只更新**真正受本次變更影響**的文件。雙語公開文件若其中一邊有實質內容變更，另一邊要同步；CI 會檢查主要 `##` 章節數 parity。

## 驗證

Windows / PowerShell：

```powershell
uv sync --frozen --group dev --extra windows
pwsh tools/dev_check.ps1
```

`tools/dev_check.ps1` 應涵蓋與 CI 對齊的主要 gate。需要單獨定位時可跑：

```powershell
uv run --no-sync ruff check .
uv run --no-sync mypy .
uv run --no-sync python scripts/check_doc_parity.py
uv run --no-sync python scripts/check_file_size.py
uv run --no-sync pytest -q
```

涉及 Windows UI、DPI、tray、WebView2、Windows 排程、真實 provider CLI 或正式打包的變更，若自動測試不足，必須明列還需要的 Windows 實機 smoke；沒有實機證據時不要宣稱已完成該層驗收。

## 對外邊界：PR 只打本 fork

- **PR、push、release 一律指向 `SanHsien/agentdeck`。** 對上游 `aqua5230/usage` 開 PR、push 或發 release
  需要主人在當次對話明確同意回貢；「fork 一份」「建開發環境」「比照其他 repo」都不是同意。
- 根因是機制不是粗心：`gh` 在 fork clone 的**預設 repo 就是上游**（`gh repo set-default --view` 會回
  `aqua5230/usage`），裸跑 `gh pr create` 必然打上去。每個 clone 先跑一次
  `gh repo set-default SanHsien/agentdeck`。
- 開 PR 仍明寫 `gh pr create --repo SanHsien/agentdeck --base <分支> --head <分支>`，並**讀輸出的 URL**，
  owner 必須是 `SanHsien`。不是就立刻 `gh pr close` 留言道歉說明，再對 origin 重開。
- 2026-08-22 一天內兩個工作階段各誤開一個上游 PR（`lidge-jun/opencodex#2373`、
  `hamanpaul/paulsha-cortex#787`）。批次跑多個 repo 時最容易略過確認，而那正是兩次出事的場合。
