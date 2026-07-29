# Repo Review

覆核日期：2026-07-29

覆核範圍：fork 初始化。基準 `main` @ `81b89e1`（`usage` v0.29.7，當時與 `upstream/main` 完全同步）、Windows 11 原生開發環境、CI gate 實跑。

本檔維持 **latest-only**：只記當前狀態與未解問題。修掉任一項就回到對應段落補上修復 commit hash 與日期。

## 結論

- 開發環境已建立並實跑驗證。初次全量跑：`ruff` 綠、`mypy` 綠（159 個檔案）、`pytest` 1171 passed / 21 skipped / **2 failed**。
- 兩個 failed 起初都被歸類為環境問題，逐一查根因後發現**只有一個真的是**：
  - **P3 是真實的程式碼缺陷**（塗銷邏輯沒有值長度下限），已修復（`8ac5d52`）。
  - **P4 才是純環境限制**（本機沒有建立符號連結的權限），CI 不受影響，維持現狀。
- 目前狀態（`pwsh tools/dev_check.ps1`）：ruff / mypy / doc-parity / pytest 四道全綠，**1175 passed / 21 skipped / 1 deselected**，exit 0。
- 21 個 skip 全為 macOS / POSIX 專屬（PyObjC、process-group signal、`/bin/sh` quoting），在 Windows 上 skip 是正確行為。
- 尚未在 macOS 驗收任何 menu bar / `.app` 打包路徑——本機是 Windows，這部分**無法**由本次覆核背書。

## 環境

| 項目 | 值 |
|---|---|
| OS | Windows 11 Pro 10.0.26200（原生，非 WSL2） |
| Python | 3.13.14（`.venv`，由 uv 安裝） |
| uv | 0.12.0 |
| 建置指令 | `uv sync --frozen --group dev --extra windows`（等同上游 Windows CI job） |
| 已安裝套件 | 27 個，含 `ruff` 0.16.0、`mypy` 2.3.0、`pytest` 9.1.1、`pystray` 0.19.5、`pywebview` 6.2.1 |

本機預設 `python` 是 3.14.6，**未**用於本專案：`pyproject.toml` 要求 `>=3.13`、mypy 釘 3.13，上游 CI 也是 3.13。

## 已修正問題

### P3：短值的「機密」環境變數會讓 `discussion_cli` 的塗銷邏輯誤傷普通輸出

`discussion_cli._redact_environment_values()`（`discussion_cli.py:836`）對名稱符合
`TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH`（`SENSITIVE_ENV_NAME_RE`，`discussion_cli.py:68`）
的環境變數，用 `str.replace()` 把它的值從子行程輸出中無條件塗成 `[REDACTED]`，**沒有長度下限**。

在 Claude Code SDK session 裡，環境有 `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH=1`（名稱含 `AUTH`，值只有一個字元 `"1"`）。
於是輸出中每一個 `1` 都被塗掉：`test_stdout_diagnostic_tail_has_fixed_line_limit` 期望
`lines[0] == "stdout-10"`，實得 `"stdout-[REDACTED]0"`。

- 影響：診斷輸出被無意義地打碎，使用者看不懂錯誤訊息。不是安全漏洞（方向是過度塗銷，不是洩漏）。
- 初步診斷：`env -u CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH -u CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH uv run pytest tests/test_discussion_cli.py -q`
  → 53 passed / 4 skipped。當時據此判為「環境注入」，**這個結論是錯的**：拿掉觸發條件只證明觸發條件是什麼，不代表被觸發的行為是對的。缺陷在程式碼。
- 修法：新增 `MIN_REDACTED_VALUE_LENGTH = 8`，值長度不足 8 的一律不塗銷。真實憑證遠長於此，原本受保護的內容不受影響。
- 迴歸測試：`test_short_sensitive_environment_values_do_not_redact_ordinary_output`（單字元值不得塗掉普通輸出）與 `test_redaction_length_floor_is_inclusive`（門檻上下各一，釘住 8 這個邊界）；既有的 `test_sensitive_environment_values_are_redacted_from_errors` 仍綠。
- 連帶清理：`tools/dev_check.ps1` 的 `-SkipEnvScrub` 繞道已移除——根因修掉後，繞道只會讓本機執行環境與 CI 不一致，反而遮蔽同類回歸。
- 修復後驗證：在**仍帶有** `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH=1` 的環境下直接跑 `pytest tests/test_discussion_cli.py::test_stdout_diagnostic_tail_has_fixed_line_limit` → 1 passed（修復前必失敗）。四道 gate 全綠，1175 passed / 21 skipped / 1 deselected。
- 修復：`8ac5d52`（2026-07-29）

### P4：`test_keeps_matching_directory_and_symlink` 在無符號連結權限的 Windows 上必定失敗

`tests/test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink` 呼叫 `Path.symlink_to()`，
在未開啟開發人員模式、也非系統管理員的 Windows 上丟 `OSError: [WinError 1314]`。

- 影響：純本機環境限制。上游 Windows CI（`windows-latest`）有建立符號連結的權限，CI 不受影響。
- 處置（擇一）：開啟 Windows 開發人員模式，或以系統管理員身分執行 pytest。
  `tools/dev_check.ps1` 會先實測本機能否建立符號連結，不能才 `--deselect` 這一條並明確告知。
- 可考慮的改善：在測試加 `pytest.mark.skipif`（無 symlink 權限則 skip），讓本機結果乾淨。屬體感改善、非必要，且會讓測試在本機靜默失去覆蓋——目前選擇留在 `dev_check.ps1` 這層處理（見 `docs/DECISIONS.md` D-04）。
- 修復：_不需修復（環境限制）_

## 已確認正常

- **不呼叫用量 API 的核心不變式**：程式碼中沒有任何 Anthropic / OpenAI 用量 API 呼叫；對外連線僅限 LiteLLM 公開價格表、Claude/OpenAI 公開服務狀態頁、GitHub Releases 更新檢查。與 `CLAUDE.md` 的聲明一致。
- **`uv.lock` 未被污染**：`[tool.uv] environments` 已針對三平台鎖定，`--frozen` 安裝未觸發重新解析，macOS 的 PyObjC 相依仍在 lock 中。
- **`.gitignore` 覆蓋充分**：`.venv/`、`vendor/`（私有 instate-cli 二進位）、`SESSION.md`、各式本機快取均已排除。
- **fork remote 配置正確**：`origin` → `SanHsien/usage`，`upstream` → `aqua5230/usage`。

## 待辦

- [x] 修掉 P3（含迴歸測試）—— `8ac5d52`（2026-07-29）。
- [x] Windows DPI 縮放缺陷（225% 下面板開在螢幕外）—— v0.30.0。

### 進行中：轉為 Windows 專用並改名（2026-07-29 決定，依此順序）

維護者決定本 fork **只做 Windows**，不再提供 macOS。三步驟，前一步完成才進下一步：

**步驟 1 — 把 AI 圓桌討論移植到 Windows。**
這是唯一「有功能、但 Windows 沒有對應」的東西（AI 人才市場依賴 gitignore 掉的私有 `vendor/instate-cli`，跨平台都缺，不在此列）。
- `discussion_cli.py`、`discussion_bridge.py`、`discussion_session.py` 已是平台中立，不必動。
- 只有 `discussion_window.py` 綁 PyObjC，且僅三處：視窗建立（NSWindow + WKWebView）、剪貼簿讀圖（NSPasteboard）、檔案挑選（NSOpenPanel）。該檔第 40–570 行（附件處理、`parse_discussion_action`、`_load_discussion_html`、事件序列化）全部平台中立，可直接沿用。
- 作法：把 `DiscussionWindowController` 改寫成 pywebview 版。**pywebview 支援多視窗共用同一個 `webview.start()` 迴圈**，所以圓桌視窗是按需建立的第二個視窗，不需要另起 GUI 迴圈；沿用 `wintray.py` 既有的 `webview.create_window(...)` + `js_api` 橋接模式。
- 剪貼簿讀圖改用 Windows API 或 Pillow 的 `ImageGrab.grabclipboard()`；檔案挑選改用 pywebview 的 `create_file_dialog`。
- **注意 DPI**：新視窗的定位若要用 Win32 工作區，必須沿用 `wintray._monitor_dpi_scale()` / `_to_logical_rect()`，否則會重蹈 v0.30.0 修掉的那個 bug。

> **步驟 1 已完成**（`7993231` 建立 Windows host、`861250f` 接上系統匣選單）。維護者已於 2026-07-29 實機點開視窗確認可正常顯示。

**步驟 2 — 移除 macOS 專屬程式碼。**

⚠️ **動手前先看這份相依分析（2026-07-29 實測）**，`menubar`／`panels` 這些名字會騙人：

- **真正在 module 層綁 PyObjC 的只有 3 個檔案**：`menubar.py`、`login_item.py`、`panels/web_panel.py`。這三個可以直接刪。
- **名字像 macOS、其實平台中立且被 `wintray` 依賴，不可刪**：`menubar_state.py`、`menubar_prefs.py`、`menubar_agy.py`、`panels/payload.py`、`panels/dynamic_height.py`。
- **有順序陷阱、不能直接刪**：
  - `discussion_window.py` —— AppKit 是**延遲 import**（寫在函式內），所以在 Windows 上照樣可載入，而 `discussion_window_win.py` 正是靠這點沿用它的 `parse_discussion_action`、`serialize_event_batch`、`save_attachment_bytes`、`import_attachment_file`、`attachment_thumbnail_data_uri`、`_load_discussion_html`、`PARTICIPANT_LABELS`、`DROP_MAX_BYTES`、`ATTACHMENT_SUFFIXES`。**必須先把這些中立函式搬進 `discussion_window_win.py`（或另立中立模組），才能刪掉 PyObjC 外殼**，否則 Windows 版直接壞掉。
  - `talent_market_bridge.py` —— 同樣是延遲 import。`list_personas` 仍被 Windows 版使用（缺 vendor binary 時回傳 `[]`，優雅降級），只有 `pick_folder` / `pick_image_file` 綁 PyObjC。


以下模組的 Windows 對應**早就存在**，不是要「改寫」，是刪除冗餘：
`menubar.py` → `wintray.py`；`panels/web_panel.py` → wintray 的 WebView2 面板；`login_item.py` → `win_login_item.py`；`setup_app.py`／`scripts/build_app.sh`／`scripts/build_icns.sh`／`scripts/make_app_icon.py`／`*.plist`／`scripts/install-launchagent.sh` → `scripts/build_windows.ps1`。
連帶要清：`pyproject.toml` 的 PyObjC 相依與 `[dependency-groups] build` 的 py2app、`tests/conftest.py` 的 `collect_ignore`、macOS-only 測試、`.github/workflows` 的 macOS job、README／CLAUDE.md／landing page 的 macOS 敘述。
`usage_statusline.py` 等三個 stdlib-only 檔案的「要能在 macOS 內建 Python 3.9 跑」限制隨之解除，但**先不要**順手現代化語法——那是獨立的一次改動。

**步驟 3 — 改名 `usage` → `quotatray`。**
維護者確認**不需要 legacy 相容層**（沒有其他使用者）。要一起改：repo 名稱、`pyproject.toml` 的 `name`、所有 `usage_*.py` 模組名與 `py-modules` 清單、hook 檔名（`~/.claude/usage-statusline.py` 等）、狀態檔（`usage-status.json`）、settings key、`~/.usage/` 快取目錄、`USAGE_LANG` / `USAGE_DEBUG` 環境變數、bundle id、`usage.exe`、README／文件／landing page。
**改名後維護者本機已安裝的 hook 會失效**（2026-07-25 裝的），必須重跑一次 `--setup`；改名的同一次改動要一併處理舊 hook 的解除安裝，不要留孤兒檔案在 `~/.claude/`。

版號依 SemVer（見 `docs/DECISIONS.md` D-05）：步驟 1 是新功能 → MINOR；步驟 2、3 是破壞性改動，`0.y.z` 階段同樣 → MINOR。

## 教訓

**「環境問題」不是結案理由，是待查標籤。** 本輪兩個測試失敗一開始都被歸類為環境問題，實際上一個是真缺陷、一個才是真環境限制。分辨方法不是「拿掉觸發條件會不會過」——那必然會過——而是問：**被觸發的那個行為本身合理嗎？** 塗銷邏輯遇到單字元的值就把整段輸出打碎，不合理，所以是 bug；`Path.symlink_to()` 在沒有權限的系統上丟 `WinError 1314`，合理，所以是環境限制。同理見 [`docs/DECISIONS.md`](docs/DECISIONS.md) D-04。

## 本 fork 的分叉決定（2026-07-29）

- 定位改為**獨立維護、不回貢上游**；`main` 允許與上游分叉，上游更新選擇性撿。
- README 改為繁中預設（`README.md`）、英文為 `README.en.md`；刪除 `zh-CN` / `ja` / `ko` 三個語言版本。
- 連帶調整 `scripts/check_doc_parity.py` 的 `DOC_PAIRS`（改比對 `README.en.md` ↔ `README.md`）與 `CLAUDE.md` 的文件慣例段落，避免文件與實際結構互相矛盾。
- app UI 仍維持五語（`i18n.json` 未動）——只有 README 檔案減為中英兩版。
- 完整分叉清單與撿上游更新的流程見 [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。
