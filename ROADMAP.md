# agentdeck 產品路線圖

繁體中文 · [English](ROADMAP.en.md)

更新日期：2026-07-31

規劃基準：`v0.31.2`

這份路線圖描述建議的產品方向、里程碑順序與完成條件。版本號代表依賴順序，不是不可調整的日期承諾；當前缺陷仍以 [`REVIEW_Claude.md`](REVIEW_Claude.md) 為準，已完成的歷史則看 [`CHANGELOG.md`](CHANGELOG.md)。

## 產品判斷

agentdeck 最有價值的方向，不是成為「又一個 token 圖表」，也不是用 provider 數量或主題數量競賽。它應該成為：

> **Windows 上本機優先、可解釋、可操作的 AI 編碼工作駕駛艙。**

使用者真正要完成的工作有三步：

1. **看見**：目前還剩多少額度、資料多久以前更新、服務是否異常。
2. **理解**：數字來自哪裡，為什麼缺資料，哪一個環節失敗。
3. **採取行動**：修復 hook、調整工作節奏、產生報告、召開 AI 圓桌，不必離開目前工作。

十二個月的理想狀態：

```text
目前：功能完整但仍有發版與 UI 邊角
  │
  ├─ v0.31.x 先消除已知不可信狀態
  ├─ v0.32   每個資料來源都能說明健康狀態與修復方式
  ├─ v0.33   狀態與診斷可供 PowerShell／其他本機工具使用
  ├─ v0.34   AI 圓桌能產生可搜尋、可續用的工作產物
  └─ v0.35   新資料來源與發版流程有明確契約
       │
       ▼
v1.0：使用者可以信任數字、信任更新，也知道出錯時怎麼救
```

## 市場訊號與差異化

同類工具已證明幾件事：

| 專案 | 已證明的需求 | agentdeck 應該學什麼 |
|---|---|---|
| [CodexBar](https://github.com/steipete/codexbar) | 多 provider、即時額度與本機成本檢視有需求 | 學習資料來源契約與狀態表達，不追求相同的 provider 廣度 |
| [ccusage](https://github.com/ccusage/ccusage) | CLI 報告、時間區塊與跨工具統計有需求 | 讓 agentdeck 的核心狀態也能穩定輸出給腳本 |
| [ccboard](https://github.com/florianbruniaux/ccboard) | 使用者需要從額度進一步看到 session、設定與診斷 | 強化「為什麼」與修復流程，不複製大型管理介面 |
| [Usage Monitor for Claude](https://github.com/jens-duttke/usage-monitor-for-claude) | Windows 單一可攜式程式、零設定與明確 stale 狀態很有吸引力 | 把首次啟動、資料缺失與更新失敗做得更直接 |

agentdeck 的差異化應維持四點：

- **Windows-first**：系統匣、WebView2、DPI、工作列位置與 Windows 發版是真正的一等公民。
- **Local-first**：Claude Code 與 Codex 的額度只讀本機檔案，不呼叫 Anthropic／OpenAI 用量 API。
- **從監控到行動**：不只顯示數字，也提供診斷、報告、工作模式、角色與 AI 圓桌。
- **可解釋的信任**：每個數字都能回答資料來源、更新時間、是否 stale，以及失敗時下一步。

## 已有基礎，不重做

後續 issue 應先重用這些現成功能，不建立平行版本：

- Claude、Codex、Antigravity 三種額度來源都有 stale 提示與重置倒數；Claude／Codex 另有燃燒率、預測與額度系統通知。
- `--doctor`、Rich TUI、HTML／CSV／PNG 報告與 `usage_cli.py report`。
- AI 圓桌的中止、輪間引導、匿名標籤、共識計票、token 估算，以及 JSON／Markdown 自動存檔。
- AI 人才市場的本機 persona 安裝、備份、drift 偵測與還原。
- 六道品質閘門、CodeQL、ClusterFuzzLite、PyInstaller 資源測試、release ZIP 與 SHA-256。

路線圖中的「新增」原則上是補齊這些能力的使用者閉環，例如讓現有討論存檔可搜尋，而不是再寫另一套存檔格式。

## 優先順序

未來工作依下列順序排：

1. **發版與資料正確性**
2. **錯誤可見性與可修復性**
3. **可測試、可腳本化的穩定介面**
4. **AI 圓桌的工作產物與復原能力**
5. **新 provider、更多主題與其他擴張**

功能看起來新，不代表比「建出的 exe 版號正確」更重要。後者沒有截圖效果，卻是使用者信任整個產品的地基。

## v0.31.x：先把可信度缺口關掉

目標：不再保留已知、可重現的產品與發版缺陷。

### 工作

- 修正 [`REVIEW_Claude.md`](REVIEW_Claude.md) P6：`scripts/build_windows.ps1` 在建置前清除舊 `agentdeck.egg-info`／`usage.egg-info`，建置後以 `agentdeck.exe --doctor` 驗證版號等於 `pyproject.toml`；對既有的乾淨 Windows release workflow 補 exe／tag 版號比對，保留既有 SHA-256 流程。
- 修正 P5：AI 圓桌參與者卡在 900×640 下至少完整顯示一張卡；清單可以捲動，但 model／persona 不得被容器垂直裁切。
- 建立 WebView2 實機矩陣：100%、150%、225% DPI，各自檢查 900×640 與 1280×800。
- 實機證據固定記錄 Windows build、WebView2 Runtime 版本、DPI、邏輯／實體解析度、結果 checklist 與問題截圖，存入版本化的 `docs/release-evidence/`；`REVIEW_Claude.md` 只連結當前未解項目。
- 清除文件中已發布內容仍留在 `Unreleased`、舊 review 檔名與功能比較表不實等漂移。

### 完成條件

- 本機與 GitHub runner 建出的 exe 都回報正確版本。
- `vX.Y.Z` tag、`pyproject.toml`、exe `--doctor` 與 release asset 四者一致。
- AI 圓桌在實機矩陣沒有關鍵控制項裁切，也沒有非預期水平捲軸。
- 六道閘門全綠，並將 P5、P6 從 `REVIEW_Claude.md` 移除。

## v0.32.0：可信的資料來源與修復流程

目標：任何 `--`、stale 或查詢失敗都能說清楚原因，使用者不用猜。

### 工作

- 建立共用 `ProviderHealth` 狀態模型，至少包含 `ready`、`stale`、`missing`、`misconfigured`、`unavailable`、`error`。
- 讓 Claude、Codex、Antigravity 的卡片與 `--doctor` 共用同一套健康狀態與修復建議，避免 UI 與 CLI 各說各話。
- 擴充既有首次啟動與 stale 判斷：統一辨識「尚未用過工具」「hook 未安裝」「檔案太舊」「CLI 未登入」「服務暫時失敗」。
- 評估 Codex plugin／`app-server` 的事件驅動來源，寫成決策記錄；JSONL 掃描仍保留為零安裝 fallback，不為追求即時性犧牲可靠性。
- 建立效能基準：冷啟動、90 天紀錄掃描、檔案事件後刷新延遲與記憶體峰值。

### 完成條件

- 每個空白或 stale 狀態都有「原因、最後更新時間、下一步」。
- 離線、損壞 JSONL、權限不足、尚無資料與舊 hook 都有測試。
- UI 與 `--doctor` 對同一狀態給出一致判定。
- Codex 事件驅動方案有採用／不採用決定與實測依據，不只停在想法。

交付順序：健康狀態模型 → 三個 provider 投影 → UI／doctor 共用 → 首次啟動修復 → Codex 事件來源評估 → benchmark。

## v0.33.0：可腳本化的本機駕駛艙

目標：讓 agentdeck 的可信狀態可以被 PowerShell、排程與其他本機工具重用。

### 工作

- 新增正式產物可用的 `agentdeck.exe --status --json`（從原始碼時為 `main.py --status --json`），由 `main.py` 路由到中立 leaf module；輸出版本化 schema，包含 provider 額度、資料健康、更新時間與服務狀態。
- 新增 `main.py --doctor --json`，供 issue 回報與自動診斷使用；預設必須遮蔽使用者名稱、專案路徑與 token。
- 在報告與 JSON 中標示資料來源與估算性質，清楚區分「官方額度」「本機紀錄推算」「價格表估算」。
- 加入只讀的 PowerShell 範例，例如額度接近門檻時顯示本機通知；不自動切換帳號、不代替使用者執行模型請求。
- 為 JSON schema 建立相容性測試與版本政策。

### 完成條件

- 腳本不必解析人類可讀文字。
- JSON 輸出預設不洩漏絕對路徑、憑證、prompt 或對話內容。
- schema 破壞性變更依 SemVer 處理，至少有一份 PowerShell smoke test。
- 無 UI 的環境也能完成狀態檢查與問題回報。

交付順序：中立狀態投影 → `--status --json` → `--doctor --json` → redaction 與 schema 測試 → PowerShell smoke。

## v0.34.0：把 AI 圓桌變成可續用的工作產物

目標：圓桌不只「跑完一次」，而是能被搜尋、重開、比較與轉成下一步工作。

### 工作

- 為既有 `~/.agentdeck/discussions/*.json`／`*.md` 存檔加入歷史索引、搜尋與「在檔案總管開啟」。
- 保留既有某一參與者失敗、其他參與者繼續的行為，並確保失敗或取消後仍持久化已完成結果；重新開啟時要看得懂中斷原因。
- 回合數維持硬上限；provider 有原生 max-output 參數時下推。token 預算在每個 turn 邊界檢查並於開始前說明，單一 turn 仍可能超出預估值。
- 盤點既有 CLI 缺失、登入失效、partial failure、malformed output 與取消測試，再補齊錯誤與復原矩陣。
- 維持附件唯讀，清楚顯示允許讀取的資料夾與圖片，不擴張成任意檔案寫入或自動執行平台。

### 完成條件

- 歷史討論可以依日期、主題、參與者與結果搜尋。
- 一個參與者失敗不會讓其他已完成內容消失。
- 回合硬上限與 token 預算語意在啟動前可見；到 turn 邊界超過預算時安全停止並存檔。
- 存檔格式有 migration 測試，舊版討論仍可讀。

交付順序：失敗／取消存檔保證 → 歷史索引與搜尋 → 重開檢視 → 預算邊界 → migration 與復原矩陣。

### 後續候選（不阻擋 v0.34.0）

- 可重用的討論範本：程式碼審查、架構取捨、事故復盤、發布決策。
- 進階摘要結構：「決定、不同意見、未解問題、下一步」，並連回原回合。

只有歷史索引與重開流程實際被使用後，才決定是否把這兩項排進後續 MINOR，避免 v0.34 同時承擔太多新互動。

## v0.35.0：可維護的擴充與發版

目標：增加能力時，不讓 `wintray.py`、打包流程或資料來源判斷持續膨脹。

### 工作

- 只有在現有三種來源的重複已可量化時，才抽出最小 `ProviderAdapter` 契約；不先建一套空泛 plugin framework。
- 新 provider 必須先通過資格門檻：Windows 可用、來源合法、失敗可辨識、可離線降級、測試不碰真實憑證。
- 產生依賴清單或 SBOM，讓 PyInstaller bundle 裡實際帶了什麼可以稽核。
- 將既有 SHA-256 與 v0.31.x 新增的 exe／tag 驗證整理成同一份 release evidence manifest，不再另建一條平行發版流程。
- 建立最近兩個 MINOR 版本的偏好、hook 與存檔 migration 測試。
- 將 UI 實機矩陣與 release smoke 寫成每次發版的固定 checklist。

### 完成條件

- 新 provider 不需要把商業邏輯塞進 `wintray.py`。
- release asset、checksum、SBOM 與版本 evidence manifest 可由同一個 workflow 重建。
- 升級與回復流程至少覆蓋最近兩個 MINOR 版本。

## v1.0.0 的門檻

`1.0.0` 不以功能數量決定，而以信任合約是否穩定決定。

- `REVIEW_Claude.md` 沒有未解、可重現的產品缺陷；環境限制則有清楚的偵測與處置。
- Windows 10、Windows 11，以及 100%／150%／225% DPI 的核心流程完成實機 smoke。
- tag、程式版號、exe 版號與 release asset 可重現地一致。
- Claude、Codex、Antigravity 的缺資料、stale、離線與登入失效都有明確 UX。
- `status --json` 與 `doctor --json` schema 宣告為 v1，並有相容性測試。
- 最近兩個 MINOR 版本的設定、hook、快取與討論存檔可安全升級。
- 所有使用者主動觸發的動作都有成功／失敗回饋，沒有已知靜默失敗。
- 隱私邊界、實際連網範圍、AGPL 發佈內容與安全回報流程都有自動或人工驗收證據。

## 衡量方式

本專案不加入遙測。以下指標由測試、benchmark、release workflow 與人工 smoke 蒐證：

| 指標 | 目標 |
|---|---|
| 首次啟動到得到有效資料或明確修復指引 | 5 分鐘內 |
| 主動操作的靜默失敗 | 0 |
| tag／pyproject／exe／asset 版號一致率 | 100% |
| 900×640 核心控制項於 100%／150%／225% DPI 的關鍵裁切 | 0 |
| 損壞或不完整本機資料造成 app crash | 0 個已知案例 |
| 問題回報所需診斷 | 一個 `--doctor` 指令完成 |

效能數字先在 v0.32 建立基準，再把可重現的數字寫成 gate；不要先憑感覺訂一個漂亮但沒有測量方法的毫秒數。

## 主要風險、依賴與防線

Windows 10、多 DPI 與 WebView2 視覺驗收需要維護者提供真實桌面環境，GitHub runner 不能取代。自動化證據放在 CI／release artifact，人工 checklist 與截圖放在版本化的 `docs/release-evidence/`；`REVIEW_Claude.md` 只引用當前未解項目的證據，效能基準則存進 repo 的 benchmark fixture 或報告。

| 風險／依賴 | 可能後果 | 防線 | 驗證證據 |
|---|---|---|---|
| Claude／Codex 本機檔案格式改變 | 額度突然空白或解析錯誤 | fixture、schema 偵測、舊格式 fallback、明確 health 狀態 | parser tests、fuzz 結果 |
| Windows 10／11、DPI 與 WebView2 組合差異 | 控制項裁切、視窗跑到螢幕外 | 純邏輯測試加三種 DPI 實機矩陣 | `docs/release-evidence/` checklist／截圖 |
| 舊 metadata 或快取污染建置 | tag 正確但 exe 版號錯誤 | 建置前清理、乾淨 runner、建置後 exe 版號 smoke | release evidence manifest |
| provider 只在 turn 結束後回報 usage | token 預算可能晚一個 turn 才停止 | 回合硬上限、原生 max-output、turn 邊界檢查與明確說明 | discussion budget tests |
| CLI 登入與參數持續變動 | AI 圓桌單一參與者失敗 | 能力偵測、adapter 隔離、每個 turn 獨立失敗與存檔 | adapter／partial-failure tests |
| 討論存檔 schema 演進 | 新版讀不到舊討論 | schema version、最近兩個 MINOR migration fixture | archive migration tests |
| 診斷輸出包含私人路徑或對話 | issue 回報時外洩資料 | 預設遮蔽、敏感字串測試、明確 opt-in 才輸出更多 | redaction tests |
| 功能持續增加造成產品失焦 | 維護成本上升、核心可靠性停滯 | 固定優先序、新 provider 資格門檻、明確不做清單 | roadmap／issue review |

## 明確不做

- 不恢復 macOS 支援；macOS 由上游維護。
- 不呼叫 Anthropic／OpenAI 用量 API 取得 Claude Code 或 Codex 額度。
- 不建立雲端帳號、團隊後台或上傳使用者對話內容。
- 不做自動多帳號切換、憑證代理或模型請求路由。
- 不以支援最多 provider 為目標；沒有可靠 Windows 資料來源就不加入。
- 不發佈 wheel／PyPI 套件；正式產品維持 Windows PyInstaller bundle。
- 不讓 AI 圓桌取得任意寫檔或執行命令的權限。

## 執行規則

每個里程碑都遵守同一個完成流程：

1. 先把可驗收的使用者結果寫成 issue。
2. 有取捨的決定寫進 `docs/DECISIONS.md`。
3. 純邏輯用自動化測試，WebView2／系統匣／對話框用 Windows 實機 smoke。
4. `pwsh tools/dev_check.ps1` 六道閘門全綠。
5. 同步中英文文件與 changelog。
6. push 後確認 GitHub CI、CodeQL 與必要的 release workflow 成功。
7. 只在完成條件有證據時，才把路線圖項目標成完成。

## 接下來三件事

1. **P6 發版版號防護**：先修 `build_windows.ps1` 的 egg-info 清理與 exe 版號 smoke。這是最直接的供應鏈可信度缺口。
2. **P5 AI 圓桌垂直裁切**：調整容器高度／捲動策略，跑 900×640 與三種 DPI 的真實 WebView2 驗證。
3. **ProviderHealth 設計與第一版**：先讓 Claude、Codex、Antigravity 對「可用、太舊、沒設定、失敗」說同一種語言，再考慮更多 provider。
