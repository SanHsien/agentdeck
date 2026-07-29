---
name: usage
description: 在 macOS menu bar / Windows system tray / 終端機 TUI 顯示 Claude Code 與 Codex 的配額用量。數字全部讀本機檔案（statusLine hook 寫的 JSON、Codex sessions JSONL），不呼叫任何用量 API。此 skill 用於維護 SanHsien/usage。
---

# usage

## 何時使用

- 要看／解讀 Claude Code 或 Codex 的 5 小時、7 天配額用量與燃燒率。
- 要維護 `SanHsien/usage`：修 bug、補測試、調 Windows 相容性、選擇性撿上游更新。
- 要安裝或排除 statusLine hook（`~/.claude/usage-status.json` 沒更新之類）的問題。

不適合的任務：

- 想「接 API 拿更準的用量」——本專案的核心不變式就是不呼叫任何 LLM 用量 API，這條不能破。
- macOS 專屬的 menu bar / `.app` 打包工作——開發機是 Windows 11，只能改 code 不能驗收，需要在 macOS 上實測。

## 前置

```powershell
uv sync --frozen --group dev --extra windows
```

需要 Python 3.13（`uv python install 3.13`）。本機預設 `python` 是 3.14，不要拿來建環境。

## 常用

```powershell
uv run --no-sync python main.py --tui        # 終端機 TUI
uv run --no-sync python main.py --mock       # 假資料預覽
uv run --no-sync python main.py --doctor     # 診斷 hook 與環境
uv run --no-sync python usage_cli.py report  # 終端機分析報告
pwsh tools/dev_check.ps1                     # ruff + mypy + pytest 三道 gate
```

## 注意

- 改 code 前先讀 [`CLAUDE.md`](CLAUDE.md)（架構）與 [`AGENTS.md`](AGENTS.md)（fork 規則與已分叉之處）。
- 測試不可碰真實 `~/.claude/`、`~/.codex/`。
- README 是繁中為預設（`README.md`）、英文在 `README.en.md`，兩邊章節數要一致，CI 會擋。
- Windows 上有兩個測試會因環境（符號連結權限、Claude Code SDK 注入的環境變數）失敗，不是 code bug——根因與處理見 [`REPO_REVIEW.md`](REPO_REVIEW.md)。
