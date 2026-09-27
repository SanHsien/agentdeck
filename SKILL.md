---
name: agentdeck
description: 維護 SanHsien/agentdeck。Windows-only AI coding cockpit：監看 Claude Code、Codex、Antigravity 額度，並提供 AI Council、persona 部署、工作續接與本機報告。Claude Code / Codex quota 讀本機資料，不呼叫 Anthropic / OpenAI usage API。
---

# agentdeck

## 適用情境

- 修復或調整 Windows tray / WebView2 / TUI。
- 維護 Claude Code、Codex、Antigravity quota 資料來源。
- 維護 AI Council、persona 安裝、auto-resume、報告功能。
- 處理 statusLine / companion hook 安裝與診斷。
- 審視並選擇性移植 `aqua5230/usage` 的上游更新。

## 先讀

1. [`AGENTS.md`](AGENTS.md)：產品邊界、fork / AGPL、Windows-only 與驗證規則。
2. [`CLAUDE.md`](CLAUDE.md)：高風險模組與常用技術入口。
3. 任務相關文件：
   - Windows 開發：`docs/DEVELOPMENT.zh-TW.md`
   - 移植：`docs/PORTING.zh-TW.md`
   - upstream：`docs/UPSTREAM.md`
   - attribution / 資料：`NOTICE.md`

## 不可破壞的邊界

- 不重新加入 macOS 正式 build / menu bar 路徑。
- 不為 Claude Code / Codex 接 Anthropic / OpenAI usage API。
- 測試不可碰真實 `~/.claude/`、`~/.codex/`、`~/.cursor/` 或 Windows 排程。
- 安裝到使用者環境的 hook 維持 root / stdlib-only。
- 不移除 AGPL-3.0-only 與上游 attribution。

## 常用指令

```powershell
uv sync --frozen --group dev --extra windows
uv run --no-sync python main.py --mock
uv run --no-sync python main.py --doctor
uv run --no-sync python main.py --tui
uv run --no-sync python usage_cli.py report
pwsh tools/dev_check.ps1
```

## 完成回報

列出：

- 修改檔案與使用者可見影響。
- 是否碰 provider credential、hook / persona 設定、Windows Scheduler、DPI / WebView2 或 release packaging。
- 自動驗證結果。
- 若需要 Windows 實機 smoke，但本輪沒有實測，明確列為未驗證，不用把它寫成產品失敗。
