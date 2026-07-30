# AGENTS.md

給 AI agent（Codex、Claude Code、Gemini 等）在 **SanHsien/agentdeck** 工作時的指引。

專案本身的架構說明在 [`CLAUDE.md`](CLAUDE.md)。這份文件補 fork 專屬的規則與 Windows 開發環境差異。

## 本 fork 的目的：把 macOS 的功能搬到 Windows，不是接受落差

**這是維護者的核心意圖，優先於「維持現狀」的直覺。**

上游是 macOS 優先的專案，很多功能在 Windows 上是缺的、殘的、或退化的。本 fork 的目標**不是**記錄這些落差然後接受它，而是**逐一移植到 Windows 版本**。

因此，遇到「這個功能只有 macOS 有」或「Windows 上做不到」時：

- **不要**寫成「平台差異，符合預期」就結案。
- **要**判斷 Windows 上實際能不能做到，能做就排進待辦、動手移植。
- 真的做不到（缺少 Windows API、依賴 macOS 專屬二進位）才記為受阻，**並寫明卡在什麼具體技術限制**，不是含糊的「平台不同」。

**動手前先讀 [`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md)** —— 移植的盤點方法、可行性判斷、實作規矩與驗收標準都在裡面,含實際踩過的坑（盤點用的 grep 錯過三次、對話框按鈕配置讓 Escape 觸發了不可逆選項）。

已知落差清單與移植狀態見 [`REPO_REVIEW.md`](REPO_REVIEW.md) 的「Windows 平台落差移植待辦」。發現新落差就補進那份清單。

參考素材：[`reference/upstream-macos/`](reference/upstream-macos/) 放著已從本 repo 移除的上游 macOS 實作，**唯讀、不參與建置與檢查**，用途是移植功能時對照原本的行為。

## 收到「上游更新檢查」issue 時

上游仍在活躍開發。`.github/workflows/upstream-check.yml` 每週跑 `tools/check_upstream_updates.py`，發現上游有比 `docs/UPSTREAM.md` 的 `last_reviewed` 更新的 commit 時，會開／更新一個「上游更新檢查」issue。

處理流程（**適用所有 AI agent 與人**）：

1. 逐筆讀 commit 內容，判斷是否適用本 fork（Windows-only、中英雙語、已移除 macOS）。
2. **採用** → `git merge` 或 `git cherry-pick`，完成後同時推進 `docs/UPSTREAM.md` 的 `last_merged` 與 `last_reviewed`。
3. **不採用** → 只推進 `last_reviewed`，**並且**在 `docs/UPSTREAM.md` 的「Skipped」表補一列（commit／標題／審視日期／理由），在 [`docs/DECISIONS.md`](docs/DECISIONS.md) 記一句理由。

`last_reviewed` 只負責「這次不用再提醒」，Skipped 表才負責「不失憶」——**兩件事缺一不可**。只推進標記卻不記理由，日後想查「當初為什麼跳過」會查無所獲。

macOS 專屬的 commit 一律不採用，但仍要進 Skipped 表，理由寫「macOS-only，本 fork 已移除該平台」。

## 這是 fork，但獨立維護

- 上游：[`aqua5230/usage`](https://github.com/aqua5230/usage)（AGPL-3.0-only）。
- 本 repo：[`SanHsien/agentdeck`](https://github.com/SanHsien/agentdeck)，remote `origin`；上游掛在 remote `upstream`（唯讀）。
- **不回貢上游**。`main` 自由發展，允許與上游分叉；要不要撿上游的更新是選擇性的。
- 因此**沒有「不准改上游檔案」這條限制**——任何檔案都可以改，包含 `CLAUDE.md`、`README*`、`.py`、`.github/`。要撿上游更新時再處理衝突即可。詳見 [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。

**硬性邊界（不可違反）**：

- **不呼叫 Anthropic / OpenAI 的用量 API**。本專案所有數字都來自本機檔案（statusLine hook 寫的 JSON、Codex 的 `~/.codex/sessions/*.jsonl`）。這是專案的核心不變式，任何「順手接 API 拿更準的數字」的提案一律停下來先跟維護者確認。
- **測試禁止碰真實的 `~/.claude/` 與 `~/.codex/`**，用 `monkeypatch` 改路徑常數（照 `tests/` 現有寫法）。
- **不把私有內容推進公開 git 歷史**：`vendor/`（instate-cli 二進位）、`SESSION.md`、本機快取都已在 `.gitignore`，不要繞過。
- AGPL-3.0 的授權標頭、`LICENSE`、上游著作權聲明不得移除或改寫。散布衍生版本時仍須沿用 AGPL-3.0 並保留 attribution。

## 本 fork 已與上游分叉之處

改到這些地方時，不要「照上游的樣子改回去」：

| 項目 | 上游 | 本 fork |
|---|---|---|
| README 預設語言 | 英文（`README.md`） | **繁體中文**（`README.md`）；英文在 `README.en.md` |
| README 其他語言 | 另有 `zh-CN` / `ja` / `ko` 三版 | **已刪除**，不要重新加回 |
| `scripts/check_doc_parity.py` | `DOC_PAIRS` 比對 `README.md` ↔ `README.zh-TW.md` | 改為 `README.en.md` ↔ `README.md` |
| 其他文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT） | 英文為預設 `.md`，中文為 `.zh-TW.md` | **維持不變** |
| 產品名稱與落地檔名 | `usage` / `~/.usage/` / `usage-statusline.py` | **`agentdeck`** / `~/.agentdeck/` / `agentdeck-statusline.py`（見 `docs/DECISIONS.md` D-09） |

新增檔案（上游沒有）：`AGENTS.md`、`SKILL.md`、`NOTICE.md`、`REPO_REVIEW.md`、`persona_store.py`、`personas/`、`discussion_window_win.py`、`discussion_assets.py`、`docs/FORK.zh-TW.md`、`docs/DECISIONS.md`、`docs/DEVELOPMENT.zh-TW.md`、`docs/PORTING.zh-TW.md`、`docs/UPSTREAM.md`、`tools/`、`reference/`、`.pre-commit-config.yaml`、`.claude/settings.json`。

**有取捨的決定寫進 [`docs/DECISIONS.md`](docs/DECISIONS.md)**，不要只留在 commit message 裡——那是為了避免日後重複討論同一個問題。

## 技術

- Python **3.13**（`requires-python >= 3.13`；mypy 也釘 3.13）。本機預設的 `python` 是 3.14，**不要**拿它建環境，一律用 uv 指定 3.13。
- 環境用 `uv` 管理，`uv.lock` 是唯一真相；`--frozen` 不可省略。
- **stdlib-only 檔案**（`usage_statusline.py`、`usage_statusline_forwarder.py`、`usage_session_resume.py`、`usage_terse_mode.py`、`usage_terse_reminder.py`）要能被使用者的 Claude Code 用**任何** `python3` 執行，不是本專案的 venv：**不可 import 第三方套件**。ruff 的 `UP017`（`datetime.UTC`）豁免是舊 macOS 3.9 下限的遺留，可以另案重新評估。
- `wintray.py` 有成長政策：新功能的**邏輯**放中立 leaf module（`menubar_state.py`、`update_gate.py` 之類），`wintray.py` 只留薄薄的 UI 外殼。理由是外殼裡的判斷測不到——見 [`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md) 第三節。
- 所有使用者可見字串必須走 `i18n.json` 的 `_t()` / JS `t()`。**本 fork 只出貨繁體中文與英文**（上游是五語），新增字串時 `zh-TW` 與 `en` 兩段都要補齊，`tests/test_i18n_key_parity.py` 會擋。
- **兩語言的判定邏輯散在五個檔案**：`usage_lang._normalize_lang()` 是主程式的版本；`usage_statusline.py`、`usage_session_resume.py`、`usage_terse_mode.py`、`usage_terse_reminder.py` 因為必須 stdlib-only、不能 import `usage_lang`，各自帶一份複本；`session_hooks.py` 另有 `RESUME_LANGS` / `TERSE_LANGS`。**改一個就要改全部**。規則：所有中文語系（含簡體）→ `zh-TW`，其餘 → `en`。
- **改版號時不要跑 `uv lock`**：手動改 `uv.lock` 裡 `agentdeck` 那一行的 `version` 即可，零解析風險。`pyproject.toml` 的 `[tool.uv] environments` 現在只鎖 win32 與 linux。

## 常用指令（Windows / PowerShell）

```powershell
uv sync --frozen --group dev --extra windows   # 建環境（等同 Windows CI）
uv run --no-sync ruff check
uv run --no-sync mypy .
uv run --no-sync pytest -q
uv run --no-sync pytest tests/test_usage_client.py::test_name -v   # 單一測試
pwsh tools/dev_check.ps1                        # 一次跑完四道閘門
```

跑程式：

```powershell
uv run --no-sync python main.py --tui       # 終端機 TUI（Windows 主要模式）
uv run --no-sync python main.py --mock      # 假資料預覽
uv run --no-sync python main.py --doctor    # 環境／hook 診斷
```

不加參數的預設模式就是系統匣（`wintray.py`）。macOS 支援已於 2026-07-29 移除，對照用的上游實作在 `reference/upstream-macos/`。

## 開發原則

- 最小干預：修 bug 優先補測試，不主動重構大段程式。
- 文件用繁體中文撰寫；`README.en.md` 與其他英文版文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT）維持英文，中英內容要互相對應。
- 改 README 時**兩邊一起改**：`README.md`（繁中）與 `README.en.md`（英文）的 `##` 章節數必須一致，CI 的 `scripts/check_doc_parity.py` 會擋。
- 動任何 `~/.claude/settings.json` 的安裝／解除流程（`setup_hook.py`、`session_hooks.py`）前先備份，那會動到本機真實的 Claude Code 設定。
- **版本一律用語意化版本（SemVer 2.0.0）**：`MAJOR.MINOR.PATCH`，tag 為 `vX.Y.Z`，**禁止**自創日期版號、build number 或任意後綴。目前在 `0.y.z` 階段：破壞相容性的改動（移除語言、改 hook 檔名／設定 key、拔掉讀取路徑、改 CLI 參數）進 **MINOR**，新功能也進 MINOR，純修 bug 進 **PATCH**；滿 `1.0.0` 之後破壞性改動才升 MAJOR。`pyproject.toml` 的 `version` 是唯一真相，tag 必須指向版號相符的 commit。完整規則見 [`CLAUDE.md`](CLAUDE.md) 的 Versioning 段。
- **測試綠了才准 commit**：`pwsh tools/dev_check.ps1` 全綠再提交，驗證與 commit 之間用 `&&` 閘門，不要用 `;` 串接。
- **修 bug 必回註 `REPO_REVIEW.md`**：每修掉一個列出的問題，回到對應項目補上修復 commit hash 與日期；過程中額外發現並修掉的也要補註。review 維持 latest-only，修復狀態必須跟上現況。
