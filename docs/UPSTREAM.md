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
      "last_reviewed": "5269fd4",
      "last_merged": "2588cc0",
      "note": "審視至 5269fd4（upstream/main 的 tip，2026-08-22）。issue #9 開出時列 2 筆，實際處理時已累積 24 筆，全數逐筆審完並記錄於下方 Skipped 表。本輪採用 2 筆：`5391aad`（系統匣提示文字：已用%／Antigravity 段落／Claude 併行，本 fork 三個問題全中）與 `2588cc0` 的**遮罩三項**（分享報告的未遮罩 CSV 內嵌、圓餅圖圖例 lg-name、insights 句中專案名——本 fork 同樣全中，屬實質資料外洩）。`2588cc0` 的檔案權限半部為 POSIX chmod，Windows-only fork 以 ACL 為機制，不適用；JSONL 上限與 RecursionError 保護列候選。"
    }
  }
}
```
<!-- sync-points:end -->

## 2026-08-22：上游的 PR、issue、分支盤點

一次盤點，之後只看增量，不要每次重新評估。

| 面向 | 當時狀態 | 結論 |
| --- | --- | --- |
| Open PR | **0** | 上游不用 PR 流程，改動直接進 `main`。所以本 fork 的審查單位就是 commit，PR 這條線沒有東西可追。 |
| Open issue | **0** | 沒有待處理的上游 issue。下次檢查時若出現，判準是：**只有會改變「本 fork 要驗什麼」的才追**（Windows 行為、資料外洩、授權），純功能請求會隨 commit 進來。 |
| 分支 | 7 個 | 都是上游自己的工作分支，`main` 以外沒有本 fork 追蹤的線。fetch 只取 `main`。 |

水位：**PR ≤（無）、issue ≤（無）、分支盤點日 2026-08-22**。下次只要確認「有沒有新的 PR／issue 出現」，
不必重讀已經看過的清單。commit 的水位仍由上面 sync-points 的 `last_reviewed` 管。

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
| main | `5391aad` | fix(wintray): 系統匣提示文字三處修復 | 2026-08-22 | **採用**。三個子項在本 fork 全中：(1) `build_tooltip` 顯示 `100 - percent`，而面板走 `percent_used`——同一個問題兩處給不同數字；(2) 完全沒有 Antigravity 段落，儘管本 fork 支援它；(3) Claude 的 Session／Weekly 各佔一行，與 Codex 的併行格式不一致。第四個子項（更新彈窗清理 Markdown）**已涵蓋且做法更好**：本 fork 的 MessageBoxW 刻意完全不放 release notes（沒有捲軸、notes 就在對話框願意開的那一頁），程式碼裡已有註解說明。另補兩條測試：`hide_claude` 開啟時 tooltip 不得把 Claude 放回來、`percent is None` 不得編造數字。 |
| main | `2588cc0` | fix(security): 修補分享報告遮罩失效與本機檔案權限 | 2026-08-22 | **遮罩三項採用，權限半部不適用，JSONL 上限列候選**。遮罩失效在本 fork 同樣成立且是實質外洩：勾了「遮罩專案名稱」匯出的 HTML，`downloadHtml` 直接序列化整份 DOM，而未遮罩的 `csvData` 就內嵌在報告自己的 script 裡跟著送出去，收檔者按報告內建的 CSV 鈕即可取回真實專案路徑。修法比照上游拆成獨立 `application/json` 節點、遮罩匯出時移除未遮罩節點、JS 端 fallback；但**遮罩標記改用排名而非名稱**（`data-mask-index`），因為把真名放進屬性一樣會跟著匯出檔外流。圖例 `lg-name` 與 insights 句中專案名同樣補上遮罩，且三處編號一致。新增 `tests/test_html_report_masking.py` 8 條把這些性質釘住。權限半部（0700／0600、copy2→copy+chmod、quarantine mode）是 POSIX chmod，本 fork 為 Windows-only、使用者目錄由 ACL 隔離，**不適用**；`3cb368d` 的 Windows 權限守衛測試隨之不適用。JSONL 單行上限與 RecursionError 保護與平台無關，**列候選**，需自帶測試另行處理。 |
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
