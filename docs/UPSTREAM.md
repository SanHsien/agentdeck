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
      "last_reviewed": "2a5a430",
      "last_merged": "2a5a430",
      "note": "v0.29.8 的兩個 Windows 修復已於 93550e0 合併；v0.29.9 的 5 筆全數審視後未採用，見下方 Skipped"
    }
  }
}
```
<!-- sync-points:end -->

## 自動分流：哪些 commit 不需要人看

上游幾乎每天 commit，而且多數與本 fork 無關——`chore: sync AI updates` 只動 `ai_updates.json`（本 fork 已移除該功能），macOS 專屬修正只動 `menubar.py`、`panel_window_state.py` 之類本 fork 沒有的檔案。若全部照列，真正該看的 commit 會被埋掉，而**一份沒人看的報告等於沒有報告**。

檢查器會逐筆查該 commit 動到哪些檔案，並依這條規則分流：

> **改動的每一個檔案在本 fork 都不存在，而且沒有任何一個是新增的** → 歸為「不影響本 fork」。

- **為什麼「新增」永遠不自動略過**：新增的檔案在本 fork 同樣不存在，但那正是「上游長出新功能」的樣子。本 fork 的目的是把功能搬過來、不是接受落差，所以新增一律要人看。
- **查詢失敗時一律當成要人看**。網路或 API 出問題不能靜默升級成「可忽略」。
- **超過 40 個未審視 commit 就整批交給人**。落後那麼多本來就該人工處理，不值得為此打幾百次 API。
- 判定用的是**檔案是否存在於本 fork**，不是寫死的路徑清單——清單會過期，這個規則會自己跟著 repo 變。

被歸為「不影響」的 commit 仍會列在報告的摺疊區塊裡，附上它動到的路徑，並給出可直接推進的 `last_reviewed` SHA。**不是隱藏，是分流**：推進標記還是人來做，只是不必為每一筆寫理由。

只有「需要人工審視」那一組非空時，workflow 才會開／更新 issue。

## Skipped（審視後未採用）

| 分支 | Commit | 標題 | 審視日期 | 不採用理由 |
|---|---|---|---|---|
| main | `616d48f` | fix: stop the talent market panel from collapsing to its floor height | 2026-07-30 | 只改 `panels/__init__.py`、`panels/web_panel.py`（本 fork 已刪除的 macOS 面板註冊表與 WKWebView 面板）。同類問題在 Windows 由 `PANEL_HEIGHTS["talent_market"]` 與 `clamp_content_height` 處理，並有 `test_every_panel_has_a_registered_height` 守著。 |
| main | `4dbf916` | feat: let the panel float free of the menu bar icon | 2026-07-30 | macOS 專屬（NSPopover → NSPanel）。**且上游此舉是放棄貼齊選單列圖示、改為可拖曳並記住位置的浮動面板——Windows 早就是這個行為**（`_place_window` + `agentdeck.windowPosition`）。上游是往 Windows 的做法收斂，本 fork 無事可做。 |
| main | `c2af3a9` | fix: dismissing the panel menu no longer throws the panel away | 2026-07-30 | 只改 `menubar.py`（已刪除）。Windows 的面板選單是 `JS_SHIM` 自製的 overlay，不共用這條路徑。 |
| main | `d2d36c8` | chore: release v0.29.9 | 2026-07-30 | 純版號與 CHANGELOG，外加更新本 fork 已刪除的 `README.ja/ko/zh-CN`。本 fork 版號獨立（見 `docs/DECISIONS.md` D-05）。 |
| main | `e94cd4d` | fix: narrow NSUserDefaults for mypy's Windows platform check | 2026-07-30 | 只改 `panel_window_state.py`——那是上游在 `4dbf916` 新建的檔案，本 fork 沒有；且 `NSUserDefaults` 是 macOS API。 |
