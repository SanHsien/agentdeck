# Codex Repository Review

覆核日期：2026-07-31  
Repo：`SanHsien/agentdeck`  
分支：`main`  
程式修正基準：`772f7d9`

## 結論

狀態：**可推送，保留兩項非阻擋追蹤**。

這次檢查的是目前整個 Windows fork，不只未提交 diff。程式核心、測試、授權、GitHub workflow 與上游追蹤機制整體健康；實際發現並修正 6 類問題：

1. 系統匣「檢查更新」仍查上游 `aqua5230/usage`，本 fork 新版不會被看見。
2. `pyproject.toml` 宣稱可建 wheel，但 setuptools 清單漏掉現行模組、還列著已刪除的 `discussion_window.py`；產物表面成功，實際不完整。
3. 本機、CI、release 的 gate 不一致：CI 漏掉雙語文件與 AI 更新頁，也沒有先驗 lock freshness。
4. SECURITY、CONTRIBUTING、issue／PR 模板、CLAUDE、SKILL 與 README 還混有上游維護者、macOS、舊產品名或錯誤 Windows 指令。
5. 已移除的 macOS curl installer 仍會下載上游程式碼，並要求使用者結束不存在的 `.app`。
6. AI 圓桌在 900×640 把兩個固定寬度控制項與名稱塞在單列五欄，造成參與者名稱裁切與水平捲軸。

以上均已在 `772f7d9` 修正並加入必要測試／文件。另刪除已被 changelog 與 review 取代的 `AGY_CARD_STATUS.md`。

## 覆核範圍

| 項目 | 結果 |
|---|---:|
| tracked files | 297 |
| Python source（排除 `reference/`） | 155 files / 42,181 lines |
| pytest files | 68 |
| open PR / open issue | 0 / 0 |
| upstream `main` tip | `e94cd4d`，與 `docs/UPSTREAM.md.last_reviewed` 一致 |
| latest release | v0.31.1，published、非 draft、非 prerelease |
| open CodeQL alerts | 0 |

檢查面向包含：

- 資料來源與隱私邊界
- subprocess／外部連線／更新機制
- Windows 系統匣、WebView2 與移植落差
- uv lock、CI、release 與 PyInstaller 打包契約
- i18n、雙語文件、fork 品牌與維護權責
- AGPL-3.0、NOTICE 與發佈文件
- GitHub Actions、CodeQL、ClusterFuzzLite、上游同步與 release 狀態

## 修正摘要

### P1：更新檢查指向錯誤 repo

`update_checker.py` 原本查 `aqua5230/usage/releases/latest`。agentdeck 版號已獨立，結果是新版 agentdeck 不會被提示。

處置：

- 改查 `https://api.github.com/repos/SanHsien/agentdeck/releases/latest`
- User-Agent 改為 `agentdeck/<version>`
- 測試鎖住 request URL 與 header
- 實際連線驗證 v0.31.1 回傳「沒有較新版本、查詢未失敗」

### P1：錯誤的 wheel／editable package 契約

舊 `py-modules` 清單會在 build 時警告 `discussion_window.py` 不存在，並漏掉多個現行 runtime module 與資源。本專案實際只發佈 PyInstaller bundle，沒有 wheel／PyPI 流程。

處置：

- 設定 `[tool.uv] package = false`
- lock root source 由 editable 改為 virtual
- 移除誤導性的 setuptools build/module 清單
- `docs/DEVELOPMENT*` 與 D-12 明確記錄 PyInstaller 是唯一 release 路徑

### P1：本機、CI、release gate 漂移

統一後的六道 gate：

1. `uv lock --check`
2. ruff
3. mypy
4. 雙語文件 parity
5. AI Update Daily freshness
6. pytest

CI 的所有 `uv run` 都加上 `--no-sync`；release 也在 frozen sync 前檢查 lock，避免測試與發佈使用不同相依狀態。

### P2：fork 身分、平台與安全文件漂移

修正範圍：

- SECURITY 改為 agentdeck、SanHsien release 與 `sanhsien@pm.me`
- 明列實際網路範圍，不再宣稱完全沒有 Anthropic／OpenAI 網路呼叫
- CONTRIBUTING、issue／PR 模板改為 Windows + uv 3.13 工作流
- CLAUDE、SKILL、README 與 landing page 移除現行指引中的 macOS／`python3`／舊名稱
- README 補正 AI Council 已可選 persona，並把比較表產品名改為 agentdeck
- 刪除會下載上游檔案的 macOS-only `scripts/install-hook.sh`

### P2：AI 圓桌 900×640 參與者列裁切

根因是單列五欄含兩個 128px 控制項。窄設定欄現在會把 model／persona 放到第二列，並新增 CSS 結構回歸測試。

尚未把「修後 900×640 WebView2 目視重驗」寫成完成；它列在追蹤項。

## 驗證證據

最後一次 commit 前硬閘門：

```text
lock OK
ruff: All checks passed
mypy: Success, 155 source files
doc-parity: PASS
ai-updates: PASS
pytest: 1199 passed, 7 skipped, 1 deselected
```

唯一 deselect 是本機未啟用 Windows 符號連結權限的
`test_usage_dir_sweeper.py::test_keeps_matching_symlink`。directory 與 junction 變體仍執行，CI 也會跑 symlink 變體。

其他實證：

- `main.py --doctor` 可正常啟動並讀到 Codex 本機資料。
- update checker 對本 fork latest release 實際查詢成功。
- GitHub 在上一個遠端 tip `e85c445` 的 CI、CodeQL、Pages 均成功。
- ClusterFuzzLite batch 最近一次成功；CI、CodeQL、Release、上游更新檢查與兩個 fuzz workflow 皆為 active。
- CodeQL open alerts 為 0；secret scanning 與 push protection 已開啟。

## 未阻擋追蹤

### F1：AI 圓桌修後實機目視

以真實 WebView2 再開一次 900×640 視窗，確認參與者名稱、model、persona 與主持按鈕均無水平捲軸或裁切。

### F2：完整 release bundle smoke

本輪沒有重建 `agentdeck-windows.zip`、啟動新 exe 或觸發 tag release。PyInstaller 資源測試已通過，但下一次發版前仍應跑 `scripts/build_windows.ps1` 並做 exe smoke。

## GitHub 設定建議

以下沒有直接修改，因為它們是 repo 設定，不是這次授權的檔案／push 變更：

- Dependabot security updates 目前 disabled；`.github/dependabot.yml` 仍可做版本更新 PR，但 security update 功能未開。
- GitHub private vulnerability reporting 目前 disabled；SECURITY 已提供可用的私人信箱，因此不是回報死路。
- Scorecard workflow 維持 `disabled_fork`，符合 D-10 的刻意決定。
