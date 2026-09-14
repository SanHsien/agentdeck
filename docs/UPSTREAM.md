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
      "last_reviewed": "d42496bd2445b604a3a20517dbb41b0b257e6564",
      "last_merged": "2a1996edb2f2d902f83572ca0403fc9f9ebefbec",
      "note": "2026-09-14 審視 2cdf3a0..d42496b 共 6 筆：採用 2a1996e 啟動時黑窗連閃（本 fork 17 個 subprocess 呼叫點只有 1 個帶 CREATE_NO_WINDOW；改成 creation_flags() 回傳整數旗標而非上游的 kwargs dict，因為 ** 展開過不了 subprocess.pyi 多載；兩支安裝到使用者環境的 hook 各自內嵌一份；AST 掃描測試釘住每個呼叫點）。連帶修掉 update_hook() 不換新 forwarder 副本，並把剪貼簿寫入下沉成 win_clipboard.py 以守住 wintray.py 的行數上限。d42496b 報表改版列後續（同 ui/ 分岔判準）；e24a5e2 發版、3 筆 ai_updates.json 不適用。逐筆見 2026-09-14 段落；更早的判定見 2026-09-12／09-10／09-08 段落。"
    }
  },
  "tickets": {
    "reviewed_pr_through": 137,
    "reviewed_issue_through": 130,
    "reviewed_date": "2026-09-14",
    "note": "以 --state all 查過。PR #136 是 2026-09-14 採用的黑窗修正、#137 是列後續的報表改版；#134／#135 仍開著，是高 DPI 那條線的後續，與 2d606b1 綁在一起列後續。#131／#132／#133 見 2026-09-12 段落。issue 仍停在 #130（250% 縮放下面板開到螢幕邊緣，同高 DPI 線，本 fork 是否重現要自己實機驗）；#129 是 CLAUDE_CONFIG_DIR，對應 a2cd93e，本 fork 已部分支援，集中化列後續。"
  }
}
```
<!-- sync-points:end -->

## 2026-09-14：`2cdf3a0..d42496b` 共 6 筆，`last_reviewed` 推到 `d42496b`

issue #21 列 3 筆需要人工審視，另有 3 筆只同步 `ai_updates.json`。

### 採用：啟動時的黑窗連閃（`2a1996e`）

這是 tray app，自己沒有主控台，所以每一個跑主控台程式的 `subprocess` 呼叫（`git`、`claude`、
`clip`、Antigravity CLI）在 Windows 上都會彈一個黑窗，存活多久閃多久。一次專案名稱解析或一次額度
輪詢就是一次閃爍，累積起來是整個工作階段的干擾，面板還可能被蓋在後面。

**本 fork 實查**：17 個呼叫點只有 `autoresume_scheduler.py` 一個帶了 `CREATE_NO_WINDOW`，其餘 16 個
都沒有——缺陷完全成立，而且打在本 fork 唯一支援的平台上。

**移植方式與上游不同的地方**：上游提供 `hidden_console_kwargs()` 回傳 dict 再 `**` 展開；本 fork 改成
`creation_flags()` 直接回傳整數旗標，呼叫端寫 `creationflags=creation_flags()`。理由是 `**{...}`
過不了 `subprocess.pyi` 的多載檢查（mypy 報 12 個錯），而 `creationflags=0` 在每個平台都合法——
只有**非零值**是 Windows 專屬。既有那個手寫 `getattr(subprocess, "CREATE_NO_WINDOW", 0)` 也一併收斂
到同一個來源。

**兩支安裝到使用者環境的 hook 各自內嵌一份**（`usage_session_resume.py`、
`usage_statusline_forwarder.py`）：它們由系統 Python 執行、看不到專案路徑，不能 import。這與 i18n
locale 對照表在那些檔案裡重複的理由相同。

**擋住回頭路的是 AST 掃描而不是註解**：`tests/test_subprocess_hidden_console.py` 走訪 tray 行程搆得到的
每個 `.py`，要求每個 `subprocess.run`／`Popen` 的 `creationflags` 來自那兩個 helper 之一——寫死
`0x08000000` 也不算，因為那在下一次重構時就是同一個缺陷。反向測試釘住「裸呼叫會被抓到」，另外兩條
釘住兩份內嵌副本與共用版本行為一致。

**連帶修掉的一個既有缺口**：`update_hook()` 只換新狀態列那份副本，不換 forwarder，所以對 forwarder 的
修正永遠不會進到已經安裝的人手上。已補上「有裝才換新」。四個受影響的版號一起升：`HOOK_VERSION` 與
`usage_statusline.__version__` 到 1.2、forwarder 到 1.1、`RESUME_HOOK_VERSION` 與
`usage_session_resume.__version__` 到 1.7。

**連帶的切分**：加完之後 `wintray.py` 超過 1816 行上限，依該檔政策把剪貼簿寫入下沉成
`win_clipboard.py`（`clip.exe` 讀 UTF-16LE，這個編碼不是隨手寫的），`wintray.py` 降到 1813 行，
上限一併調降。

### 逐筆判定

| Commit | 判定 | 理由 |
| --- | --- | --- |
| `2a1996e` 啟動黑窗連閃 | **採用** | 見上；本 fork 17 個呼叫點裡 16 個重現得到 |
| `d42496b` 報表改版（網頁內選日期、分組收合、專案展開） | 後續 | 動 `analyzer/reporter.py`、`i18n.json` 與三份 snapshot（每份 +1200 行）；同 `0aef437`／`42d6ad1`／`c4f0edf` 的判準，`ui/` 與報表產生鏈已與上游分岔，需要獨立的渲染與列印驗收 |
| `e24a5e2` v0.30.14 | 不適用 | 上游發版 chore，本 fork 自行版控 |
| `b501575`／`65154f6`／`327c9d3` | 不適用 | 三筆都只有 `ai_updates.json`，符合 2026-09-08 段落的整類判準 |

PR／issue 兩軸：以 `--state all` 查過，PR 推進到 `#137`、issue 仍是 `#130`。`#136` 就是上面採用的那筆，
`#137` 是列後續的報表改版。

### 審視期間上游又推進了，標記刻意停在有證據的地方

開始審的時候上游 tip 是 `d42496b`；寫完這一段時已經多出 18 筆（`153a876..c8aa485`），內容是報表改版那
條線（`24d2130` 的 merge 加上七、八筆 report 修正與視覺調整）、`d1ea2a7`／`153a876` 的永久用量小計快照、
`9c82430` v0.30.15，以及數筆 `ai_updates.json` 同步。

`last_reviewed` 因此停在 `d42496b` 而不是 tip：那 18 筆沒有逐筆讀過，推上去等於宣稱看過。下一次排程
檢查會把它們列出來，issue 因此仍會有內容，那是正確狀態不是漏做（同 D-30 的判準）。報表那條線大機率
併入既有的「`ui/` 已分岔、需要獨立渲染與列印驗收」判定，但快照那兩筆是新功能，要單獨評估。

**尚未做 Windows 實機驗收**：黑窗屬於「CI 看不到」那一類，CLAUDE.md 對 tray 改動的要求是自動測試與實機
驗收分開寫。這一輪只有自動測試；下次開 tray 時看一眼專案切換與額度輪詢還會不會閃窗即可。

## 2026-09-12：`0bd03fb..2cdf3a0` 共 19 筆，`last_reviewed` 推到 `2cdf3a0`

issue #20 列了 8 筆；開審時上游又推進 11 筆（含 v0.30.12、v0.30.13 兩次發版），所以照 2026-09-10
的做法以上游 `main` 的實際 tip `2cdf3a0` 為準，兩批一起判。

### 採用一：狀態列在單位邊界顯示不存在的單位（`45b27ee`）

`fmt_tokens` 的門檻寫成單位本身（`>= 1_000_000` 才進位成 `M`），但 `k` 那一支用 `:.0f`
四捨五入，所以 999,500～999,999 會印成 **`1000k`**——一個不存在的單位。本 fork 的
`usage_statusline.py` 與 `usage_statusline_agy.py` 都有同一段，實測仍會重現。

改法照上游：門檻改成**進位邊界**（`999_500` 進 `M`、`999_950_000` 進 `B`），並補上 `B` 那一支。
本 fork 沒有 `usage_statusline_grok.py`，該檔略過。

**連帶一件事**：`setup_hook.needs_update()` 是拿 `HOOK_VERSION` 比對**已安裝副本**的
`__version__`，所以只改檔案不升版號，修正永遠不會進到 `~/.claude` 的那份。這正是上游同批
`144ecac` 在修的東西。`usage_statusline.py` 的 `__version__` 與 `HOOK_VERSION` 一起升到 `1.1`，
並補一條契約測試把四組配對（statusline／resume／terse／terse reminder）全部釘住——原本沒有任何
測試防止兩者分家。

### 採用二：精簡模式壓過使用者明確要求的詳細解說（`93b2f19`）

兩處：

- **每則訊息都會注入的提醒句**沒有讓步條款，於是它蓋過使用者當下「請詳細說明」的要求。
  zh-TW 與 en 都補上「使用者明確要求詳細解說時，以使用者當下的要求為準」。
- **開場指示**裡「允許用短句、片語甚至不成句的斷句表達」會把解釋類回答壓成碎片。中文版整句移除；
  英文版上游改完留下一個以小寫 `filler` 開頭的破碎句子，本 fork 不照抄，改寫成
  `Cut filler (...) and pleasantries (...).`——移植的是做法不是 diff。

`usage_terse_reminder.py` 自帶的預設文字與 `i18n.json` 同步，並補一條測試比對兩者一致：hook 在 venv
外跑、帶著自己的副本，兩份文字原本會無聲分家。版號與 `TERSE_REMINDER_HOOK_VERSION` 一起升到 `1.2`。

### 採用三：系統匣提示超過 Windows 上限會卡住面板更新（`8eacc3b`）

`Shell_NotifyIcon` 的 `szTip` 上限是 128 個 WCHAR（含結尾），pystray 超過就丟 `ValueError`，
而那個例外落在更新路徑裡——症狀不是提示被截斷，是**面板不再更新**。本 fork 的 `build_tooltip`
沒有任何長度處理，四列供應商加上本地化的視窗標題就會超過。照上游截到 127 並補上省略號。

### 逐筆判定

| Commit | 判定 | 理由 |
|---|---|---|
| `45b27ee` 狀態列單位邊界 | **採用** | 見上；本 fork 兩個狀態列檔都重現得到。**已知缺口**：`usage_statusline_agy.py` 沒有版號與自我修復比對，這個修正只會進到新安裝的副本，理由與觸發條件見 DECISIONS D-31 |
| `93b2f19` 精簡模式兩處 | **採用** | 見上；提醒句與開場指示都照本 fork 的雙語改寫 |
| `8eacc3b` 系統匣提示截斷 | **採用** | 見上；本 fork 的 `wintray.py` 有同樣缺陷 |
| `144ecac` hook 版號 | **採用（觀念）** | 上游升的是它自己那四個版號；本 fork 只在這次真的改到的檔案上升版，並把「常數與檔案版號必須一致」做成測試 |
| `42d6ad1` 週趨勢長條圖滑鼠提示 | 後續 | 動 `ui/html_report.py` 與三份 snapshot；同 `0aef437` 的判準，`ui/` 已與上游分岔，需要獨立的渲染與列印驗收 |
| `c4f0edf` 洞察卡片改方角淡色 | 後續 | 同上，動 `ui/report_styles.py` 與 snapshot |
| `2d606b1` 高 DPI 面板位置與跨螢幕記憶 | 後續 | 真正的 Windows 缺陷，但上游改的是它新加的 `wintray/app.py` 與 `panels/panel_scale.py`，本 fork 的系統匣是自己的頂層 `wintray.py`，沒有那兩個檔。要移植是概念重寫＋多螢幕實機驗收，不在同步裡順手做 |
| `a2cd93e` 跟著 `CLAUDE_CONFIG_DIR` 找設定資料夾 | 後續 | 本 fork 的 `adapters/claude.py` 已經讀這個環境變數；上游那筆是把它集中成 `loaders/claude_paths.py` 並套進 persona／subscription／installer 等六處，本 fork 對應模組已分岔，要逐處確認 |
| `aa07018` 下架 AI 人才市場與 AI 圓桌討論 | 不適用 | 上游的產品方向。本 fork 仍出貨這兩個功能（`panels/registry.py` 的人才市場面板、`council/`），跟進等於自己砍掉在用的功能 |
| `a0fbdad` 首張功能卡拿掉橘色軌 | 不適用 | 只動上游行銷官網 `docs/index.html` |
| `85c854c`／`6df8c22` 上游 `CLAUDE.md` | 不適用 | 上游那份是 macOS 導向、給上游維護者看的；本 fork 的 `CLAUDE.md` 是自己維護的 Windows-only 版本 |
| `061cda7`／`d680bc7` 測試修正 | 不適用 | 修的是上游新檔 `tests/test_claude_paths.py` 與 `tests/test_menubar.py`，本 fork 沒有這兩個檔 |
| `c21d84f`／`ab84c0b` v0.30.12／v0.30.13 | 不適用 | 上游發版 chore，本 fork 自行版控 |
| `2cdf3a0`／`ef2012f`／`9ea34fe`／`37559f4` | 不適用 | 四筆都只有 `ai_updates.json`，符合 2026-09-08 段落的整類判準 |

PR／issue 兩軸：以 `--state all` 查過，PR 推進到 `#135`、issue 推進到 `#130`。

- PR `#131`／`#132`／`#133` 已合併，就是上面判定過的三筆（高 DPI 列後續、提示截斷已採用、hook 版號
  採用觀念）。
- PR `#134`／`#135` **仍開著**，是同一條高 DPI 線的後續（面板位置改存實體像素、縮放下限改以實際像素
  計算）。和 `2d606b1` 綁在一起列後續：等那條線在上游收斂，再一次評估本 fork 的 `wintray.py` 要怎麼改。
- issue `#129`「CLAUDE_CONFIG_DIR is not respected」對應 `a2cd93e`，本 fork 已部分支援，集中化列後續。
- issue `#130`「面板在 250% 縮放下開到螢幕邊緣看不到」同屬高 DPI 線。**這一條要自己實機驗**：本 fork
  的面板定位是另一套程式，是否重現未知，列為後續時的第一個檢查點。

## 2026-09-10：`6a3ad53..0bd03fb` 共 22 筆，水位推到 `0bd03fb`

issue #19 當時列了 13 筆；開始審的時候上游又推進了 9 筆，所以這一輪以上游 `main` 的
實際 tip `0bd03fb` 為準，兩批合併判定，免得下一輪才發現清單不完整。

### 新採用：Grok 花費恆為 `$0.00`（`784eeb9`＋`7a78e64`）

Grok CLI 把每次請求的花費寫在各 session 的 `updates.jsonl`（`costUsdTicks`，1 tick＝
`1e-10` 美元），不在本 fork 原本讀的 `unified.jsonl`——所以 Grok 那一列的花費永遠是
`$0.00`。`784eeb9` 改為一併讀 `~/.grok/sessions/*/updates.jsonl` 把花費掛回對應 entry；
`7a78e64` 再處理 `unified.jsonl` 只保留一段滾動視窗的問題：視窗外的舊請求原本直接丟掉，
現在從 `updates.jsonl` 補回成獨立 entry（上游實測花費由 $13.17 補足到 $23.17）。

**移植方式是可驗證的機械改寫，不是手寫**：本 fork 的 `providers/grok_loader.py` 與上游
這兩筆之前的版本（`47b0a64`）逐字比對，差異只有四行 import 路徑（`jsonl_limits`、
`time_utils` 在本 fork 位於根目錄，`history_loader` 位於 `providers/`）。把同一套改寫套在
上游改動前的版本，得到的檔案與本 fork 現有檔案逐字相同，因此套在改動後的版本就是正確移植；
`tests/test_grok_loader.py` 同樣只差 `from providers import grok_loader` 一行。

### 新採用：離線價目表補上 Codex 與新 Claude 模型（`47b0a64`）

本 fork 會讀 Codex 的本機用量，但 `_fallback_pricing()` 裡原本一個 `gpt-*` 都沒有——網路
價目表取不到時，Codex 花費只能算成 0。補上 `claude-mythos-5-1`、`gpt-6-astra`、
`gpt-5.6-terra`／`sol`／`luna`、`gpt-5.5`、`gpt-5.4-mini` 七筆，數值取自上游該 commit。

### 已涵蓋：`fde1c0c` 通知門檻只留 90%

上游把預設門檻由 `[50, 90]` 改回 `[90]`。本 fork 的 `QuotaNotifier.__init__` 與
`_quota_notification_thresholds()` 預設早就是 `[90.0]`，沒有可移植的差異。

### 其餘逐筆

| Commit | 判定 | 理由 |
|---|---|---|
| `0aef437` 報表視覺重整與亮暗切換 | 後續 | 動 `ui/html_report.py`、`ui/report_styles.py`、`ui/report_scripts.py`、`i18n.json` 與三份 snapshot；同 2026-08-31 起的判準，`ui/` 已與上游分岔，需要獨立的渲染與列印驗收 |
| `d41e983`／`24e2b22`／`43409c4`／`eb09407`／`7716b04`／`4c3020b` | 不適用 | 六筆檔案集合都只有 `ai_updates.json`，符合 2026-09-08 段落的整類判準 |
| `ea2c3a0`／`b2eb5aa`／`af7f72c`／`95f2b97`／`44dc3c0` | 不適用 | 只動上游行銷官網 `docs/index.html` |
| `55db9f0` | 不適用 | 官網的 `robots.txt`、`sitemap.xml` 與 13 張面板預覽頁；本 fork 只出貨 4 款面板，也沒有這個官網 |
| `8543bd3` | 不適用 | 上游五語 README 與官網首屏示意圖；本 fork 的 README 是自己維護的雙語版本 |
| `0337ea9`／`8749009`／`7c8d70c` | 不適用 | 只換上游官網的截圖與品牌圖檔 |
| `0bd03fb`（PR #128） | 不適用 | 只動上游的 `uv.lock`（ruff 0.16.5→0.16.6）；本 fork 自行維護 `uv.lock` |

### 驗證

- 聚焦測試：`tests/test_grok_loader.py`、`test_grok_panel_contract.py`、`test_menubar_grok.py`、
  `test_grok_quota_probe.py`、`test_pricing.py` → 82 passed。
- 完整閘門：`pwsh -NoProfile -File tools/dev_check.ps1` → 1584 passed、8 skipped、exit 0。

跑閘門前要注意環境：`dev_check.ps1` 在本機會把 `UV_PROJECT_ENVIRONMENT` 設成
`C:\tmp\agentdeck`。直接執行 `uv run` 而沒帶這個變數，會在 repo 裡另建一個空的 `.venv`，
測試會因為找不到 pytest 而失敗——那是環境問題，不是程式碼問題。

## 2026-09-08：issue #19 的 58 筆判完，水位推到 `6a3ad53`

接續同檔 2026-09-06 段落。那次只把 `e32c2f6` 已經併入的 6 筆補上出處，其餘 44 筆沒有判定，
`last_reviewed` 因此刻意停在 `1312289`。這次把目前累積的 58 筆全部判完。

### 新採用：`d665d67` 的 token 單位進位半部

`_fmt_tokens()` 的門檻寫在**整數單位本身**，但格式化會先四捨五入：`999_950 / 1_000_000`
是 `0.99995`，用 `.1f` 印出來是 `1.0`——可是 `999_950 >= 1_000_000` 為假，所以走 K 那一支，
印成 **`1000.0K`**，一個不存在的單位。十億級同理，`.2f` 的進位點在 `999_950_000`。

本 fork 實測重現（修補前）：

```text
999949     -> 999.9K      999949999  -> 999.9M
999950     -> 1000.0K     999950000  -> 1000.0M   ← 兩個不存在的單位
```

門檻改到四捨五入後真正會進位的點。`tests/test_ui_tables.py` 補四個邊界案例，
突變驗證：把門檻改回 `1_000_000`／`1_000_000_000`，`999950-1.0M` 與 `999950000-1.00B`
兩例轉紅；還原後 37 passed。

同一筆的另一半（移除每日折線圖、`ui/report_charts.py` 減 45 行、三份 HTML snapshot）
屬報表視覺改版，照 2026-08-31 起的既有判準列為後續。

### `chore: sync AI updates` ×25：整類不適用

58 筆裡有 25 筆是這個標題。以 `git diff-tree` 核對全部 25 筆，檔案集合都只有
`ai_updates.json`——上游的自動資料同步，沒有可移植的概念。本 fork
2026-08-31 已把 `ai_updates` 歸為不適用，這裡沿用同一判準整類處置，不逐筆讀 diff。
判準：只要該 commit 的檔案集合僅有 `ai_updates.json`，就落在這一類；哪天它動到別的檔，
就不再適用整類處置。

### 其餘逐筆

| Commit | 判定 | 理由 |
|---|---|---|
| `1d9cd55` codeql-action group bump | 不適用 | 只動上游的 `codeql.yml`／`scorecard.yml`。本 fork 的工作流程與 Action 釘選自行維護，PR #124 同結論 |
| `2c6bb7b` rich 移到 py2app packages | 不適用 | py2app 是 macOS 打包路徑，正式產品不支援該平台 |
| `9666e57` 出貨前先跑打包好的 app | 不適用 | 同上，上游 macOS release CI |
| `9261121` v0.30.7、`710e3c8` v0.30.9、`18e785d` v0.30.10 | 不適用 | 上游發版 chore，本 fork 自行版控 |
| `afde801` 派工任務書不進版本庫 | 不適用 | 只動上游自己的 `.gitignore`，本 fork 沒有那些路徑 |
| `97bf233` 修 token 組成測試的 mypy 錯誤 | 不適用 | 只動 `tests/test_reporter_build_data.py`，那是 `91d9d2a` 帶進來的測試；該功能本 fork 列為後續，測試自然也不在樹上 |
| `91d9d2a`／`feb84cd`／`52f4750`／`d7a91de`／`cf1f116`／`d006828`／`e63e244` 報表功能與版面 | 後續 | 同 2026-08-31 判準：`ui/` 已與上游分岔，整批需要獨立的渲染與列印驗收，不在上游同步裡順手做 |
| `97d62e6` 的 Grok 接線與「燒掉成本」正名半部 | 後續 | 同上。該筆的**歷史保全半部已於 2026-09-06 採用**，見同檔該段 |
| `43fa739`／`6cad536`／`a9ea66e`／`1674ab1`／`3f33a31`／`d92bda0`／`3fdda7e`／`6a2ff55`／`e42350e`／`b026f4c` | 已判定 | 2026-09-04 那輪已逐筆處理，見同檔該段與 Skipped 表 |
| `69e2e12`／`2e99c86`／`c1d2749`／`30aac9c`／`9282a5b`／`1674ab1` Fable 半部／`97d62e6` 歷史保全半部 | 已採用 | 2026-09-06 補記出處，見同檔該段 |

### 水位

`last_reviewed` → `6a3ad53`（58 筆全部有判定）。`last_merged` 維持 `9282a5b`：
本輪新採用的 `d665d67` 在上游歷史裡比 `9282a5b` 舊，最新一筆有併入內容的仍是後者。

### 上游 ticket 水位

- PR #126 的 Antigravity TUI loader 已由 `e32c2f6` 採用，對應上游 `c1d2749`／`30aac9c`；
  `reviewed_pr_through` 推到 126。
- issue #127 是 macOS 面板失焦行為，上游基於常駐面板契約關閉；本 fork 是 Windows-only，
  沒有可移植工作，`reviewed_issue_through` 推到 127。

## 2026-09-06：補記 `e32c2f6` 採用了什麼——一筆沒有出處的提交

**這一節是補救，不是正常流程。** commit `e32c2f6`（「fix: reconcile usage data and model
updates」）動了 17 個檔並直接推上 `main`，但沒有寫出它從上游哪幾筆來、水位沒推、Skipped 表
沒補。**採用了上游程式碼卻不留出處，等於下一輪要重新判一次同樣的東西**，所以這裡把它逐 hunk
對回上游、補上出處。對應關係是從 diff 內容重建的，不是原提交自己聲明的，這一點必須寫明。

先修正一個我自己下錯的判斷：初次跑閘門是紅的（mypy、pytest 皆失敗），一度以為那個 commit
帶著壞掉的狀態推上去。實查後不是——`mypy .` 回 `Success: no issues found in 204 source files`，
pytest 的錯全是 `No module named 'PIL'` 與 `pystray`，本機 venv 少了 windows extra。照
`CLAUDE.md` 跑 `uv sync --frozen --group dev --extra windows` 之後閘門全綠（1571 passed、
8 skipped、exit 0）。程式碼沒問題，缺的只有紀錄。

### 逐 hunk 對回上游

| 落地的改動 | 對應上游 | 憑據 |
|---|---|---|
| `analyzer/reporter.py` 新增 `_normalize_project_tokens()`，把 `.git` 尾綴併回同一個專案；`project_resolver.py` 同步 | `69e2e12` fix(projects): bare repo worktree 讓同一個專案被拆成兩筆 | 兩檔都在該 commit 的檔案集合內，改的正是 bare repo 的 `.git` 尾綴 |
| `analyzer/reporter.py` schema 不符時不再整份清空，改為逐日搶救仍可解析的資料並記 warning；全數解析失敗才回空 | `97d62e6` feat(report) 的「堵住會清空使用者歷史的洞」半部 | 原本 `schema_version` 一對不上就 `return _empty_year_ledger()`——維護者替 ledger 加一個欄位，使用者下次啟動就失去整年 contribution 紀錄 |
| `i18n.json` 的 `burn_warning` 縮短並新增 `burn_warning_compact`；`state/menubar_state.py` 加 `reset_text_compact`；`panels/payload.py` 輸出 `resetTextCompact` | `2e99c86` fix(panels): 縮短配額警告文案，修面板五語言全被切掉 | 三個檔一起動，正是該 commit 的形狀 |
| `usage_cli.py` 的 `AGENT_LOADERS` 補 `antigravity`；`ui/tables.py` 的 `AGENT_SHORT`／`AGENT_LABEL` 補 `AGY`／`Antigravity` | `c1d2749`（PR #126）＋ `30aac9c` | 漏了 loader，互動式 dashboard 的 Antigravity 分頁會渲染成 "No data"，而 `report` 指令卻有資料——註解已寫在 `usage_cli.py` 呼叫點 |
| `pricing.py` 補 `claude-fable-5-1` 價格、`FALLBACK_PRICING_AS_OF` 推到 2026-09-06；`ui/tables.py` 的 `MODEL_SHORT` 補 `Fable 5.1` 與 `Opus 5` | `1674ab1` 的 Fable 5.1 半部 | 該 commit 的版本號誤配半部已於 2026-09-04 採用，價目表半部這次補齊 |
| `council/discussion_assets.py` 的 `ALLOWED_MODELS`＋`assets/windows/discussion.html` 下拉補 `gpt-6-astra` | `9282a5b` feat(discussion): 圓桌可選 Codex 新模型 Astra | 兩處同時加同一個 model id |

`usage_notifications.py` 把門檻判斷改寫成 list comprehension 這一 hunk **對不回上游任何一筆**：
行為與 2026-09-04 採用的 `b57e8e9` 相同，看起來是本地重構。列在這裡當作已知的未解釋改動，
下次有人動這個檔時不必再查一遍。

### 水位怎麼推

`last_merged` 推到 `9282a5b`（本輪實際併入內容的最後一筆）。`last_reviewed` **維持
`1312289` 不動**——issue #19 列的 50 筆裡，只有上表這 6 筆有可查證的判定，其餘沒有人寫下
結論。把 `last_reviewed` 推到 tip 會讓那些未審的 commit 永遠不再被提起，那正是這份文件
存在的理由。issue #19 因此仍會有內容，是正確狀態。

## 2026-09-04：issue #18 列出的 21 筆逐筆收斂

issue [#18](https://github.com/SanHsien/agentdeck/issues/18) 累積到 20 筆待審（外加後續補上的
`1312289`）。逐筆讀 diff 後的分佈：

```text
21 commits
  ├─ 採用：resume／terse／hooks 穩健性、Grok 週配額歸零、pricing 版本誤配、
  │        額度門檻通知、偏好檔測試隔離、Windows 登錄檔容錯、terse 禁止原文轉貼
  ├─ 結構上已涵蓋：3f8e289 的 ja／ko 誤判（本 fork 只有 zh-TW／en）、6a2ff55 的 ruff 下限
  └─ 不採用：上游 release chore、官網五語文案、HTML 報告視覺改版、macOS launchctl
```

三筆值得單獨說明：

**`1674ab1` 的 pricing 版本誤配**不是補價目表而已。原本的前綴比對會讓已經帶版本的查詢
（`claude-opus-4`）落到 `claude-opus-4-6` 的價格上——版本更長不代表是同一個模型的變體。
改法是：查詢本身結尾是數字時，候選鍵在前綴之後不得再接數字；另補 Bedrock 的 `-vN:N` 後綴正規化。

**`b57e8e9` 的門檻通知**有兩個獨立的 bug 疊在一起：`previous is None`（開機後第一次觀測）
直接跳過整個門檻迴圈，所以開機時額度已經很高不會提醒；而 `state.depleted = False` 寫在
每次觀測都會走到的分支，小幅波動就把耗盡狀態清掉。上游把前者改成「沒有前值時只看 `current`
是否已越過門檻」，後者移除——耗盡狀態只由 `reset`（跌幅超過 `RESET_DROP_PERCENT`）清除。

**`dca76d8` 的 hook 誤判**是本 fork 特別在意的一類：自我修復原本用子字串比對判斷某個 hook
指令是不是自己安裝的腳本，於是使用者自己放的 `usage-terse-mode-backup.py` 會被當成舊版**刪掉**。
改成要求 marker 後面緊接 `.py`、兩側是路徑分隔符／引號／空白。

**HTML 報告的視覺改版（`3f33a31`、`d92bda0`）列為後續**，與 2026-08-31 那批同樣的理由：
本 fork 的 `ui/report_styles.py`、`ui/html_report.py` 已與上游分岔，整批視覺改版需要獨立的
渲染與列印驗收，不在上游同步裡順手做。

## 2026-08-31：Claude Desktop 刷新／重置推估與上游 36 筆收斂

本輪先重新 fetch `origin`／`upstream`，逐筆讀完 `10be369..7cd04fc`、PR #118–#120、
issue #117／#121。取捨如下：

```text
36 commits
  ├─ 採用／部分採用：報告正確性、agy effort、hook 精準歸屬
  ├─ 已有等價修正：Grok 今日用量、Windows statusLine 鎖逾時
  ├─ 不適用：macOS menubar、上游 release、ai_updates、上游專屬測試
  └─ 後續候選：cache 健康度、Grok statusLine、報告呈現功能
```

同時處理 Claude Desktop 本機配額。`plan-usage-history.json` 只持久化百分比，不含 API 回傳的
`resets_at`；因此不越過「不呼叫 Anthropic usage API」邊界，而是從同一組織的本機歷史找出
額度下降點：5 小時視窗只在目前有使用量、且找得到仍有效的起點時推估；週視窗以最窄的重置
觀測區間定相位並每七天前推。兩者在 UI／TUI 都明標「約略」，且推估值不得啟動 window keeper。
0% 的 5 小時視窗不捏造重置時間，改顯示「下次使用 Claude 後開始計時」。

手動重整原本撞上背景 refresh lock 就直接 `return`。本輪採用先前上游 `25b0979` 的 bounded
trailing-refresh 概念：忙碌期間的多次要求合併成一次補跑，不搬入整套 Windows watcher。

報告只帶回三個可重現的數值正確性修正：甜甜圈分母改用報告總量並補「其他」、熱力圖月份以
週四歸屬且被間距擋下後會重試、進行中的週不再拿去和完整週比較。上游同批的漸層長條、色彩與
額外分析卡屬呈現功能，本輪不混入。

## 2026-08-29：terse 兩筆修正採用，plain-language 列後續

`83f8a4e` 之後上游 ahead 8 筆，扣掉 4 筆 `chore: sync AI updates`（只動 `ai_updates.json`，本 fork 已移除）
與 `beacc12a`（上游發版 v0.30.3），真正要判的是 terse 三筆。三筆都動到本 fork 也有的檔案
（`usage_terse_mode.py`、`usage_terse_reminder.py`、`session_hooks.py`、`i18n.json`），不能走自動分流。

### 採用 1：`1ec6fe4` — 自我修復不會替換已安裝的舊版 reminder script

本 fork 的 `_self_heal_terse_reminder()` 只檢查「script 或 entry 不存在」，兩者都在就 `return`。
裝好之後就再也不會被換掉，而同一支檔案裡另外三個 hook 都有版本比對：SessionStart terse、Codex terse、
resume。`usage_terse_reminder.py` 本來就有 `__version__`，只是沒人拿來比。已補
`TERSE_REMINDER_HOOK_VERSION` 與 `_installed_terse_reminder_version()`，缺件的還原路徑不變，多一條
「present but stale → 重新複製並記 `update_terse_reminder_hook`」。回歸測試
`test_self_heal_updates_old_reminder_version` 拿掉修正即紅燈。

### 採用 2：`4222250` 的 prompt 半部 — 兩處自相矛盾

同一段指令要求開場白帶 🐾，接著又說不要表情符號；工具呼叫旁白也被一竿子禁掉，跟「開工具前說一句要做
什麼」的用法打架。兩句都改寫：表情符號限縮成「除了開頭那句招呼，內文不放」，工具旁白改成「不要複述工具
名稱或呼叫過程，但開工具前用一句話說明要做什麼是可以的」。

**兩份副本都要改**。`usage_terse_mode.py` 裡的 `_DEFAULT_INSTRUCTION` 只是退路；真正送進模型的是
`i18n.json` 的 `terse_mode_instruction`，由 `_write_terse_sidecar()` 寫進
`~/.claude/agentdeck-terse-prompt.json`，而 `_load_instruction()` 優先讀 sidecar。只改 .py 等於沒改。
`TERSE_HOOK_VERSION` 因此推到 `1.1`——`_self_heal_terse_mode()` 版本不符時會同時重寫 script 與 sidecar，
已經開著精簡模式的使用者才拿得到修好的文字。

### 不適用：`4222250` 的語言偵測半部

上游的 `_detect_lang()` 只讀 `USAGE_LANG`／`TT_LANG`／`LANG`，環境變數都沒有就掉到英文，所以它把
`detect_lang()` 的結果寫進 sidecar 讓 hook 讀回來（跨平台，macOS 要 NSLocale）。本 fork 是 Windows-only，
`_detect_lang()` 讀完 `AGENTDECK_LANG`／`TT_LANG` 之後回退 `_windows_system_lang()`
（`GetUserDefaultUILanguage`），而且刻意不讀 `LANG`（Git Bash 會塞 en_US 蓋掉系統語言）。
上游要修的那個洞在這裡本來就沒有，照抄只會多一條 sidecar 相依。

### 採用 3（同日稍晚改判）：`ec89500` plain-language 改寫

原判「列為後續、等維護者點名」。維護者當日授權「這類評估你決定就好」後改判**採用**。

理由：它針對的是精簡模式的實際失效方式——只要求短，回覆就靠塞術語變短，短而難懂。加入的三條規則（挑口語詞、術語第一次出現補十字以內白話、收尾講做了什麼／成功沒／下一步）都是可檢查的具體要求，
不是空泛的風格宣示，而且與本 repo 兩語文件一貫的白話取向一致。成本是 SessionStart 指令變長；
每則都送的 reminder hook 只多「用白話」三個字，逐則的節省不受影響。

`usage_terse_reminder.py` 也跟著改，所以 `TERSE_REMINDER_HOOK_VERSION` 推到 1.1——這正好第一次
實際用到本輪修好的自我修復：舊版 reminder script 會被換掉，換作修好之前就是永遠停在 1.0。

issue #12 仍保持開啟：前一輪列出的 agy 額度通知／burn rate、面板量高度與縮放、Codex `status_line`
無裸 `[tui]`、Claude advisor 成本對帳、Codex 5h session keeper 都還在候選裡。

## 2026-08-28：Grok 本機額度卡與打包斷言，其餘 backlog 記略過

San-Hsien Yang 指定本輪由 **grok-4.6 high** 處理 issue #12，優先兩件事，其餘略過並留下理由，不整批吞掉、不改本 fork 的套件佈局。

### 採用 1：Windows 打包斷言（`c1b8d80`；`82895b6` 不適用）

上游 v0.29.34 把 `wintray.py`→`wintray/app.py`、`tui.py`→`tui/app.py`，打包腳本的 `--hidden-import` 仍寫舊頂層名，打出來的 exe `Test-Path` 綠燈、一啟動 `ModuleNotFoundError`。`82895b6` 把 hidden-import 改成 `wintray.app`／`tui.app`；`c1b8d80` 再用 `archive_viewer` 斷言封存裡真有這兩個模組。

本 fork **仍是頂層** `wintray.py`／`tui.py`，`main.py` 用字串動態載入。照抄 `wintray.app` 會打出一個缺進入點的 exe。因此：

- `82895b6` **略過**：那個 bug 在此 fork 不存在。
- `c1b8d80` **採用概念**：`scripts/build_windows.ps1` 斷言封存含 `'wintray'`、`'tui'`；`tests/test_main.py` 釘 hidden-import 必須是頂層名，且禁止 `wintray.app`／`tui.app`。

`49d4df5`（`installer.session_hooks`）隨之不適用：本 fork 沒把 hook 搬進 `installer/`。

Linux cloud agent **沒有**跑 `build_windows.ps1`；archive_viewer 那層要等 Windows 發版／實機打包才算驗完。

### 採用 2：Grok CLI 第四張本機額度卡

來源是 `~/.grok/logs/unified.jsonl`（billing snapshot + `shell.turn.inference_done`），外加 `~/.grok/config.toml` 的預設模型。**沒有新的 usage API**，與 Claude／Codex 同一套 local-file 契約，因此採用：

| 上游 | 內容 |
|---|---|
| `505336f` | 第四張週額度卡 |
| `74ad95f` | WebKit 圖示尺寸 + Hide Sections |
| `5463cd3` | 單次 token 併入今日成本／用量 |
| `32da5ab` | 獨立單色 `--grok`，不再借用 agy 紫 |
| `1cc5929` 的 Grok 缺口 | Windows 拖曳區 selector 補 grok；四張主題的 DOM／payload 合約測試 |

本 fork 沒有 13 張主題、沒有 Cloud Observation，所以 `ba4f690`、`667b038` 略過。`1cc5929` 的文件搬家與五語 README **不採用**。`7065af7` 是上游 `menubar.py` 的去重；本 fork 為過 `wintray.py` 行數閘門而抽出 `_panel_menu_data()`，不是 cherry-pick。

### 其餘 64 筆：逐筆審完，標記推到 tip

`last_reviewed` = `83f8a4e`，`last_merged` = `1cc5929`（最後一筆有採用內容的上游 commit；其「slim repo root」半部仍略過）。未採用的每一筆都在下方 Skipped 表。下列真實功能**列為後續**，不是「不適用」：agy 額度通知／burn rate、面板量高度與縮放、Codex `status_line` 在無裸 `[tui]` 時寫不進去、Claude advisor 成本對帳、Codex 5h session keeper。issue #12 保持開啟，因為這些後續候選還在。

## 2026-08-22：上游的 PR、issue、分支盤點

一次盤點，之後只看增量，不要每次重新評估。

| 面向 | 當時狀態 | 結論 |
| --- | --- | --- |
| Open PR | **0** | ~~上游不用 PR 流程~~ — **這個前提是錯的，已於 2026-08-23 更正**：當時只查了 `--state open`。上游有 106 個 PR（82 merged／11 closed／0 open）。逐筆結果見本檔的 2026-08-23（補）段落。 |
| Open issue | **0** | 沒有 **open** issue，但 `--state all` 有 92 個（全部 closed）。判準不變：**只有會改變「本 fork 要驗什麼」的才追**（Windows 行為、資料外洩、授權）。抽查結果見 2026-08-23（補）段落。 |
| 分支 | 7 個（6 個不是任何 open PR 的 head） | **逐一比對過，不是只數數量。** 只有兩個相對 `main` 有獨佔 commit，而且兩個都是 Windows 修正——本 fork 正是 Windows 線，所以特別查了：<br>• `fix/windows-project-resolver-drive-root`（ahead 2）：把編碼過的專案路徑錨定在磁碟根。本 fork `project_resolver.py:100` 已有同名的 `_encoded_path_root()`，內容一致。<br>• `fix/windows-claude-quota-fallback`（ahead 2）：`~/.claude.json` 配額回退與 ASCII hook 路徑。本 fork `usage_client.py:29` 有 `CLAUDE_JSON_FILE`、`session_hooks.py:66,80` 有 `_RESUME_MARKERS`／`_TERSE_MARKERS`，內容一致。<br>兩者都已涵蓋，無須引用。其餘分支相對 `main` 沒有獨佔 commit。 |

水位（**2026-08-23 更正為** PR **#106**、issue **#92**，分支盤點日 2026-08-23）。原本記為「無」是因為只查了 open。下次只要確認「有沒有新的 PR／issue 出現」，
不必重讀已經看過的清單。commit 的水位仍由上面 sync-points 的 `last_reviewed` 管。

## 2026-08-23：把「列候選」的解析韌性補完，並確認增量水位

### 已引用：`2588cc0` 的 JSONL 韌性半部

上一輪把 `2588cc0` 的遮罩三項採用、權限半部判為不適用，剩下的 JSONL 上限與 RecursionError
保護寫成「**列候選**」。回頭實查，這個「候選」沒有站得住的理由——它與平台無關，而本 fork
讀的正是同一批 session log：

- `jsonl_utils.py`、`providers/history_loader.py:301`、`providers/codex_loader.py:1112`
  全部是無上限的 `readline()`；
- 四個 `json.loads` 呼叫點只捕捉 `json.JSONDecodeError`，而深層巢狀丟的是 `RecursionError`；
- `grep -rn "RecursionError"` 在本 fork 的產品碼是 **0 命中**。

亦即缺陷全中，只是沒人回頭做。本輪落地：新增 `jsonl_limits.py`（64 MiB 上限），五個讀取點
改走 `read_bounded_jsonl_line`，四個解析點補 `RecursionError`，另補 `_websocket_event_payload`
——它同樣對不可信內容做 `json.loads`，上游沒改，但那是同一類缺陷。

**照抄會壞掉的那一段**：`history_loader` 與 `codex_loader` 的增量快取對「已確認前綴」做滾動
雜湊，下次執行從 offset 0 重算比對。上游的版本在跳過超長行時推進 confirmed offset，卻沒把
排掉的位元組餵進雜湊，於是 digest 與檔案永遠對不起來——解析結果仍正確，但增量路徑會**靜默
退化成每次全量重解**。因此 `read_bounded_jsonl_line` 多一個 `on_skipped_bytes` 參數，由這兩個
呼叫點傳入 `digest.update`。`test_skipped_oversized_line_keeps_the_incremental_cache_usable`
就是釘這件事的：拿掉參數實跑會紅（`_confirmed_prefix_hasher` 回 `None`）。

驗證：新增 8 條測試，`tools/dev_check.ps1` 全綠。

### 增量：`5269fd4` → `6d74e58`

兩筆 `chore: sync AI updates`（`a3574b5`、`6d74e58`），只動 `ai_updates.json`；該檔已在本 fork
移除，`tools/check_upstream_updates.py:157` 的過濾器正是為此而設。**不適用**。

### 分支／PR／issue

`upstream/main` 之外仍是同 7 條分支、0 個 open PR、0 個 open issue。今天重驗兩條相對 `main`
有獨佔 commit 的 Windows 分支，結論與 2026-08-22 相同，且本 fork 的 `_encoded_path_root()`
比上游多接受裸磁碟字母（Claude Code 把 `C:\` 編成 `C--`，上游只認 `C:`），**本 fork 較完整**。

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
| main | `9261121` | chore(release): v0.30.7 | 2026-09-04 | **不適用**。上游的發版 chore（`CHANGELOG`、`pyproject` 版號、`uv.lock`）。本 fork 自行版控與發版，不跟上游版號。 |
| main | `6adc9bb` | docs(website): 官網補上 Grok CLI 功能卡片，五語系同步 | 2026-09-04 | **不適用**。上游 `docs/index.html` 的行銷頁與五語系文案；本 fork 的公開入口是自己的，正式 UI 只出貨 zh-TW／en。 |
| main | `3f33a31` | style(web,report): 官網與 HTML 報告視覺改版 | 2026-09-04 | **列後續**。同 2026-08-31 那批的判準：`ui/report_styles.py` 已與上游分岔，整批視覺改版需要獨立的渲染與列印驗收，不在上游同步裡順手做。 |
| main | `d92bda0` | refactor(report): 重做頂部 KPI 卡片 | 2026-09-04 | **列後續**。同上。牽動 `ui/html_report.py`、`i18n.json` 與三份 snapshot fixture，屬報告呈現功能而非修正。 |
| main | `e42350e` | docs: 修正文件與程式碼脫節的三處事實 | 2026-09-04 | **不適用**。修的是上游 `README` 與五語鏡像（ja／ko／zh-CN）加官網；本 fork 的 README／DEVELOPMENT 是自己維護的雙語版本，那三處敘述本來就不同。 |
| main | `b026f4c` | docs: 副標與 meta description 補上 Grok CLI | 2026-09-04 | **不適用**。同上，上游五語 README 與官網 meta。 |
| main | `3fdda7e` | docs(changelog): Fable 5.1 定價與配額門檻的變更紀錄 | 2026-09-04 | **不適用**。上游 `CHANGELOG` 條目；本 fork 只記自己的維護歷史。 |
| main | `6a2ff55` | build(deps-dev): bump ruff 0.16.4 → 0.16.5 | 2026-09-04 | **已涵蓋**。本 fork 的 `pyproject.toml` 已宣告 `ruff>=0.16.5`。 |
| main | `1312289` | fix(login-item): 開機自動啟動關閉失敗時補提示 | 2026-09-04 | **不適用**。整筆都在 `installer/login_item.py` 的 `_launchctl_bootout()`，是 macOS `launchctl` 路徑；正式產品不支援該平台。同批 `43fa739` 的 Windows 登錄檔半部已採用。 |
| main | `b253fcc`／`10e1897`／`b7949cb` | fix(report): 甜甜圈總量、月份標籤、進行中週比較 | 2026-08-31 | **正確性採用，視覺半部不採用**。甜甜圈用 `summary.total_tokens` 並補「其他」；月份用週四且被 spacing 擋下後重試；未完成週標成進行中、摘要只比完整週。漸層條與表格配色不影響數值，未混入本輪。 |
| main | `f06216f` | fix(statusline): agy 模型名不再一中一英 | 2026-08-31 | **採用**。移除 `display_name` 的 `(Low/Medium/High)` 後綴，只保留本地化 `/速答／標準／深思`；缺 `effort` 時才用後綴回填。 |
| main | `188b3f7` | fix(installer): 別把名字像的第三方狀態列當成自己的 | 2026-08-31 | **採用並擴到本 fork 的 Claude／Antigravity／self-heal 路徑**。由子字串改成完整 script 檔名邊界比對，`agentdeck-statusline-pro.py` 與 `.backup` 保持 external。 |
| main | `e90daaf` | fix(wintray): Grok CLI token 納入 Windows 今日用量 | 2026-08-31 | **已有等價實作**。本 fork 的 `_load_entries()` 已呼叫 `grok_loader.load_entries()`，fingerprint 也包含 Grok log。 |
| main | `053c66a` | fix(statusline): 檔案鎖加上逾時 | 2026-08-31 | **Windows 路徑已有**。本 fork 的 `_acquire_msvcrt_lock()` 已以 deadline 輪詢；上游本筆新增的是 POSIX `fcntl` 保護，正式產品不支援該平台。 |
| main | `b41ef98` | fix(panels): CSS zoom 後保留自然 layout height | 2026-08-31 | **不適用目前架構**。本 fork 沒有 `usageApplyPanelZoom`／`fit_scale`，超出工作區時採固定視窗加可捲動內容；不存在該筆 Chromium zoom deadlock／flex 裁切路徑。PR #118 同結論。 |
| main | `3da9301`／`45bd0eb`／`be99752`／`6532dd8`／`8625719` | feat/fix(report): 佔比長條、逐日曲線、列印／空狀態、一次過關率、視覺層次 | 2026-08-31 | **列後續，不在 bug 修補中擴張報告 UI／schema**。正確性子項已由上一列收斂；這組需要獨立 HTML 渲染與列印 smoke。 |
| main | `c542ffe` | fix(report): 缺模型名的打斷與拒絕工具不漏算 | 2026-08-31 | **不適用目前資料模型**。本 fork 的 `persona_loader.py` 只產生活躍時段、專案、標題與訊息數，沒有上游的 model interruption／denied-tool 統計。 |
| main | `f3f2c19`／`95ff0e8`／`5c69549`／`54152f7`／`1002370`／`4b97ee0` | feat/fix/docs(statusline): cache 命中率與到期倒數 | 2026-08-31 | **列後續功能**。會改部署到使用者環境的 stdlib hook、版本、自我修復與雙語字串，需以真實 Claude payload 驗證，不順手併入額度讀取修補。 |
| main | `52230b6`／`aebf2a7`／`b7e7dff` | feat/fix(statusline): Grok CLI 狀態列、跨平台測試、解除安裝還原 | 2026-08-31 | **列後續功能**。新增第三套 provider credential／安裝／備份／還原契約；需完整 rollback 與 idempotency 測試，不能只帶 renderer。 |
| main | `9cdd2c3` | feat(terse): 加三條 Pinker 白話規則 | 2026-08-31 | **列後續文案變更**。現有 D-28 指令已涵蓋白話、術語說明與刪贅字；再增加每 session 固定 prompt 成本需另做取捨，不當作 bug。 |
| main | `b88c2bc`／`a7927b5`／`ec2e29d` | feat/fix/style(menubar): Grok 取代 companions、標題與圖示間距 | 2026-08-31 | **不採用**。macOS menubar-only；本 fork 已移除該平台。PR #120／issue #117 同結論。 |
| main | `3816c33`／`5759d39`／`7cd04fc` | release: v0.30.4／v0.30.5／v0.30.6 | 2026-08-31 | **不適用**。上游版號與發版文件；本 fork 版號獨立（D-05）。 |
| main | `05efa87`／`75ef0dc`／`83f13df`／`6a544ad`／`81a293a` | chore: sync AI updates | 2026-08-31 | **不適用**。只動 `ai_updates.json`，該檔已在本 fork 移除。 |
| main | `5ab4bd0` | fix(ci): Windows mypy 放行不存在的 `os.fork` | 2026-08-31 | **不適用**。修的是上游 POSIX lock timeout 測試；本 fork 沒有該 `os.fork` 測試，現有 mypy 已通過。 |
| main | `c1b8d80` | ci(build): Windows 打包後斷言 exe 內含 wintray.app 與 tui.app | 2026-08-28 | **採用概念，不照抄模組名**。本 fork 仍用頂層 `wintray.py`／`tui.py`，`archive_viewer` 斷言改驗 `'wintray'`／`'tui'`；測試禁止 hidden-import 寫成 `wintray.app`／`tui.app`。Windows 實機打包尚未跑。 |
| main | `505336f`／`74ad95f`／`5463cd3`／`32da5ab` | feat+fix: Grok CLI 第四張本機額度卡、Hide Sections、今日 token、獨立 --grok 色 | 2026-08-28 | **採用**。讀 `~/.grok/logs/unified.jsonl`，無 usage API。接進 `providers/grok_*`、`state/menubar_grok.py`、四張主題、payload、tooltip、選單。 |
| main | `1cc5929` | chore: slim the repo root and close the Grok CLI gaps | 2026-08-28 | **Grok 缺口採用，搬家不採用**。Windows 拖曳區 selector 與 DOM／payload 合約測試已補。九份文件搬出根目錄、五語 README 補 Grok——本 fork 根目錄契約與兩語 README 不同，不跟。`last_merged` 設於此 SHA，因為這是最後一筆有採用內容的上游 commit。 |
| main | `cf90198` | test(main): 守住以字串動態載入的模組 | 2026-08-28 | **精神採用**。本 fork `tests/test_main.py` 已守 `tui`／`wintray` 動態載入，並把 hidden-import 與 archive 斷言綁在同一條測試。 |
| main | `82895b6` | fix(build): Windows 打包補回 wintray.app 與 tui.app 的 hidden-import | 2026-08-28 | **不採用**。那個 bug 的前提是模組已搬進 `wintray/app.py`／`tui/app.py`；本 fork 從未搬家，照抄會打出缺進入點的 exe。守門改由 `c1b8d80` 的斷言（本 fork 模組名）負責。 |
| main | `49d4df5` | fix(build): point Windows hidden-imports at their post-refactor package paths | 2026-08-28 | **不適用**。上游把 `session_hooks`／`setup_hook` 搬進 `installer/`；本 fork 仍是根目錄 stdlib hook，hidden-import 維持頂層名。 |
| main | `f839c0a`／`ef3ef23`／`974b6c4`／`1f64331`／`b724d45`／`ca5487a`／`aeb4b46`／`da03ca7`／`978a4a4`／`59bd475`／`79fb52f`／`960a775` | chore: sync AI updates | 2026-08-28 | **不適用**。只動 `ai_updates.json`，該檔已在本 fork 移除。 |
| main | `e0d27b2`／`08c2c44`／`375bfc9`／`8ddd193`／`7065af7` | feat+revert+fix: macOS 選單列粗體／兩行堆疊／單色 template／去重 | 2026-08-28 | **不採用**。macOS menubar；本 fork 已移除該平台。`08c2c44` 隨後被 `8ddd193` 還原。`7065af7` 的檔案大小去重，本 fork 以抽出 `_panel_menu_data()` 過閘門，不 cherry-pick 上游 menubar。 |
| main | `dff85ee`／`5bbdcf6`／`6ed1f06`／`2e83796`／`0a98175`／`4f18573`／`2328bae` | refactor: menubar／loaders／wintray／discussion／tui／installer／quota 套件搬家 | 2026-08-28 | **不採用**。本輪明確不把樹改成上游套件佈局；hook 必須留在根目錄 stdlib-only。搬家正是 `82895b6`／`49d4df5` 那些打包事故的源頭。 |
| main | `e8b4bd3`／`69d0e1f`／`e422a65`／`b3e4613`／`20a6f10`／`655488d`／`8c72373`／`2b8b284`／`ba4f690` | docs(site/readme): 官網活面板、十三張圖庫、favicon、footer 翻譯、WebP、README 示範圖補 Grok | 2026-08-28 | **不採用**。上游官網與 13 張主題圖庫；本 fork 的 `docs/index.html` 已獨立、只維護四張主題、兩語 README。 |
| main | `de72a1d` | feat(panels): 新增候鳥遷徙面板，彩繪玻璃改成會動的萬花筒 | 2026-08-28 | **不採用**。本 fork 自 D-23 只留四張主題；不引入第十五張，也不把既有彩繪玻璃改成萬花筒。 |
| main | `667b038` | fix: use this panel's own stale classes for Cloud Observation's Grok row | 2026-08-28 | **不採用**。Cloud Observation 已於 v0.40.0 移除。 |
| main | `bbf642c` | polish: give the yearly Wrapped card a glow, badge, and overflow fix | 2026-08-28 | **不採用（裝飾，列後續若要視覺對齊）**。本 fork Wrapped 卡樣式已分家，照抄需渲染驗證。 |
| main | `a79b15d`／`c0e1022`／`61ea4ad`／`15fef03`／`31e2246`／`83f8a4e` | chore/release: 上游 0.29.34／0.29.36／0.29.37／0.30.0／0.30.1／0.30.2 | 2026-08-28 | **不適用**。上游自己的發版與版號（D-05）。 |
| main | `98d26ec` | chore: retrigger CI after GitHub Actions outage | 2026-08-28 | **不適用**。空 commit，重跑上游 CI。 |
| main | `f64d7a8` | docs(claude): 記下面板量高度會被 flex 1 加 overflow hidden 塌掉 | 2026-08-28 | **不採用**。上游 CLAUDE.md；本 fork 面板量高度問題與 D-23 注入層修法已另記。相關程式修正在 `e3cc667`／`88a3308`／`a12f604`，列後續。 |
| main | `e3cc667`／`88a3308`／`a12f604` | fix+feat(panels): 還原高度後重測、固定彈性卡片、螢幕放不下改縮放 | 2026-08-28 | **想要，列為後續**。真實裁切問題，但本 fork 自 D-23 已用注入層改 overflow，與上游量測／縮放路徑不同，需 Windows 實機對過再移植，本輪不做半套。 |
| main | `15df18f`／`f256dcf` | feat(quota): Antigravity 額度通知、Codex 歷史遷移偵測、Claude 成本對帳、agy burn rate 提前警示 | 2026-08-28 | **想要，列為後續（優先）**。與本 fork 的 agy／通知契約相容，但不是本輪指定的兩項優先；半套接入會跟既有 window keeper／quota notifications 纏在一起。 |
| main | `752416e` | feat: add Codex CLI to auto-start 5-hour session keeper | 2026-08-28 | **想要，列為後續**。本 fork 已有 Claude／agy window keeper；接 Codex 要另驗排程與預設關閉契約。 |
| main | `ba66338` | fix: count advisor iterations and 1h cache writes in Claude cost | 2026-08-28 | **想要，列為後續**。成本對帳正確性，與 `15df18f` 同批做。 |
| main | `cd2ff46` | fix(codex): write status_line when config.toml has no bare [tui] header | 2026-08-28 | **想要，列為後續（優先）**。會改使用者 `~/.codex/config.toml` 的寫入路徑，必須連 backup／rollback／idempotency 一起驗，本輪不做半套。 |
| main | `2551e17` | fix: pin utf-8 decoding on the launchctl and gh subprocess reads | 2026-08-28 | **launchctl 半部不適用**（macOS）。`gh` 讀取編碼本 fork 若有同等 subprocess 應另查，列後續，本輪不順手改。 |
| main | `df78c34`／`5fa8796` | build(deps): PyObjC 12.2.2、ruff 0.16.4、codeql-action | 2026-08-28 | **不適用（各自處理）**。PyObjC 本 fork 不使用；ruff 0.16.4 已在本 fork；codeql-action 走自己的 Dependabot。 |
| main | `5391aad` | fix(wintray): 系統匣提示文字三處修復 | 2026-08-22 | **採用**。三個子項在本 fork 全中：(1) `build_tooltip` 顯示 `100 - percent`，而面板走 `percent_used`——同一個問題兩處給不同數字；(2) 完全沒有 Antigravity 段落，儘管本 fork 支援它；(3) Claude 的 Session／Weekly 各佔一行，與 Codex 的併行格式不一致。第四個子項（更新彈窗清理 Markdown）**已涵蓋且做法更好**：本 fork 的 MessageBoxW 刻意完全不放 release notes（沒有捲軸、notes 就在對話框願意開的那一頁），程式碼裡已有註解說明。另補兩條測試：`hide_claude` 開啟時 tooltip 不得把 Claude 放回來、`percent is None` 不得編造數字。 |
| main | `2588cc0` | fix(security): 修補分享報告遮罩失效與本機檔案權限 | 2026-08-22 | **遮罩三項採用，權限半部不適用，JSONL 上限列候選**。遮罩失效在本 fork 同樣成立且是實質外洩：勾了「遮罩專案名稱」匯出的 HTML，`downloadHtml` 直接序列化整份 DOM，而未遮罩的 `csvData` 就內嵌在報告自己的 script 裡跟著送出去，收檔者按報告內建的 CSV 鈕即可取回真實專案路徑。修法比照上游拆成獨立 `application/json` 節點、遮罩匯出時移除未遮罩節點、JS 端 fallback；但**遮罩標記改用排名而非名稱**（`data-mask-index`），因為把真名放進屬性一樣會跟著匯出檔外流。圖例 `lg-name` 與 insights 句中專案名同樣補上遮罩，且三處編號一致。新增 `tests/test_html_report_masking.py` 8 條把這些性質釘住。權限半部（0700／0600、copy2→copy+chmod、quarantine mode）是 POSIX chmod，本 fork 為 Windows-only、使用者目錄由 ACL 隔離，**不適用**；`3cb368d` 的 Windows 權限守衛測試隨之不適用。JSONL 單行上限與 RecursionError 保護與平台無關，**已於 2026-08-23 引用**（見同日段落：本 fork 的增量快取需要額外的 `on_skipped_bytes` 才不會退化）。 |
| main | `90000a9`／`1c8e82d`／`5269fd4` | chore: 發布 0.29.31／0.29.32／0.29.33 | 2026-08-22 | **不適用**。上游自己的發版 commit，本 fork 有獨立版號。 |
| main | `6e43f4d`／`f445f5b` | feat(panel): 昨日用量與一般 Codex 限額選擇、切換鈕移入 Codex header | 2026-08-22 | **候選**。功能面沒有邊界衝突，但本 fork 的面板自 v0.40.0 起已收斂成 `panels/registry.py` 單一來源且樣式分歧，屬移植而非套用，需實際渲染驗證。 |
| main | `28a982d`／`709cb9d` | feat(agy): 用 session 的 Cwd 推導 Antigravity 用量的實際專案 | 2026-08-22 | **候選（優先）**。這是真實的歸屬錯誤修正，本 fork 同樣支援 Antigravity；需比對本 fork 的 agy loader 實作後再移植，並補歸屬測試。 |
| main | `01c86f7`／`ed76d12`／`4fd5bd8` | feat(packaging): 以 usage-cli 發行名提供零安裝 uvx 入口 | 2026-08-22 | **不適用**。綁上游的 PyPI 發行名 `usage-cli`；本 fork 的發行識別是 agentdeck，且 `[tool.uv] package = false`。 |
| main | `a0fb415`／`60bc262`／`facec9b`／`a86a44d`／`f6421c9`／`ecce186` | build(deps): mypy／ruff／codeql-action／setup-uv／signpath 版本更新 | 2026-08-22 | **不適用（各自處理）**。本 fork 有自己的 dependabot 與依賴新鮮度檢查；mypy 2.3.1 與 ruff 的更新本輪已在本 fork 獨立完成。`setup-uv` v9.0.0→v10.0.1 交給本 fork 的 dependabot 依既有 pin-by-SHA 流程處理。 |
| main | `7d495ae` | test(ci): 驗證 Linux 上的 Claude Code 狀態列 | 2026-08-22 | **不適用**。本 fork 的 CI 是 windows-latest，正式產品只支援 Windows。 |
| main | `cf49d7a`／`557c201` | chore: sync AI updates | 2026-08-22 | **不適用**。只動 `ai_updates.json`，該檔已在本 fork 移除（upstream-check 的過濾器正是為此而設）。 |
| main | `5ad2b3f` | fix(tests): 修 mypy 對 test_agy_loader 的 func-returns-value 誤判 | 2026-08-22 | **不適用**。修的是上游該檔的寫法；本 fork 的 `tests/test_agy_loader.py` 已獨立演進，且 `mypy .`（189 個檔案）目前零錯誤。 |
| main | `92f536f` | fix(rate): 速率分類改用真實經過時間，停手後會自然衰減 | 2026-08-18 | **已採用**。本機重現:分母原本是「最後一筆減第一筆 entry」，不含最後一筆之後的閒置時間。餵 56,100 active tokens、密集 10 分鐘後停手 40 分鐘——舊算法仍是 5,610 tokens/min（**Active**），真實速率只有 1,122（Normal），而且會一路卡著直到 entry 滑出 1 小時窗。改成從 `_utc_now()` 起算。既有測試原本沒固定「現在」、隱含依賴舊分母，補上 `_pin_now_to_last_entry()` 維持它們原本要測的語意;另加兩條新測試把「停手會衰減」與「進行中仍讀得到高負載」同一份資料的兩種答案釘住。 |
| main | `3039745` | fix(panels): 摺紙面板重置文字改深色加光暈 | 2026-08-18 | **已採用，並先量了才做**。本 fork 的摺紙面板同樣有這個問題:`.reset` 是 `--muted`（`#55778e`），右下摺角最深處是 `#205779`，實算 **WCAG 對比 1.63**（AA 小字要 4.5）。值得記的是**上游的說法只對了一半**:本 fork 早有 `.card > * { z-index: 1 }`，字並沒有被摺角蓋住，它只是跟腳下的顏色一樣。真正有效的是**光暈**——深色字配三層淺色 text-shadow 實算 **12.11**，疊在什麼底色上都讀得到。上游同時把 margin-top 收 2px，那是為了它自己的卡片高度，本 fork 面板可捲動、高度另有處理，不跟。警示紅疊光暈底實算 3.24，對小字仍不足 AA 但遠優於疊深藍摺角，且紅色本身帶語意。 |
| main | `ac01760` | ci: 加面板定義一致性檢查 | 2026-08-18 | **精神採用，實作不照抄**。上游要同步的是 `panels/all_panels()` 與 Windows 的 `WINDOWS_PANELS`／`PANEL_HEIGHTS` **三處**人工同步;本 fork 於 v0.40.0 已把面板定義收斂成單一來源 `panels/registry.py`，那個問題不存在，一支 141 行的守門腳本沒有對應的東西可守。但單一來源仍有它驗不了自己的部分——**檔名是否還指向存在的檔案**。實查目前四張主題＋人才市場全部一致，隨即補上三道測試:高度涵蓋從 `available_panels()` 擴到 `renderable_panels()`（人才市場走同一條查表路徑）、登記的 HTML 檔必須存在、不得有指向已移除面板的孤兒高度（v0.40.0 移除九張主題正是這種風險）。三道都注入缺陷確認會紅燈。 |
| main | `2607850`／`6bd05ad` | style+feat: 預設面板 80% 門檻線與 90% 警示光 | 2026-08-18 | **想要，但需視覺驗證，列後續**。`2607850` 裡有一項本 fork 也有:`.card::before` 的 accent 條同時吃 `linear-gradient(..., transparent 72%)` 與 `opacity: 0.72`，兩層淡相乘。但這跟摺紙那筆不同——**沒有可量測的門檻可以判定它算不算缺陷**，是視覺取捨;而本 fork 的 `classic.html` 自 v0.40.0 起已與上游分歧，照抄需要實際看渲染結果才負責任。`6bd05ad` 的 conic-gradient 邊框環同理。兩筆一起排後續，屆時要在真實面板上截圖比對。 |
| main | `2128240` | fix(cli): usage status 百分比格式化 | 2026-08-18 | **不適用**。修的是 `usage status` 子指令的浮點數尾巴;本 fork 沒有這個子指令（`58f4228` 已於上一輪決定列為後續功能）。日後若移植 `usage status`，這筆要一起帶。 |
| main | `1be0540`／`367ca52` | style(panels): 駭客任務／雲圖觀測面板調透明 | 2026-08-18 | **不採用**。這兩張主題已於 v0.40.0 隨舊九張一併移除，本 fork 只維護預設＋Catppuccin＋彩繪玻璃＋摺紙。 |
| main | `1fbdea2`／`60c1bf4` | fix+design(site): 官網無障礙與社群預覽圖 | 2026-08-18 | **不採用**。上游自家官網的內容與視覺;本 fork 的 `docs/index.html` 已獨立改寫，主題數量也不同。 |
| main | `ef4af4e`／`1ddf5a7`／`afcd508`／`6724fba`／`903c34a` | docs(readme): 狀態列章節與 VHS 動圖（含簡中／日文／韓文） | 2026-08-18 | **不採用**。上游五語 README 的截圖與章節重整;本 fork 只維護 zh-TW／en 兩語，簡中／日文／韓文 README 已移除（見 CLAUDE.md 的 i18n 規則，明文寫著不要重新引入）。動圖本身是上游用 VHS 錄自家 macOS 狀態列，與本 fork 的 Windows 呈現不同。 |
| main | `867acf9`／`bb0e692` | chore: 發布 0.29.29／0.29.30 | 2026-08-18 | 純上游版號（D-05）。 |
| main | `d9e0935` | fix: 補回警示抑制的事件來源,並擋掉 cmd.exe 特殊字元路徑 | 2026-08-14 | **已採用,兩半都做,第二半做得比上游廣**。第一半是**本 fork 自己上一筆 `db6e34a` 造成的回歸**:`components.json` 頂層沒有 `incidents`,`_apply_alert_suppression()` 的「事件停在 monitoring 超過 4 小時就收警示」永遠進不去,只剩 24 小時兜底,警示多掛約 20 小時。實測頂層鍵確認:`components.json` 只有 `['components']`,OpenAI `summary.json` 是 `['components','page','status']`——**Codex 側那條抑制從未生效過**。端點選 `incidents.json`:實測 `incidents/unresolved.json` 對 OpenAI 回 **404**。測試替身一併改成照現實拆成兩個端點——原本一個 payload 供兩用,正是這個回歸能溜過去的原因。第二半上游只修 agy 路徑且靠「拒絕安裝＋轉 8.3 短路徑」;本 fork 的 `_shell_arg` 被所有 hook 共用（statusLine／forwarder／resume／terse／agy）,`list2cmdline` 只為空格與引號加引號,`C:/Users/R&D/` 原樣輸出。實測三種殼層全掛(cmd.exe rc=1、Git Bash rc=127「D/.gemini/hook.py: No such file or directory」、PowerShell rc=1),加雙引號後三種全 rc=0。改為偵測 shell 元字元就加引號——能修就修,不把使用者擋在門外。 |
| main | `3d44b80` | chore(pricing): 標註離線價目表核對日期 | 2026-08-14 | **已採用**。離線 fallback 價目表寫死且無版本資訊,廠商調價後會**無聲算錯成本**,而且沒有任何東西能告訴你表有多舊。加 `FALLBACK_PRICING_AS_OF`,並把 `calculate_cost()` 裡裸露的 1.25／0.1 抽成具名常數(是 Anthropic 的比例,對其他供應商不保證正確)。上游的 `scripts/check_fallback_pricing.py` 對帳腳本未移植——它比對的是上游 LiteLLM 表的取用方式,列為後續。 |
| main | `4bb717c` | fix(release): Windows 版本號解析改用 binary 讀取 | 2026-08-14 | **不適用,但已回頭確認本 fork 沒有同一個洞**。上游是 `read_text()` 在 Windows runner 上用 cp1252 讀含中文的 `pyproject.toml` 而炸。本 fork 的 `release.yml` 沒有那個步驟(改用 `check_release_version.py` 與 exe `--doctor` 對帳),`scripts/make_version_file.py` 讀同一個檔時本來就帶 `encoding="utf-8"`。 |
| main | `ef4dcbf`／`c30d043` | feat+fix: Windows 工作列進度條顯示配額（含 ITaskbarList3 IID 修正） | 2026-08-14 | **想要,列為後續功能**。本 fork 目前沒有任何 `ITaskbarList`／`SetProgressValue` 程式碼,屬新增功能而非錯誤修正。兩筆必須一起移植——`c30d043` 揭露上游的 IID 寫錯、進度條先前完全沒作用,只移植 `ef4dcbf` 會複製一個不會動的功能。 |
| main | `4a59670` | feat: Windows 配額通知改用可互動的 Action Center 快顯 | 2026-08-14 | **想要,列為後續功能**。本 fork 目前沒有 Action Center／ToastNotification 程式碼。會動到打包設定與相依套件,屬獨立的一輪工作。 |
| main | `60f9f5d` | feat: Windows 執行檔宣告 Per-Monitor-v2 DPI 感知 | 2026-08-14 | **想要,優先度較高的後續**。本 fork 沒有 manifest 也沒有 DPI 宣告,而開發機是 225% 縮放——這正是 DPI 問題最容易現形的環境。本輪已先把座標與執行緒問題處理完(見 `6901504` 列),manifest 屬打包層變更,另開一輪並要在多螢幕不同縮放下實測。 |
| main | `25b0979` | feat: Windows 刷新請求排隊,並補上檔案事件驅動刷新 | 2026-08-14 | **部分想要,列為後續**。上游新增 `windows_watch.py`(本 fork 沒有)。刷新排隊的動機與本輪 `6901504` 的 UI 執行緒佇列相近,但那是刷新流程而非視窗幾何,兩者不能混做。檔案事件驅動刷新會改變輪詢模型,需先量測本機實際效益。 |
| main | `0d5f05f` | feat: Windows 補上每日健檢、服務狀態橫幅與自動更新檢查 | 2026-08-14 | **多數本 fork 早已有**。實查:`_maybe_auto_check_update` 在 `wintray.py`、服務狀態橫幅有完整的 `service_status.py`(本輪還修了兩筆)。僅每日健檢是本 fork 沒有的,列為後續。 |
| main | `db42060` | feat: Windows 系統主題色同步成 CSS 變數 | 2026-08-14 | **想要,列為後續功能**。本 fork 的四張面板主題(預設／Catppuccin／彩繪玻璃／摺紙)是刻意選定的配色,接系統強調色要先決定它跟既有主題怎麼共存,不是單純移植。 |
| main | `75f8f66`／`87e3147` | refactor+fix: Windows 選單收斂成單一來源／分組跟 macOS 對齊 | 2026-08-14 | **不採用**。本 fork 已於 v0.40.0 自行把選單抽成 `win_tray_menu.py`(同樣是單一來源),項目組成與上游不同(多了人才市場、圓桌討論、四張主題),分組照抄反而會錯。 |
| main | `fdc89ac`／`d9625ce` | feat+fix: Antigravity 狀態列支援 Windows／改用無引號路徑 | 2026-08-14 | **已在 v0.41.0 自行移植,且本輪把引號問題修得更廣**。上游 `d9625ce` 的無引號路徑處理只涵蓋 agy;本 fork 的修正落在共用的 `_shell_arg`,涵蓋全部五種 hook,見 `d9e0935` 列。 |
| main | `5bb2c2b` | ci(release): 加上 SLSA build provenance 與 CycloneDX SBOM | 2026-08-14 | **想要,列為後續**。供應鏈安全,與已寫好的 SignPath 簽章步驟(`SIGNING.zh-TW.md`)屬同一批工作,一起做比較合理。本 fork 目前沒有 provenance／SBOM 產出。 |
| main | `58f4228` | feat(cli): 新增 usage status 指令與 JSON 輸出 | 2026-08-14 | **列為後續**。本 fork 有 `usage_cli.py` 但沒有 `status` 子指令。屬新功能;打包白名單那半本 fork 已有等價的`test_every_stdlib_hook_script_is_bundled` 閘門。 |
| main | `a1ce980`／`0a67ac1`／`dcd716c` | feat+style: 水墨貓新圖示、Windows app 圖示、readme logo 裁圓 | 2026-08-14 | **不採用**。上游的品牌識別;本 fork 是獨立分支,有自己的圖示與 README 視覺。 |
| main | `184fb74` | fix(menubar): 更新通知彈窗清乾淨 Markdown 符號 | 2026-08-14 | **不採用,本 fork 已用更徹底的做法解決**。動的是上游的 `menubar.py`／`update_release_notes.py`(本 fork 沒有)。本 fork 的更新提示已依需求縮到只顯示版本號與下載網址,連 release notes 本體都不呈現,自然沒有 Markdown 符號問題。 |
| main | `63509f5`／`7e07a1c` | chore: sync AI updates | 2026-08-14 | 只動 `ai_updates.json`;本 fork 已移除該功能。 |
| main | `eb896b0` | fix(menubar): forwarder 提示函式搬進 leaf module | 2026-08-14 | 動的是上游 `menubar.py`／`menubar_actions.py`(本 fork 沒有)。同樣的檔案大小紀律本 fork 有自己的閘門,本輪就因此把視窗佇列抽成 `win_ui_thread.py`。 |
| main | `8c4e3a9` | test: 放寬 shutdown 有界性測試的時間門檻 | 2026-08-14 | **不採用**。放寬的是上游 CI runner 上的時間門檻;本 fork 的 `test_discussion_bridge.py` 在 windows-latest 上一直是綠的,沒有理由先放寬一個沒有失敗過的門檻。 |
| main | `af313b8`／`3340aaa` | test+fix: 修 macOS runner 上失敗的測試／CI 的 mypy 失誤 | 2026-08-14 | **不採用**。前者是為上游的 macOS runner 加 skip(本 fork CI 只有 windows-latest);後者修的是上游當時的 mypy 紅燈,且動到 `windows_watch.py`／`test_usage_statusline_agy.py`(本 fork 沒有)。本 fork 的 mypy 一直是綠的。 |
| main | `9548705`／`ecabd3a`／`342f526` | build(deps): dependabot 升版 | 2026-08-14 | **不採用**。本 fork 有自己的 dependabot,版本由本 fork 的 `uv.lock` 決定。 |
| main | `d55bac3`／`b6e55b4`／`2f474ee` | chore+docs+release: 上游 0.29.27／0.29.28 版號與五語文件 | 2026-08-14 | 純上游版號與文件(D-05)。本 fork 走自己的 SemVer,文件只維護 zh-TW／en 兩語並有 `check_doc_parity.py` 閘門。 |
| main | 16 筆 merge commit | Merge branch 'codex/win-*' / PR #96 等 | 2026-08-14 | **不逐筆審視**。merge commit 不帶獨立變更,內容已由其父 commit 涵蓋,全數列在上方各列中。 |
| main | `6901504` | fix: Windows 視窗定位改用邏輯座標,幾何操作收斂到 UI 執行緒 | 2026-08-14 | **一半早已自行修好,一半採用**。座標那半本 fork 先前已獨立解決（`_to_logical_rect`／`_monitor_dpi_scale`／`_work_area_for_point`），且做得更多（扣標題列高度、右上角錨定、面板可捲動），不回頭照抄。執行緒那半是真的:實測本機安裝的 pywebview 6.2.1,`js_bridge_call` 對每一則 JS 訊息都跑 `Thread(target=_call).start()`,而 `resize()`／`move()` 直接讀 WinForms 的 `Location`／`Width`／`Handle` 再呼叫 `SetWindowPos`,完全沒有封送——面板回報高度走的就是這條路。在真實 WinForms 視窗上實測:工作執行緒 `InvokeRequired=True`、mutation 內 `False`,resize 生效（444×333 邏輯 → 999×749 實體）。同一次量測另外發現 pywebview 的 `loaded` 事件也不在 UI 執行緒上,`on_loaded()` 的重新定位是同一個 bug 的第二個現場。實作放進新的 leaf module `win_ui_thread.py`（`wintray.py` 已逼近 1900 行上限）,並比上游多一步:明確 `import clr` 再取 `System`,不倚賴 pywebview 先載入 pythonnet 的隱含順序——否則失敗形式是被吞掉的 ImportError 加一個永遠不執行的 mutation。 |
| main | `e720255` | perf: Windows 刷新不再重複遞迴掃描 Codex sessions | 2026-08-14 | **已採用**。先量再改:本機 54 個 session 檔,冷啟動 `load_rate_limits()` 自己走一次 237 ms、傳入掃描結果 142 ms。`HistorySourceScan.codex_rate_limit_candidates` 與 `jsonl_candidates` 參數本 fork 早就有,只是 `wintray.py` 沒接上,等於每次刷新遞迴走兩趟 `~/.codex`。加測試釘住呼叫路徑（只測 dispatcher 會漏掉這種回歸）。 |
| main | `db6e34a`／`352bed8` | fix: 服務狀態改讀 components.json | 2026-08-14 | **已採用**。對實際 feed 驗證後才動手:OpenAI 的 `summary.json` 只回前 25 個 component，實際有 34 個，`Codex API` 排在第 27——橫幅因此永遠是 unknown，而「元件不存在」與「元件正常」對呼叫端長得一模一樣。上游改測試斷言，本 fork 另加一條直接打真實 feed 的測試:白名單再度脫節就會紅燈，feed 連不上則 skip（別人的故障不該讓我們的 CI 紅）。 |
| main | `8e5e574`／`ea59b60`／`45b43ad`／`d9441fe` | fix(lang): Windows 忽略殼層繼承的 LANG | 2026-08-14 | **已採用，做得比上游更徹底**。本機重現:`LANG=en_US.UTF-8`（Git Bash／MSYS 會塞這個）讓 `detect_lang()` 回 `en`，但系統 UI 語言是 `zh-TW`——中文使用者從 Git Bash 啟動就是英文介面。上游以 `sys.platform` 分支保留非 Windows 的 LANG；本 fork 只跑 Windows、CI 也只有 windows-latest，那條分支永遠走不到，因此六個檔案一律拿掉 LANG。另加一條掃描測試:五個獨立 hook 腳本各有一份複製的語言判斷，漏改一份就會出現「app 與 hook 講不同語言」而其他測試都看不到。 |
| main | `9d573bd` | fix: hook 找不到可用 Python 時明確報錯 | 2026-08-14 | **一半採用，一半實測後否決**。採用的一半:找不到 Python 時原本回傳字面上的 `"python"`，裝出一條跑不起來的 statusLine——Claude Code 只會顯示空白、兩端都看不到錯誤。但上游 `raise SystemExit`，而 `SystemExit` 不是 `Exception`，本 fork 的 GUI 只接 `Exception`，照抄會讓例外從系統匣 callback 直接逃出去；且 `is_*_setup()` 這些述詞也會呼叫同一條路徑，等於「沒裝 Python 就連選單都開不出來」，比原本的 bug 更糟。改法:新增 `HookSetupError`，只在**安裝進入點**檢查，述詞維持不拋。否決的一半:上游同時讓非 ASCII 路徑直接報錯。本機實測 Windows 11 建立中文目錄，裝出的指令在 cmd.exe／sh（Git Bash）／PowerShell 三種殼層下**都跑得起來**（rc=0），而 `GetShortPathNameW` 回傳的仍是原長路徑（8.3 短檔名已停用），根本沒有 ASCII 形式可退。照抄會把所有帳號名非 ASCII 的使用者——正是本 fork 服務的繁中族群——擋在門外，理由還是一個重現不出來的故障。已為此加測試釘住。 |
| main | `4eb0e5e` | fix: 用量預估改用窗口平均斜率 | 2026-08-13 | **已採用**。本機重現:穩定 0.5%/分鐘燒十分鐘後，一則大訊息在 5 秒輪詢間隔內加 7%，EMA 預估 **0.9 分鐘**用完，窗口斜率是 32 分鐘。 |
| main | `07812bb` | feat: Windows 執行檔接上 SignPath 簽章流程 | 2026-08-13 | **部分採用**。版本資源產生器已移植（v0.40.1）。SignPath 本體需要維護者親自申請 OSS 方案——申請與接線步驟已完整寫成 [`SIGNING.zh-TW.md`](SIGNING.zh-TW.md)，步驟 1～3 需本人執行，4～5 可交給我。 |
| main | `99d143c`／`ed9bedb`／`17e8c46` | feat+fix: Antigravity CLI 狀態列 | 2026-08-13 | **已採用**。先驗證平台支援才動手:`agy.exe` 內含 `"statusLine"`／`Statusline Error`／`statusline command` 字串，`~/.gemini/antigravity-cli/settings.json` 在 Windows 上同路徑存在。上游把 `/usr/bin/python3` 寫死——在 Windows 上會裝出一條永遠跑不起來的指令，改用 `_find_system_python()`。腳本另從五語縮為兩語、`USAGE_LANG` 改為 `AGENTDECK_LANG`。 |
| main | `0014773` | feat: Codex 狀態列加 git-branch 與 used-tokens | 2026-08-13 | **已採用，整包做**。先對安裝的 codex-cli 0.146.0 執行檔驗證七個段位識別字全部存在，才改設定。含 `LEGACY_CODEX_STATUS_LINES` 升級安全機制與 self-heal 就地升級。 |
| main | `f74bbe0` | refactor: 合併選單開關分組 | 2026-08-13 | 上游 `menubar_menu.py` 的分組取捨；本 fork 的選單已於 v0.40.0 抽成 `win_tray_menu.py`，項目組成與上游不同（多了人才市場與 Catppuccin 配色）。 |
| main | `7fa4b6c` | fix: 自癒測試明確模擬 macOS | 2026-08-13 | 針對 `tests/test_usage_statusline_agy.py`（本 fork 沒有）。概念（測試不該依賴執行平台）本 fork 已在用 `sys.platform` 明確 skip。 |
| main | `bc26c6a` | docs: 記錄 window keeper 開窗不穩定的實測證據 | 2026-08-13 | 上游對自家 macOS 開窗行為的觀測；本 fork 的 window keeper 走 Windows 路徑，該證據不適用。 |
| main | `112bef4` | chore: 發布 v0.29.25 | 2026-08-13 | 純上游版號（D-05）。 |
| main | `d01f38a`／`49a0dfa` | feat+docs: Catppuccin 面板主題與四款 flavor 截圖 | 2026-08-12 | **想要，但不能直接複製**。實測 `catppuccin.html` 完全沒有 JS 狀態入口（`applyState` 出現 0 次），因為上游 `3e0fc4e` 之後面板狀態由共用核心供應——上游連 `classic.html` 都已經不定義 `window.usageApplyState`，而本 fork 的九張面板都還定義它。照抄會得到一張畫得出來、但永遠收不到額度資料、也永遠不回報高度的主題。與 `3e0fc4e`／`7743649`／`417ff01` 合併為同一項後續工作。 |
| main | `2a03853` | fix: 新面板同步測試在 Windows CI 誤觸 PyObjC import | 2026-08-12 | 為他們的 `panels.panel_ids()`（延遲 import PyObjC 的 HTMLPanel）加 macOS-only skip；本 fork 沒有那條測試，也沒有 PyObjC 路徑。 |
| main | `efce61a` | docs: 修正鐵則措辭矛盾、標註 codex_otel 舊格式相容路徑 | 2026-08-10 | 文件本身是上游 CLAUDE.md，但其中的事實已採用並**自行量測驗證**後寫進本 fork 的 CLAUDE.md：`codex_otel.trace_safe` 在本機 35,250 筆紀錄中只佔 47 筆，全部集中在 2026-08-05 的 52 分鐘視窗內，而該表至今仍在寫入。 |
| main | `7a8f8f6` | fix: 補 ruff lint（import 排序、Yoda condition） | 2026-08-10 | 修的是上游當時的 lint 紅燈；本 fork 的 ruff gate 一直是綠的。 |
| main | `bd89d98`／`fe0d547`／`236ff02`／`483e635` | docs/style: 官網與主題文案 | 2026-08-10 | 上游自家官網的內容與視覺；本 fork 的 `docs/index.html` 已獨立改寫，主題清單也因移除 World Cup 而不同。 |
| main | `60d11fe` | feat: 年度熱力圖加入貪食蛇彩蛋 | 2026-08-10 | 純娛樂性彩蛋，不影響任何額度資料；本 fork 目前優先處理正確性與資安，未來要加也應以本 fork 自己的報告版面為準。 |
| main | `3e0fc4e`／`7743649`／`417ff01`／`d01f38a` | refactor+feat: 共用面板核心與三張新主題 | 2026-08-12 | **已於 v0.40.0 採用**（此列保留以免記錄斷裂）。九張舊主題移除，改為 Classic＋Catppuccin＋彩繪玻璃＋摺紙。移植前逐張確認 Antigravity 支援（19／13／17 處）。詳見 D-23。 |
| main | `67eb3bb`／`3192874` | chore(release): v0.29.22／v0.29.23 | 2026-08-10 | 純上游版號（D-05）。 |
| main | `410ba88` | docs: CLAUDE.md 補上 codex 雙 sqlite 與 agy 配額端點的實際行為 | 2026-08-10 | 上游 CLAUDE.md 的內部說明；本 fork 的對應段落已自行改寫，且對外連線已在 `SECURITY.md` 逐條列出（D-18）。 |
| main | `d57e7c3` | refactor: 抽掉磁碟快取與 session hook 的三處逐字重複 | 2026-08-10 | 去重的三處在本 fork 的檔案結構下並非逐字重複（磁碟快取已分成 history／codex／agy 三個模組，session hook 在 `session_hooks.py`）；為了對齊上游而重構，風險大於收益。 |
| main | `723b9ab` | fix(security): build_app.sh 核對 instate-cli 指紋才打包 | 2026-08-10 | 針對 macOS 的 `build_app.sh` 與 py2app 打包流程；本 fork 用 PyInstaller，且 `instate-cli` 已被 `persona_store` 取代，沒有要核對的外部二進位檔。 |
| main | `6e22e84` | chore: 刪除死碼與 13 個孤兒翻譯鍵 | 2026-08-10 | 孤兒鍵清單是上游五語 bundle 的產物；本 fork 的兩語 bundle 已由 `test_i18n_key_parity.py` 與 v0.37.6 新增的兩條檢查把關，另行清理應以本 fork 自己的掃描為準。 |
| main | `dfa051c` | chore(release): v0.29.20 | 2026-08-10 | 純上游版號（D-05）。 |
| main | `0f97979` | chore(release): v0.29.21 | 2026-08-10 | 同上。 |
| main | `ad786a9` | refactor(menubar): 第九刀——四塊搬進葉模組 | 2026-08-08 | 同 `86bde4a`：抽葉模組的概念本 fork 已是既有做法，被重構的 `menubar.py` 我們沒有。 |
| main | `377aec2` | refactor(menubar): 第十刀——標題渲染與 PopoverViewController 出走 | 2026-08-08 | 同上。 |
| main | `13eba4d` | chore: 發版 v0.29.19 | 2026-08-08 | 純上游版號；本 fork 版號獨立（D-05）。 |
| main | `1220a08` | build(deps-dev): bump ruff 0.16.0 → 0.16.1 | 2026-08-08 | 本 fork 的開發相依由自己的 `uv.lock` 與 Dependabot 管理。 |
| main | `31e8883` | build(deps): bump the codeql-action group | 2026-08-08 | 同上；本 fork 的 workflow 以 SHA 釘選，由自己的 Dependabot 推進。 |
| main | `cdf43b3` | docs: README 移除 TUI 賣點與失效的 Star History 圖 | 2026-08-08 | 上游自身的行銷文案取捨；本 fork 的 README 已獨立改寫，TUI 仍是本 fork 支援的模式。 |
| main | `82c7c2a` | docs: README 開頭去複述、AI 協作獨立分組 | 2026-08-08 | 同上。 |
| main | `4d2d7e1` | docs: 修正日韓數字語序與繁韓翻譯錯誤 | 2026-08-08 | 只動 `README.ja.md`／`README.ko.md`／`README.zh-TW.md`；前兩者本 fork 已移除，第三者對應本 fork 的 `README.md`，該處無對應錯誤。 |
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
| main | `1ec6fe4` | fix(terse): update a stale reminder hook instead of only backfilling a missing one | 2026-08-29 | **採用**。本 fork 的 `_self_heal_terse_reminder()` 有同一個早退，已補 `TERSE_REMINDER_HOOK_VERSION` 與版本比對，並加回歸測試。 |
| main | `4222250` | fix(terse): resolve two contradictions in the prompt and stop defaulting to English | 2026-08-29 | **只採 prompt 半部**。emoji 與工具旁白兩處矛盾已在 `usage_terse_mode.py` 與 `i18n.json` 兩份副本改掉，`TERSE_HOOK_VERSION` 推到 1.1。語言偵測半部不適用：本 fork `_detect_lang()` 已回退 `_windows_system_lang()`，不會預設落到英文。 |
| main | `ec89500` | feat(terse): ask for plain language, not just short replies | 2026-08-29 | **採用**（同日稍晚，維護者授權自行評估後改判）。加「精簡是預算、白話是風格」與術語加註、收尾三件事；reminder 同步補「用白話」。見 D-28。 |
| main | `beacc12a` | release: v0.30.3 | 2026-08-29 | **不適用**。上游發版；本 fork 版號獨立。 |
| main | `4a1ece0`／`64c51aa`／`ff7859d`／`10be369` | chore: sync AI updates | 2026-08-29 | **不適用**。只動 `ai_updates.json`，該檔已在本 fork 移除。 |

## 2026-08-23（補）：PR 那一欄的前提是錯的

2026-08-22 的盤點寫「Open PR **0** ⋯上游不用 PR 流程，改動直接進 `main`。所以本 fork 的審查單位
就是 commit，PR 這條線沒有東西可追」。**「0 個 open PR」是對的，「上游不用 PR 流程」是錯的**：
盤點時只查了 `--state open`。`--state all` 一查，上游有 **106 個 PR**（82 merged、11 closed、
0 open）與 **92 個 issue**。

差別不只是數字。已合併的 PR 會變成 `main` 的 commit，commit 稽核照得到；**未合併就關閉的
PR 不會**——它們永遠不會出現在 commit 清單裡，只有查 PR 才看得到。上游是 macOS 優先，被關掉的
那幾筆恰好是 Windows 專屬修正，而本 fork 是 Windows-only。

### 11 筆 closed-未合併 PR 的逐筆結果

| PR | 內容 | 本 fork 實查 |
| --- | --- | --- |
| [#71](https://github.com/aqua5230/usage/pull/71) Windows status-file lock 靜默退化成沒有鎖 | `msvcrt.locking(LK_NBLCK)` 遇到競爭立刻丟 `OSError`，而外層 `except OSError: pass` 把它當成「這個檔案系統不支援鎖」吞掉，直接進臨界區 | **已有，設計相同**：`usage_statusline.py:244` 的 `_acquire_msvcrt_lock()` 以 deadline 輪詢 `LK_NBLCK`，並用 errno 區分「競爭」與「真的不支援」。 |
| [#69](https://github.com/aqua5230/usage/pull/69) 系統匣啟動時的幽靈視窗 | pywebview 的 `resize()`/`move()` 帶 `SWP_SHOWWINDOW`，在 `on_loaded` 裡放置還隱藏著的視窗會把空白面板拖上螢幕；另缺單一實例保護 | **兩半都已有**：`wintray.py:729` 的 `on_loaded` 註解就寫著這個原因，放置改在 `show_panel()`；`_acquire_single_instance_lock()` 與 `wintray_already_running`（i18n 兩語）都在。 |
| [#95](https://github.com/aqua5230/usage/pull/95) 面板尺寸與在地化 | 昨日專案用量、Codex 一般週限額、Windows 面板高度隨版面/字型/DOM 變化 | **內容與已記錄的 commit 候選 `6e43f4d`／`f445f5b` 重疊**（見上方 Skipped 表），且它同時動 `menubar_refresh.py`、`menubar_state.py` 這類本 fork 沒有的 macOS 檔。維持該筆候選的結論與觸發條件，不另外處理。 |
| [#18](https://github.com/aqua5230/usage/pull/18) 追蹤 Gemini（Antigravity）用量 | 新增 `gemini_loader.py`、8 個主題面板的 Gemini 卡片、macOS menu bar 自訂 | **能力已有，實作不同**：本 fork 是 `providers/agy_loader.py`＋`providers/agy_quota_probe.py`。它動的 8 個主題面板本 fork 已於 v0.40.0 移除，`menubar.py` 也不存在。 |
| [#2](https://github.com/aqua5230/usage/pull/2)／[#3](https://github.com/aqua5230/usage/pull/3) Windows tkinter 桌面小工具 | 上游早期的 Windows widget 提案 | **不適用**：本 fork 的 Windows 實作是 pystray＋pywebview 的系統匣與面板，早已超過這兩筆的範圍。 |
| #49／#51／#52／#85／#86 | Dependabot 的 codeql-action 升版 | **不適用**：本 fork 有自己的 Dependabot 與依賴新鮮度檢查。 |

**結論：11 筆都不需要動作**，但這是**查過之後**的結論，不再是「PR 這條線沒有東西可追」那種
從錯誤前提推出來的結論。

### 92 個 issue：抽查三筆最可能命中的

全數為 closed。逐筆讀標題後挑出三筆可能觸及本 fork 行為的，實查結果都是已涵蓋：

- **#74**「Claude quota is structurally unavailable to users who never open the terminal TUI」
  → 本 fork 已實作 `plan-usage-history.json` 接管（見 CHANGELOG「只使用 Claude Desktop 時」）。
- **#46**「Session resume picks up isMeta-injected content」→ `usage_session_resume.py:390`
  已過濾 `isMeta`，並有 `tests/test_session_resume.py:794` 釘住。
- **#35／#36**「隱藏 Claude Code 用量／隱藏時不要顯示錯誤」→ `hide_claude` 已實作並串到面板
  payload（`panels/payload.py:183`），tooltip 也已在本輪修正中一併處理。

### 水位

- commit：`6d74e58`（本日稍早已推進）
- **PR：#106**、**issue：#92**（首次以 `--state all` 查過並逐筆判斷）
- 判準補一條：**PR 與 issue 一律 `--state all`**。未合併就關閉的 PR 永遠不會進 commit 清單，
  而那正是上游拒收、但對 Windows-only fork 可能最有價值的一類。
