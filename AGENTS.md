# AGENTS.md

給 AI agent（Codex、Claude Code、Gemini 等）在 **SanHsien/usage** 工作時的指引。

專案本身的架構說明在 [`CLAUDE.md`](CLAUDE.md)。這份文件補 fork 專屬的規則與 Windows 開發環境差異。

## 這是 fork，但獨立維護

- 上游：[`aqua5230/usage`](https://github.com/aqua5230/usage)（AGPL-3.0-only）。
- 本 repo：[`SanHsien/usage`](https://github.com/SanHsien/usage)，remote `origin`；上游掛在 remote `upstream`（唯讀）。
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

新增檔案（上游沒有）：`AGENTS.md`、`SKILL.md`、`NOTICE.md`、`REPO_REVIEW.md`、`docs/FORK.zh-TW.md`、`docs/DECISIONS.md`、`docs/DEVELOPMENT.win.zh-TW.md`、`tools/`、`.pre-commit-config.yaml`、`.claude/settings.json`。

**有取捨的決定寫進 [`docs/DECISIONS.md`](docs/DECISIONS.md)**，不要只留在 commit message 裡——那是為了避免日後重複討論同一個問題。

## 技術

- Python **3.13**（`requires-python >= 3.13`；mypy 也釘 3.13）。本機預設的 `python` 是 3.14，**不要**拿它建環境，一律用 uv 指定 3.13。
- 環境用 `uv` 管理，`uv.lock` 是唯一真相；`--frozen` 不可省略。
- 三個 stdlib-only 檔案（`usage_statusline.py`、`usage_statusline_forwarder.py`、`usage_session_resume.py`）要能在 macOS 內建的 Python 3.9 跑：**不可 import 第三方套件、不可用 `datetime.UTC`**（用 `timezone.utc`）。ruff 的 `UP017` 已針對這幾個檔關掉，別去「修好」它。
- `menubar.py` 有成長政策：新功能邏輯放 leaf module（`menubar_state.py` 之類），這裡只留薄薄的 ObjC dispatch 殼。
- 所有使用者可見字串必須走 `i18n.json` 的 `_t()` / JS `t()`，五種語言（`zh-TW`/`zh-CN`/`en`/`ja`/`ko`）都要補齊才能出貨。**app UI 的五語支援與 README 只留中英兩版是兩回事**，不要因為刪了 README 語言版本就去動 `i18n.json`。
- **不要在 Windows 上跑 `uv lock`**：會把 macOS 的 PyObjC 相依標記成不可能達成、無聲地從 lock 檔裡丟掉，直接弄壞 macOS 打包。`pyproject.toml` 的 `[tool.uv] environments` 就是在防這件事。

## 常用指令（Windows / PowerShell）

```powershell
uv sync --frozen --group dev --extra windows   # 建環境（等同 Windows CI）
uv run --no-sync ruff check
uv run --no-sync mypy .
uv run --no-sync pytest -q
uv run --no-sync pytest tests/test_usage_client.py::test_name -v   # 單一測試
pwsh tools/dev_check.ps1                        # 一次跑完三道 gate
```

跑程式：

```powershell
uv run --no-sync python main.py --tui       # 終端機 TUI（Windows 主要模式）
uv run --no-sync python main.py --mock      # 假資料預覽
uv run --no-sync python main.py --doctor    # 環境／hook 診斷
```

menu bar 模式是 macOS 專屬；Windows 對應的是 `wintray.py`（system tray）。

## 開發原則

- 最小干預：修 bug 優先補測試，不主動重構大段程式。
- 文件用繁體中文撰寫；`README.en.md` 與其他英文版文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT）維持英文，中英內容要互相對應。
- 改 README 時**兩邊一起改**：`README.md`（繁中）與 `README.en.md`（英文）的 `##` 章節數必須一致，CI 的 `scripts/check_doc_parity.py` 會擋。
- 動任何 `~/.claude/settings.json` 的安裝／解除流程（`setup_hook.py`、`session_hooks.py`）前先備份，那會動到本機真實的 Claude Code 設定。
- **測試綠了才准 commit**：`pwsh tools/dev_check.ps1` 全綠再提交，驗證與 commit 之間用 `&&` 閘門，不要用 `;` 串接。
- **修 bug 必回註 `REPO_REVIEW.md`**：每修掉一個列出的問題，回到對應項目補上修復 commit hash 與日期；過程中額外發現並修掉的也要補註。review 維持 latest-only，修復狀態必須跟上現況。
