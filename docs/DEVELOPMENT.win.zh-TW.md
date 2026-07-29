# Windows 開發環境

上游的 [`DEVELOPMENT.zh-TW.md`](DEVELOPMENT.zh-TW.md) 是 macOS 導向的（`source .venv/bin/activate`、`.app` 打包）。這份文件補 Windows 11 原生（非 WSL2）的實際做法。

fork 規則見 [`FORK.zh-TW.md`](FORK.zh-TW.md)；專案架構見 [`CLAUDE.md`](../CLAUDE.md)。

## 前置

- **Python 3.13**。`pyproject.toml` 要求 `>=3.13`，mypy 也釘 3.13。本機預設的 `python` 是 3.14，**不要拿它建環境**——上游 CI 跑的是 3.13，用 3.14 開發等於在驗證別的東西。
- **uv**（本機 0.12.0）。`uv.lock` 是相依的唯一真相。
- `pwsh`（PowerShell 7+）。

```powershell
uv python install 3.13
```

## 建環境

```powershell
uv sync --frozen --group dev --extra windows
```

這行跟上游 Windows CI job（`.github/workflows/check.yml`）**完全相同**。三個要素都不能省：

- `--frozen`：照 `uv.lock` 裝，不重新解析相依（重 lock 會弄壞 macOS 的 PyObjC，理由見 `FORK.zh-TW.md`）。
- `--group dev`：ruff、mypy、pytest。
- `--extra windows`：`pystray`、`pillow`、`pywebview`——Windows system tray 要用的。

裝完會有 `.venv\`（Python 3.13.14，已 gitignore）。macOS 專屬的 PyObjC 套件不會裝，那是預期的：`pyproject.toml` 用 `sys_platform == 'darwin'` marker 擋掉了。

## 三道 gate

```powershell
pwsh tools/dev_check.ps1
```

或分開跑：

```powershell
uv run --no-sync ruff check
uv run --no-sync mypy .
uv run --no-sync pytest -q
```

`--no-sync` 避免每次跑都重新檢查相依。三項全綠才能 commit——CI 跑一模一樣的三項。

## 跑起來看

```powershell
uv run --no-sync python main.py --tui       # 終端機 TUI（Windows 的主要模式）
uv run --no-sync python main.py --mock      # 假資料預覽，不用真的有用量
uv run --no-sync python main.py --doctor    # 診斷 hook 安裝狀態與環境
uv run --no-sync python usage_cli.py report # 終端機分析報告
$env:USAGE_DEBUG=1; uv run --no-sync python main.py   # 讓被吞掉的例外浮出來
```

**menu bar 模式（不加參數的預設）在 Windows 跑不起來**，那是 PyObjC 專屬。Windows 對應的是 `wintray.py`（system tray）。

## 平台差異

| 項目 | macOS | Windows |
|---|---|---|
| 常駐 UI | menu bar（`menubar.py`, PyObjC） | system tray（`wintray.py`, pystray） |
| 開機自啟 | LaunchAgent（`login_item.py`） | 登錄檔（`win_login_item.py`） |
| 打包 | `scripts/build_app.sh` → `dist/usage.app` | `scripts/build_windows.ps1` → `winbuild/` |
| hook 直譯器 | 系統內建 `/usr/bin/python3`（3.9） | 一般 Python 3 |

因為 hook 腳本要能在 macOS 內建的 3.9 上跑，`usage_statusline.py`、`usage_statusline_forwarder.py`、`usage_session_resume.py` 這三個檔**只能用 stdlib、不能用 `datetime.UTC`**（用 `timezone.utc`）。ruff 的 `UP017` 已針對它們關掉，不要去「修好」。

## 已知的 Windows 測試失敗

`pytest` 在 Windows 上有一個測試會失敗，是**本機權限限制、不是 code bug**：

- `test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink`：建立符號連結需要權限（開發人員模式或系統管理員）。`tools/dev_check.ps1` 會先實測本機能不能建連結，不能才排除這一條並印出說明；CI 的 windows-latest 有權限，那裡照跑。

（曾有第二個失敗 `test_discussion_cli.py::test_stdout_diagnostic_tail_has_fixed_line_limit`，根因是 `discussion_cli` 的塗銷邏輯沒有值長度下限，已修復，見 [`REPO_REVIEW.md`](../REPO_REVIEW.md) P3。）

21 個 skip 全部是 macOS / POSIX 專屬測試（PyObjC、process group signal、`/bin/sh` quoting），在 Windows 上 skip 是正確行為。
