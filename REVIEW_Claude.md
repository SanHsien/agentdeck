# Repo Review — Claude

覆核日期：2026-07-31 · 版本：v0.31.2+ · 分支：`main`

**這是 Claude 的覆核紀錄。Codex 的覆核寫在 [`REVIEW_Codex.md`](REVIEW_Codex.md)，兩份各自維護、不互相改寫。** 對彼此改動的意見寫在自己這份裡（見「對 Codex 改動的覆核」），這樣兩邊的判斷都留得住，也看得出哪些是被獨立驗證過的。

本檔維持 **latest-only**：只記**當前狀態與未解問題**。修掉一項就從這裡拿掉，不要留成流水帳——歷史在 git log 與 [`CHANGELOG.zh-TW.md`](CHANGELOG.zh-TW.md)，決策理由在 [`docs/DECISIONS.md`](docs/DECISIONS.md)。這裡只回答兩件事：**現在這個 repo 健康嗎、還有什麼沒解決**。

## 結論

- 六道閘門全綠：lock freshness / `ruff` / `mypy`（155 個檔案）/ 雙語文件對稱性 / AI 更新頁 / `pytest`（1215 passed、7 skipped、1 個本機權限排除）。實跑複驗，非引用他人回報。
- 已完成從 macOS 優先的上游轉為 **Windows 專用**，並改名為 **agentdeck**。
- 2026-07-31 Codex 於 `772f7d9` 修正了更新檢查仍指向上游、CI／release／本機 gate 漂移、wheel 設定、fork 身分文件，以及 AI 圓桌參與者列裁切。**已逐項獨立驗證：三項確認有效、一項為部分修正、一項發現新缺陷**（見下節）。
- **未解問題：1 項**——只剩本機符號連結權限（P4），是環境限制、不是程式缺陷。
- P5（AI 圓桌版面）與 P6（發版版號）已修並實測關閉；證據見 [`docs/release-evidence/`](docs/release-evidence/)。

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

## 對 Codex 改動的覆核（`772f7d9`、`e575768`）

逐項獨立驗證，不採信 commit message 的自我宣稱。

| 項目 | 判定 | 驗證方式 |
|---|---|---|
| `update_checker.py` 指向上游 | ✅ **有效，且是真缺陷** | 原本查 `aqua5230/usage` 的 latest release——agentdeck 使用者會被通知去更新到上游的版本。這是使用者看得到的功能性錯誤，先前的覆核漏掉了 |
| 刪除 `scripts/install-hook.sh` | ✅ **有效，且比「死碼」更嚴重** | 該腳本從上游的 raw URL 下載 `usage_statusline.py` 裝進使用者的 `~/.claude/`。不只是 macOS 專用的死碼，是會把上游程式碼裝到本 fork 使用者機器上。grep 確認無殘留引用 |
| `package = false`、移除 `[build-system]` | ✅ **方向正確，但有一個本機陷阱**（見下方 P6） | 風險在 `wintray._current_version()` 走 `metadata.version("agentdeck")`。實測：模擬 `PackageNotFoundError` 後 fallback 正確回傳版號；`build_windows.ps1` 有 `--add-data pyproject.toml`，凍結後的 exe 讀得到；`uv lock --check` 通過 |
| CI 補上 doc-parity／ai-updates／`uv lock --check` | ✅ **有效** | 先前 CI 比本機 `dev_check.ps1` 弱，兩道文件閘門只在本機跑。現在兩邊一致 |
| P5 參與者列裁切 | ⚠️ **當時為部分修正，現已補完** | 實機量測顯示換列讓卡片變高、下拉選單改被容器垂直切掉 24px。後續調整 `.controls-scroll` 的 `min-height` 與 `.setup` 的 `max-height` 才真正解決，並以 3×2 矩陣驗證 |
| 新測試 `test_participant_controls_reflow…` | ❌ **發現缺陷，已修** | 插入新函式時把前一個測試最後一行 `assert win.EVENT_DRAIN_LIMIT == 50` 併進了新測試尾端。結果是 `test_drain_limit_and_shared_serializer` **不再斷言 drain limit**（名字與內容不符），而 CSS 測試多了一條與 CSS 無關的斷言。**兩者都仍會通過，所以 CI 抓不到** |

**這次覆核學到的**：`772f7d9` 的兩個最有價值的修正（更新檢查指向上游、install-hook 拉上游程式碼）有共同特徵——**都是 fork 繼承下來、指向原專案的東西**，而且都不會讓任何測試變紅。改名與去品牌時我掃的是「顯示給人看的字串」，漏掉了「連出去的網址」。**下次做 fork 身分稽核，要把所有對外 URL 當成獨立一類逐條檢查，不能靠 grep 專案名稱帶出來。**

**測試互相污染這一類**：新增測試時把游標停在前一個測試的最後一行、於其上插入新函式，就會產生這種「斷言換了主人」的結果。兩邊都綠，靜態檢查也不會抱怨。加測試後值得看一眼 diff 的上下文邊界。

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
| AI 圓桌討論僅 macOS | 移植完成（pywebview host）。參與者卡裁切已完全修正，並以 3 種 DPI × 2 種尺寸的實機矩陣驗證（見 `docs/release-evidence/2026-07-31-discussion-layout.md`） |
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
- **改名／去品牌時，「連出去的網址」是獨立一類。** 掃字串會抓到顯示文字，抓不到 `update_checker.py` 的 API URL 或 `install-hook.sh` 的下載來源——那兩處都還指著上游，而且都不會讓測試變紅。
- **UI 修正只讀 CSS 判定不了成敗。** P5 的換列在 CSS 上完全正確，實機開窗才看得到裁切只是從水平換成垂直。版面問題一律要開窗看。
