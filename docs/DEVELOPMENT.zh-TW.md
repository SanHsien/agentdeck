# 開發文件

繁體中文 · [English](DEVELOPMENT.md)

agentdeck 是 Windows 專用的。fork 規則見 [`FORK.zh-TW.md`](FORK.zh-TW.md)，架構見 [`../CLAUDE.md`](../CLAUDE.md)，移植 macOS 功能的方法見 [`PORTING.zh-TW.md`](PORTING.zh-TW.md)。

## 前置

- **Python 3.13**。`pyproject.toml` 要求 `>=3.13`，mypy 也釘 3.13。本機預設的 `python` 是 3.14，**不要拿它建環境**——CI 跑 3.13，用 3.14 開發等於在驗證別的東西。
- **uv**。`uv.lock` 是相依的唯一真相。
- `pwsh`（PowerShell 7+）。

```powershell
uv python install 3.13
```

## 建環境

```powershell
uv sync --frozen --group dev --extra windows
```

這行跟 CI 的 job（`.github/workflows/check.yml`）**完全相同**。三個要素都不能省：

- `--frozen`：照 `uv.lock` 裝，不重新解析相依。
- `--group dev`：ruff、mypy、pytest。
- `--extra windows`：`pystray`、`pillow`、`pywebview`——系統匣 UI 要用的。

裝完會有 `.venv\`（Python 3.13，已 gitignore）。

### 如果 checkout 放在 OneDrive 資料夾裡

把 `UV_PROJECT_ENVIRONMENT` 指到 OneDrive 以外的位置，例如：

```powershell
setx UV_PROJECT_ENVIRONMENT "C:	mpgentdeck"
```

OneDrive 樹裡的每個目錄都是 Files On-Demand 佔位目錄（reparse tag
`IO_REPARSE_TAG_CLOUD_E`），雲端過濾驅動會掛在每一次檔案操作的路徑上——**暫停同步不會把它卸載**。
一次移除大量套件目錄時可能跟該驅動搶輸，留下半移除的環境。放到外面同時也省下
OneDrive 同步約 5,000 個「`uv.lock` 幾秒就能重建」的檔案。

`uv run` 與 `tools/dev_check.ps1` 都會讀這個變數。CI 不受影響——它從不設定它，
所以 runner 照舊用 `.venv`。

## 閘門

```powershell
pwsh tools/dev_check.ps1
```

一次跑完六項：lock freshness、`ruff check`、`mypy .`、雙語文件對稱性、AI 更新頁同步檢查、`pytest`。全綠才能 commit。分開跑：

```powershell
uv lock --check
uv run --no-sync ruff check
uv run --no-sync mypy .
uv run --no-sync python scripts/check_doc_parity.py
uv run --no-sync pytest -q
```

`--no-sync` 避免每次都重新檢查相依。

## 跑起來看

```powershell
uv run --no-sync python main.py             # 系統匣（預設）
uv run --no-sync python main.py --tui       # 終端機 TUI
uv run --no-sync python main.py --mock      # 假資料預覽，不需要真的有用量
uv run --no-sync python main.py --doctor    # 診斷 hook 安裝狀態與環境
uv run --no-sync python usage_cli.py report # 終端機分析報告
$env:AGENTDECK_DEBUG=1; uv run --no-sync python main.py   # 讓被吞掉的例外浮出來
```

## 打包

這是以 PyInstaller 發佈的 flat application，不發佈 wheel／PyPI 套件；`[tool.uv] package = false` 是刻意設定。請勿用 `uv build` 當作 release 驗證。

```powershell
pwsh scripts/build_windows.ps1      # 產出 dist/agentdeck-windows/agentdeck.exe
```

建置腳本會把 `LICENSE`、`NOTICE.md`、`README.md` 複製到產出目錄旁——AGPL-3.0 §4 要求每份副本都帶授權全文，缺任一個會讓建置失敗。

動到打包相關的東西之後，跑 `pytest tests/test_packaged_resources.py`：它守著「程式碼用 `packaged_resource_path()` 要求的資源，都有用 `--add-data` 宣告給 PyInstaller」。漏宣告不會拋錯，只會在打包後變成找不到檔案。

## 幾個容易踩的地方

- **stdlib-only 檔案**：`usage_statusline.py`、`usage_statusline_forwarder.py`、`usage_session_resume.py`、`usage_terse_mode.py`、`usage_terse_reminder.py` 會被使用者的 Claude Code 用**任何** `python3` 執行，不是本專案的 venv，因此**不可 import 第三方套件**。
- **DPI**：Win32 回傳的座標是實體像素，pywebview 的 API 是邏輯像素。要用 `wintray._monitor_dpi_scale()` / `_to_logical_rect()` 換算，否則面板會開在螢幕外（v0.30.0 修過這個 bug）。
- **模組檔名仍是 `usage_*`**：那是內部實作，刻意不隨產品改名（見 [`DECISIONS.md`](DECISIONS.md) D-09）。它們**安裝到 `~/.claude/` 的檔名**才是 `agentdeck-*`。

## 已知的本機測試失敗

`test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink` 在沒有符號連結權限的機器上必定失敗（需開發人員模式或系統管理員）。這是**環境限制、不是 code bug**：`tools/dev_check.ps1` 會先實測能不能建連結，不能才排除這一條並印出說明；CI 的 windows-latest 有權限，那裡照跑。
