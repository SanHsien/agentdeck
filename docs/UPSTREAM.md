# 上游同步狀態

上游 [`aqua5230/usage`](https://github.com/aqua5230/usage) 仍在活躍開發，所以本 fork 需要定期評估「上游有什麼新東西、要不要吃進來」。這份文件是那個評估的**單一真相源**。

機制：`.github/workflows/upstream-check.yml` **每天 02:00 UTC** 跑 `tools/check_upstream_updates.py`，比對下方標記區塊的 `last_reviewed` 與上游 `main` 的 tip。有比 `last_reviewed` 新的 commit 就開／更新一個「上游更新檢查」issue。

## 兩個標記的分工

| 標記 | 意思 |
|---|---|
| `last_reviewed` | **已看過**的最後一個上游 commit，包含看過之後決定不採用的。只負責「不要再提醒我這一筆」。 |
| `last_merged` | 實際**合併進本 fork** 的最後一個上游 commit。 |

兩者會分岔，而且**應該**分岔——這正是它們分開存在的理由。只推進 `last_reviewed` 表示「看過、不用」。

## 收到「上游更新檢查」issue 時的處理流程

**適用所有 AI agent（Claude Code、Codex、Gemini…）與人。**

1. 逐筆讀 commit 內容，判斷是否適用本 fork（Windows-only、繁中/英雙語、已移除 macOS）。
2. **採用** → 走 `git merge` 或 `git cherry-pick`，完成後同時推進下方的 `last_merged` 與 `last_reviewed`。
3. **不採用** → 只推進 `last_reviewed`，**並且**在下方「Skipped」表補一列（commit、標題、審視日期、不採用的理由），在 [`DECISIONS.md`](DECISIONS.md) 記一句理由。

> `last_reviewed` 只負責「這次不用再提醒」，Skipped 表才負責「不失憶」。**兩件事缺一不可**——只推進標記卻不記理由，日後想回頭查「當初為什麼跳過」會查無所獲。

macOS 專屬的 commit 一律屬於「不採用」，但仍要記進 Skipped 表，理由寫「macOS-only，本 fork 已移除該平台」。

<!-- sync-points:start -->
```json
{
  "repo": "aqua5230/usage",
  "branches": {
    "main": {
      "last_reviewed": "73b71d4",
      "last_merged": "bc28b5a",
      "note": "審視至上游 v0.29.18；移植離線價目表修正、zh-TW 簡體字修正與兩條 i18n 檢查概念，其餘逐筆理由見 Skipped"
    }
  }
}
```
<!-- sync-points:end -->

## 自動分流：哪些 commit 不需要人看

上游幾乎每天 commit，而且多數與本 fork 無關——`chore: sync AI updates` 只動 `ai_updates.json`（本 fork 已移除該功能），macOS 專屬修正只動 `menubar.py`、`panel_window_state.py` 之類本 fork 沒有的檔案。若全部照列，真正該看的 commit 會被埋掉，而**一份沒人看的報告等於沒有報告**。

檢查器會逐筆查該 commit 動到哪些檔案，並依這條規則分流：

> **改動的每一個檔案都在「純資料同步」清單裡** → 歸為「沒有可移植的概念」，只有這一類才自動略過。

- **「本 fork 沒有這個檔案」不是略過的理由。** macOS 專屬的修正確實無法 cherry-pick，但它背後的推理常常同樣適用於 Windows——而移植推理正是這個 fork 存在的目的。這類 commit 會單獨列成「需要判斷是否值得移植」，附上它動到的路徑，**要人看，不自動略過**。
- **為什麼「新增」永遠不自動略過**：新增的檔案在本 fork 同樣不存在，但那正是「上游長出新功能」的樣子。
- **查詢失敗時一律當成要人看**。網路或 API 出問題不能靜默升級成「可忽略」。
- **超過 40 個未審視 commit 就整批交給人**。落後那麼多本來就該人工處理，不值得為此打幾百次 API。
- 判定用的是**檔案是否存在於本 fork**，不是寫死的路徑清單——清單會過期，這個規則會自己跟著 repo 變。

被歸為「不影響」的 commit 仍會列在報告的摺疊區塊裡，附上它動到的路徑，並給出可直接推進的 `last_reviewed` SHA。**不是隱藏，是分流**：推進標記還是人來做，只是不必為每一筆寫理由。

只有「需要人工審視」那一組非空時，workflow 才會開／更新 issue。

## Skipped（審視後未採用）

| 分支 | Commit | 標題 | 審視日期 | 不採用理由 |
|---|---|---|---|---|
| main | `86bde4a` | refactor(menubar): 第八刀——_refresh_in_background 抽成 menubar_refresh | 2026-08-08 | 概念（檔案觸頂就把內聚的一塊抽成葉模組，而不是抬高上限）本 fork 已是既有做法，寫在 `scripts/check_file_size.py` 的錯誤訊息裡並實際執行過（v0.37.2 把 `on_closing` 搬進 `panels/window_visibility.py`）；被重構的 `menubar.py` 本 fork 沒有。 |
| main | `1fd5235` | chore: release v0.29.17 | 2026-08-08 | 純上游版號與 CHANGELOG；本 fork 版號獨立（D-05）。 |
| main | `57f207b` | fix(panels): 面板高度在 974 與 1004 之間反覆跳動 | 2026-08-08 | 根因是 `NSUserDefaults` 回傳 `NSDictionary` 而 `isinstance(x, dict)` 為 False，存下的實測高度被丟棄。本 fork 的 `_content_height` 只存在記憶體（`wintray.py`），不經任何持久化字典，也沒有「永遠不回報高度」的面板——`panel_html()` 一律注入回報腳本，機制不存在。 |
| main | `73b71d4` | chore: release v0.29.18 | 2026-08-08 | 同 `1fd5235`。 |
| main | `9f7a155` | feat(report,tui): 顯示 Claude Code 自動產生的對話標題 | 2026-08-02 | 屬報告與 TUI 的新呈現能力；目前優先完成 Phase A 的資料修復閉環，不在這次上游維護中擴張報告 schema 與 snapshot。 |
| main | `5a8bbd7` | chore: release v0.29.11 | 2026-08-02 | 純上游版號、CHANGELOG 與本 fork 已移除的 README 語言；本 fork 版號獨立（D-05）。 |
| main | `f4338e5` | fix(tests): 修 mypy 在測試檔上的 11 個錯誤 | 2026-08-02 | 修的是上游當時的測試型別錯誤；本 fork 的 mypy gate 已全綠，沒有對應缺陷。 |
| main | `97ed52a` | docs: cut CLAUDE.md to what the repo cannot tell you itself | 2026-08-02 | 與 `9be2ddf` 同一概念；本 fork 的模組導覽仍和 README 專案架構互相引用，不能單獨裁掉。 |
| main | `cb5799d` | feat(talent-market): 角色卡一律顯示啟動，不再分兩步安裝 | 2026-08-02 | 本 fork 同時管理 Claude、Codex、Cursor 的安裝、drift 與還原；保留明確的安裝／啟動兩步，避免一次點擊隱含跨工具寫檔。 |
| main | `efc2691` | chore: release v0.29.12 | 2026-08-02 | 純上游版號與 CHANGELOG；本 fork 版號獨立。 |
| main | `c1f35c8` | chore: 同步 uv.lock 到 v0.29.12 | 2026-08-02 | 只同步上游 root package 版號；本 fork 的 lock 與 v0.35.0 已一致。 |
| main | `3daba5f` | fix(setup,hooks): 讀不出來或不是自己的設定就停手 | 2026-08-02 | 等價保護已存在：本 fork 對 JSON／TOML／UTF-8 讀取失敗會略過，且只修復 agentdeck 擁有的 hook；現有 ownership 與 unreadable 測試覆蓋。 |
| main | `4d34ee5` | chore: release v0.29.13 | 2026-08-02 | 純上游版號、lock 與 CHANGELOG；本 fork 版號獨立。 |
| main | `a801c3a` | test(jsonl-utils,time-utils): 補共用底層模組直接單元測試 | 2026-08-02 | 上游的 `jsonl_utils.py` 本 fork 不存在；`time_utils` 目前由消費端測試覆蓋，不能原樣搬入兩份不存在／不同結構的測試。 |
| main | `3bcfb79` | refactor(menubar): 抽出 macOS 通知橋接 | 2026-08-02 | macOS-only；本 fork 已移除 `menubar.py` 與 Objective-C 通知橋接。 |
| main | `30bb4b0` | fix(panel): 面板位置改用頂邊當錨點 | 2026-08-02 | 修的是 macOS `NSPanel` 座標；Windows 使用工作區座標、持久化頂左位置並已有 clamp／hide-show 測試。 |
| main | `a5c8391` | fix(tests): 面板位置測試改為函式內匯入 menubar | 2026-08-02 | 只修 macOS 測試在 Windows 匯入 `menubar` 的問題；本 fork 沒有該測試或模組。 |
| main | `6fccf63` | fix(panel): 開啟時使用上次實測高度 | 2026-08-02 | 上游修的是 `NSPanel`；Windows 已以 `_content_height` 保存實測高度，切換面板也刻意沿用並有回歸測試。 |
| main | `de40632` | chore: release v0.29.14 | 2026-08-02 | 純上游版號、lock 與 CHANGELOG；本 fork 版號獨立。 |
| main | `12e476d` | feat(cache): 快取損毀先隔離再刪 | 2026-08-02 | 概念有價值但會同時改三種 cache 的生命週期與隱私留存；排入 Phase A／D 設計，不在追蹤 issue 中直接新增持久化 `.corrupt` 證據。 |
| main | `886a666` | chore(scripts): 新增 install_local.sh | 2026-08-02 | POSIX-only；本 fork 是 Windows-first，正式安裝產物為 PyInstaller ZIP。 |
| main | `f9e1576` | fix(doctor): 健檢報告分層 | 2026-08-02 | 本 fork 的 `doctor` 已由共享 `ProviderHealth` 提供狀態、原因與下一步；直接套用上游文字層級會繞過共享模型。 |
| main | `a4550c7` | fix(tests): wintray 測試寫入真實 preferences | 2026-08-02 | 本 fork 對應測試已用 `tmp_path` 與 monkeypatch 隔離 preferences；完整測試未寫入真實設定。 |
| main | `5922a67` | fix(scripts): 文件同步納入簡中、日文、韓文 README | 2026-08-02 | 本 fork 只維護繁中／英文雙語（D-11），其他三份 README 已移除。 |
| main | `d074018` | chore: release v0.29.15 | 2026-08-02 | 純上游版號與 CHANGELOG；本 fork 版號獨立。 |
| main | `fc098c5` | chore: 同步 uv.lock 到 v0.29.15 | 2026-08-02 | 只同步上游 root package 版號；本 fork lock 已獨立維護。 |
| main | `3942090` | feat: 日誌輪替與 doctor 機器可讀輸出 | 2026-08-02 | `doctor --json` 是 Phase B 的正式 schema 工作，必須先完成 redaction 與相容性契約；不直接搬入尚未承諾 schema 的上游版本。日誌輪替亦需先定 Windows 路徑與隱私政策。 |
| main | `81d5b24` | fix(tests): 隔離 ~/Library/Logs/usage | 2026-08-02 | macOS-only 路徑，且本 fork 未採用該上游日誌功能。 |
| main | `32b8908` | docs: 記錄測試日誌 fixture 不可移除 | 2026-08-02 | 文件只描述未採用的 macOS 日誌 fixture，對本 fork 不成立。 |
| main | `2328b5e` | refactor(menubar): 抽出 switchPanel_ 選單樣板 | 2026-08-02 | macOS `menubar.py` 重構；Windows 功能表由 HTML／系統匣各自的既有實作負責。 |
| main | `33641bc` | chore: release v0.29.16 | 2026-08-02 | 純上游版號、lock 與 CHANGELOG；本 fork 版號獨立。 |
| main | `9be2ddf` | docs: trim CLAUDE.md module map to gotchas only | 2026-07-31 | 只改上游的 `CLAUDE.md`。概念（模組表只留陷阱、不重複程式碼講得清楚的事）可移植，但本 fork 的模組表剛被 README 的「專案架構」章節引用為導覽入口，現在砍掉會讓兩邊對不上。留待日後與該章節一起重整。 |
| main | `ece46e2` | refactor: move menubar chrome helpers into menubar_chrome.py | 2026-07-31 | 拆 `menubar.py`（本 fork 沒有），**同時調降 `check_file_size.py` 的上限**——這正是 `8d26748` 那條政策在運作，是採用該概念的佐證。上游正往「小葉模組」收斂，而本 fork 從一開始就沒有那顆巨石。 |
| main | `be4e4ac` | refactor: move state constructors into menubar_state.py | 2026-07-31 | 動到 `menubar_state.py`（本 fork 有同名檔案），但內容是把上游 `menubar.py` 裡的 macOS 狀態建構子搬出來——本 fork 從未有那顆巨石，這些建構子本來就在各自的模組裡。與 D-07 同一類：上游在往本 fork 已有的結構靠。 |
| main | `ec24f50` | chore: release v0.29.10 | 2026-07-31 | 純版號與 CHANGELOG。本 fork 版號獨立（D-05）。 |
| main | `616d48f` | fix: stop the talent market panel from collapsing to its floor height | 2026-07-30 | 只改 `panels/__init__.py`、`panels/web_panel.py`（本 fork 已刪除的 macOS 面板註冊表與 WKWebView 面板）。同類問題在 Windows 由 `PANEL_HEIGHTS["talent_market"]` 與 `clamp_content_height` 處理，並有 `test_every_panel_has_a_registered_height` 守著。 |
| main | `4dbf916` | feat: let the panel float free of the menu bar icon | 2026-07-30 | macOS 專屬（NSPopover → NSPanel）。**且上游此舉是放棄貼齊選單列圖示、改為可拖曳並記住位置的浮動面板——Windows 早就是這個行為**（`_place_window` + `agentdeck.windowPosition`）。上游是往 Windows 的做法收斂，本 fork 無事可做。 |
| main | `c2af3a9` | fix: dismissing the panel menu no longer throws the panel away | 2026-07-30 | 只改 `menubar.py`（已刪除）。Windows 的面板選單是 `JS_SHIM` 自製的 overlay，不共用這條路徑。 |
| main | `d2d36c8` | chore: release v0.29.9 | 2026-07-30 | 純版號與 CHANGELOG，外加更新本 fork 已刪除的 `README.ja/ko/zh-CN`。本 fork 版號獨立（見 `docs/DECISIONS.md` D-05）。 |
| main | `e94cd4d` | fix: narrow NSUserDefaults for mypy's Windows platform check | 2026-07-30 | 只改 `panel_window_state.py`——那是上游在 `4dbf916` 新建的檔案，本 fork 沒有；且 `NSUserDefaults` 是 macOS API。 |
