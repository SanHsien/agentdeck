# Repo Review

覆核日期：2026-07-31 · 版本：v0.31.1 · 分支：`main` · 修正基準：`772f7d9`

本檔維持 **latest-only**：只記**當前狀態與未解問題**。修掉一項就從這裡拿掉，不要留成流水帳——歷史在 git log 與 [`CHANGELOG.zh-TW.md`](CHANGELOG.zh-TW.md)，決策理由在 [`docs/DECISIONS.md`](docs/DECISIONS.md)。這裡只回答兩件事：**現在這個 repo 健康嗎、還有什麼沒解決**。

## 結論

- 六道閘門全綠：lock freshness / `ruff` / `mypy`（155 個檔案）/ 雙語文件對稱性 / AI 更新頁 / `pytest`（1199 passed、7 skipped、1 個本機權限排除）。
- 已完成從 macOS 優先的上游轉為 **Windows 專用**，並改名為 **agentdeck**。
- 2026-07-31 Codex 審查修正了版本檢查仍指向上游、CI／release／本機 gate 不一致、錯誤的 wheel 設定、fork 所有權與 Windows 文件漂移，以及 AI 圓桌參與者列裁切；修正 commit 為 `772f7d9`。
- **未解問題：2 項**——一項是本機環境限制、不是程式缺陷；一項是已修版面的實機目視重驗。

## 環境

| 項目 | 值 |
|---|---|
| OS | Windows 11 Pro 10.0.26200（原生，非 WSL2） |
| Python | 3.13（`.venv`，由 uv 安裝） |
| 建置指令 | `uv sync --frozen --group dev --extra windows`（等同 CI） |

本機預設 `python` 是 3.14，**未**用於本專案：`pyproject.toml` 要求 `>=3.13`，mypy 與 CI 都釘 3.13。

## 未解問題

### P4：`test_keeps_matching_symlink` 需要符號連結權限

`tests/test_usage_dir_sweeper.py` 的這一條呼叫 `Path.symlink_to()`，在未開啟開發人員模式、也非系統管理員的 Windows 上丟 `OSError: [WinError 1314]`。

- **這是環境限制，不是 code bug。** CI 的 windows-latest 有權限，在那裡照跑。
- **影響已縮到最小。** 原本一條測試同時涵蓋目錄與符號連結，沒權限就整條消失。現已拆成三條：`test_keeps_matching_directory`、`test_keeps_matching_junction`（junction 是一般使用者就能建的 Windows reparse point，實測免權限、`lstat` 報 `S_ISDIR`）、`test_keeps_matching_symlink`。前兩條在本機照跑，所以「名稱吻合但不是一般檔案就不刪」這個行為本機仍然覆蓋得到，只有符號連結那個變體會缺。
- 處置：`tools/dev_check.ps1` 先實測本機能不能建連結，不能才 `--deselect` 那一條並印出說明。刻意不在測試裡加 `skipif`——那會讓覆蓋在本機靜默消失（理由見 `docs/DECISIONS.md` D-04）。
- 要連符號連結那條也在本機跑：開啟 Windows 開發人員模式（設定 → 系統 → 開發人員專用），或以系統管理員身分執行 pytest。這是系統設定，由維護者自行決定。

### P5：AI 圓桌參與者列修正後仍需 900×640 實機目視重驗

2026-07-30 實機開窗驗證時發現：參與者那一列同時出現水平與垂直捲軸，模型名稱被右邊的下拉選單擠掉，只看得到第一個字。

- 2026-07-31 已確認根因：`participant-head` 把 badge、名稱、主持按鈕與兩個固定 128px 控制項塞進單列五欄；預設視窗的右側設定欄不足以容納。
- 修正：設定欄較窄時，模型與 persona 控制項換到第二列，移除造成水平捲軸的固定單列需求；`tests/test_discussion_window_win.py` 有斷點與換列結構的回歸測試（`772f7d9`）。
- 剩餘工作只是真實 WebView2 於 900×640 的目視重驗；在完成前不宣稱視覺驗收完成。

## 已確認正常

- **不呼叫用量 API 的核心不變式**：程式碼中沒有任何 Anthropic / OpenAI 用量 API 呼叫。對外連線僅限 LiteLLM 公開價格表、Claude/OpenAI 公開狀態頁、GitHub Releases 更新檢查，以及使用者自己啟用 Antigravity 時的 Google 官方額度端點。
- **更新檢查屬於本 fork**：`update_checker.py` 查詢 `SanHsien/agentdeck` 的 latest release，user agent 也是 `agentdeck/<version>`；單元測試同時鎖住 URL 與 header（`772f7d9`）。
- **AGPL-3.0 合規**：`LICENSE` 與各檔 SPDX 標頭完好；`NOTICE.md` 有 §5a 要求的修改聲明與日期；建置腳本會把 `LICENSE`／`NOTICE.md`／`README.md` 放進發佈產出，缺任一個就讓建置失敗（§4）。
- **發佈模型與打包資源**：本 repo 是 uv virtual root／flat application，不發佈 wheel；正式產物由 PyInstaller 建置。`tests/test_packaged_resources.py` 守著「程式碼透過 `packaged_resource_path()` 要求的資源，都有用 `--add-data` 宣告給 PyInstaller」。
- **上游追蹤**：`docs/UPSTREAM.md` 的 `last_reviewed` 為 `e94cd4d`、`last_merged` 為 `5fbf0ba`；每週 workflow 會回報更新並開 issue。
- **CI 實際涵蓋範圍**：`CI`、`CodeQL`、`上游更新檢查`、`Release` 為啟用狀態並有成功紀錄；`ClusterFuzzLite batch` 已啟用並實測跑完（build 與 30 分鐘 fuzzing 全綠、無 crash）。`ClusterFuzzLite PR` 保留但只在 PR 時觸發，`Scorecard` 刻意維持停用——理由見 `docs/DECISIONS.md` D-10。

## Windows 平台落差：已全數處理

上游是 macOS 優先的專案，本 fork 的目的是把功能搬過來、不是接受落差（規則見 [`AGENTS.md`](AGENTS.md)，方法見 [`docs/PORTING.zh-TW.md`](docs/PORTING.zh-TW.md)）。盤點出的落差**沒有未處理項**：

| 落差 | 結果 |
|---|---|
| AI 圓桌討論僅 macOS | 移植完成（pywebview host）；視窗建立與關閉已實機驗證。900×640 參與者列裁切已於 `772f7d9` 修正，待修正後目視重驗（P5） |
| hook 安裝／statusLine 切換／session resume／terse mode／報告產生失敗無回饋 | 五處都接上結果回報 |
| 更新提示無法「跳過此版本」 | 三鈕對話框；Escape 落在「稍後」而非「跳過」 |
| 無自動每日更新檢查（README 卻宣稱有） | 掛進輪詢，採用自動檢查偏好／每日間隔／近期「稍後」／已跳過版本四道閘門 |
| 選單項 tooltip（pystray 不支援） | 改為啟用該功能時以對話框說明一次 |
| AI 人才市場依賴閉源二進位 | 改為自製開源版（`persona_store` + `personas/`） |
| 面板未貼齊系統匣圖示 | **不做**——上游反而放棄了貼齊（D-07）；但修掉其中真正的缺陷：首次開啟的角落現在跟著工作列位置走 |
| py2app `RESOURCEPATH` 死碼 | 清除，並留一條合併防護測試（上游仍有那段） |

發現新落差就補進這張表，並依移植手冊處理。

## 教訓（會重複踩的那幾種）

- **「環境問題」不是結案理由，是待查標籤。** 分辨方法不是「拿掉觸發條件會不會過」——那必然會過——而是問**被觸發的行為本身合理嗎**。塗銷邏輯遇到單字元的值就把整段輸出打碎，不合理，是 bug；`symlink_to()` 在沒有權限時丟 `WinError 1314`，合理，是環境限制。
- **盤點有保存期限。** 落差寫進待辦後，動手前要再確認上游現在怎麼想——D-07 那條在盤點時是真的，兩個上游 commit 之後就不是了。
- **`git log main..branch` 說「領先 N 個 commit」不代表改動沒進去。** 上游可能 squash 或重新實作過；判斷要比對**當前檔案內容**（D-06）。
- **刪掉一個測試前，先想清楚它在擋什麼。** `test_packaged_resources` 被刪過一次，改寫回來後立刻抓到 `--add-data` 與資源名稱不一致。
- **稽核用的 grep 會騙人。** 比對 i18n key 時漏了單引號與跨行呼叫，產出的落差清單有三項是假的。正確做法見移植手冊第一節。
