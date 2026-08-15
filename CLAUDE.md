# CLAUDE.md

Claude Code 維護 `SanHsien/agentdeck` 時的技術入口。**產品邊界、fork / AGPL 規則、Windows-only 原則與一般維護流程以 [`AGENTS.md`](AGENTS.md) 為準。** 本檔只保留高風險技術位置與常用指令；完整架構、建置與 Windows 陷阱見 [`docs/DEVELOPMENT.zh-TW.md`](docs/DEVELOPMENT.zh-TW.md)。

## 專案摘要

agentdeck 是 Python 3.13 的 Windows tray / TUI 應用：

- Claude Code / Codex quota：讀本機資料，不呼叫 Anthropic / OpenAI usage API。
- Antigravity quota：使用本機 CLI 已有登入身分查 Google 官方 quota endpoint。
- Windows UI：`pystray` + `pywebview` / WebView2。
- TUI：`rich`。
- AI Council：驅動本機 provider CLI。
- Persona Market：把開源 persona 寫入已安裝工具的 agent 目錄。
- 報告：本機 HTML / CSV / PNG 分析。

本 repo 是 `aqua5230/usage` 的 AGPL-3.0-only fork，正式產品只支援 Windows。

## 常用指令

環境以 `uv.lock` 為準：

```powershell
uv sync --frozen --group dev --extra windows

uv run --no-sync python main.py            # tray
uv run --no-sync python main.py --mock     # fake-data preview
uv run --no-sync python main.py --tui      # terminal UI
uv run --no-sync python main.py --doctor   # environment / hook diagnostics
uv run --no-sync python usage_cli.py report

pwsh tools/dev_check.ps1                    # normal pre-PR validation
pwsh scripts/build_windows.ps1              # Windows bundle
```

單獨測試：

```powershell
uv run --no-sync pytest tests/test_usage_client.py::test_name -v
```

## 主要資料流

```text
Claude Code statusLine
        │
        ▼
usage_statusline.py ──> ~/.claude/agentdeck-status.json ─┐
                                                         │
Codex ~/.codex/* ───────> providers/codex_loader.py ─────┼─> state / wintray / TUI
                                                         │
Antigravity CLI auth ───> providers/* Antigravity loader ┘
```

Claude / Codex 的 quota path 是 local-first。Antigravity 是例外：quota 來源本來就是 Google 官方端點，但使用的是 Antigravity CLI 已保存的本機登入身分。

## 高風險模組

| 位置 | 注意事項 |
|---|---|
| `setup_hook.py` / `session_hooks.py` | 會修改使用者工具設定；必須有 backup / restore / idempotency，測試只用 temp path。 |
| `usage_statusline*.py` / `usage_session_resume.py` / `usage_terse*.py` | 會被複製到使用者環境；依 [`AGENTS.md`](AGENTS.md) 規定維持 root / stdlib-only。 |
| `providers/codex_loader.py` | Codex 本機資料契約與 `CODEX_HOME` 路徑處理；不要寫回 provider 資料。 |
| Antigravity provider | Credential 只讀；不得把 token 寫 log / cache；刷新後的 access token 只留記憶體。 |
| `wintray.py` | Windows tray / WebView2 orchestration；DPI 座標與 monitor work area 容易出錯，邏輯盡量下沉可測 leaf module。 |
| `council/` | 會啟動 provider CLI；處理 subprocess lifecycle、取消、timeout、唯讀附件邊界時要補測試。 |
| `persona_store.py` | 寫 Claude / Codex / Cursor agent 目錄；同名檔案必須先備份，回報實際寫入位置。 |
| auto-resume / Windows Scheduler | 預設關閉；一次性任務要能清理，不能把 7-day quota 用盡視為應自動續跑。 |
| `update_checker.py` / 外部連結 | URL 必須綁定預期 host / repo；不要退回只驗 scheme 或 substring 的檢查。 |

## i18n

正式 UI 只有 `zh-TW` 與 `en`。使用者可見字串從 `i18n.json` 取值；新增 key 兩邊一起加。

部分 stdlib-only hook 因不能 import 共用模組，會各自保留 locale normalization。改語言映射時搜尋：

- `usage_lang.py`
- `usage_statusline.py`
- `usage_session_resume.py`
- `usage_terse_mode.py`
- `usage_terse_reminder.py`
- `session_hooks.py`

目前所有中文 locale 都映射到 `zh-TW`，其他語系回退 `en`。

## 歷史命名

對外與新寫入資料使用 `agentdeck` / `AGENTDECK_*`。`usage_*`、`menubar_*` 等內部名稱多為上游相容或既有 migration path，不代表需要立即重命名。

尤其不要移動會安裝到使用者環境的 root hook，也不要刪除仍有 migration / fallback 測試覆蓋的歷史路徑。

## 文件與 upstream

- 一般開發：[`docs/DEVELOPMENT.zh-TW.md`](docs/DEVELOPMENT.zh-TW.md)
- Windows 移植：[`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md)
- fork 邊界：[`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)
- upstream 審視：[`docs/UPSTREAM.md`](docs/UPSTREAM.md)
- 長期決策：[`docs/DECISIONS.md`](docs/DECISIONS.md)
- attribution / AGPL / 資料來源：[`NOTICE.md`](NOTICE.md)

處理 upstream-check issue 時才更新 `docs/UPSTREAM.md`；不要把一般 bug fix 變成全文件 sweep。

## 驗證原則

一般 code 變更至少通過：

```powershell
pwsh tools/dev_check.ps1
```

這套 gate 與 CI 對齊：lockfile freshness、ruff、mypy、雙語文件 parity、受控檔案大小、pytest。

若改 Windows tray / DPI / WebView2、排程、真實 CLI 啟動或 PyInstaller bundle，CI 綠燈不等於完成實機驗收；回報時要分開寫「自動測試」與「Windows smoke test」。
