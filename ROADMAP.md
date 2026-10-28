# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `2a8a662b11b8` 查的快照，開工前先重查 GitHub。

## 現況

Windows 系統匣駕駛艙（Claude Code、Codex、Antigravity 額度、AI 圓桌、報告），私有，從上游 [`aqua5230/usage`](https://github.com/aqua5230/usage) 分出後獨立維護，定位與邊界見 [`docs/DECISIONS.md`](docs/DECISIONS.md) D-01。健康：`main` 的 CI、CodeQL、Scorecard、ClusterFuzzLite batch、上游更新檢查最近一次皆 success（2026-10-27／28）；open PR 0、Dependabot 與 Code scanning 告警 0；open issue 1（#34，上游更新檢查，審視 `310d779`、`9723c04`）；最新 release 是 v0.42.1，`pyproject.toml` 已是 0.42.2、`CHANGELOG.md` 的 `[Unreleased]` 另有已合併未發版的修正（`gh` 實查，2026-10-29）。上游已把根目錄模組搬進套件，無法整段 merge，一律手工移植（`docs/UPSTREAM.md`）。卡住的是需要真實 Windows 桌面的驗證與發版決定，不是程式缺陷。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 處理上游更新檢查 #34：逐筆判斷後推進 `docs/UPSTREAM.md` 的標記 | 上游 `310d779` 把 `setuptools` 升到 84.2.1（GHSA-xmj3-9gf7-h52w），本 fork 的 `uv.lock` 已是同一版，應記為「已等價、不採用」而不是漏看；`#262` 也要記入已審視範圍 | `docs/UPSTREAM.md` 的 `last_reviewed` 與 `tickets.reviewed_pr_through` 已推進、Skipped 表補一列含理由、`docs/DECISIONS.md` 補一句；下次「上游更新檢查」workflow 不再開新 issue、#34 關閉；重新確認 `uv.lock` 的 `setuptools` 版本不低於上游該筆修正版 | Claude Sonnet | Issue #34；`uv.lock:574-577`（`setuptools` 84.2.1）；`docs/UPSTREAM.md:28-47`（sync points）、`docs/UPSTREAM.md:16-24`（處理流程） |
| 決定並發佈下一版（含 `[Unreleased]` 的修正與 0.42.2 之後的 runtime 修正） | `pyproject.toml` 是 0.42.2 而最新 release 是 v0.42.1；`[Unreleased]` 有價格表、專案目錄解碼、hook、WebView2 設定檔等修正，尚未讓使用者拿到 | 維護者決定版號後：`CHANGELOG.md` 與 `CHANGELOG.en.md` 把 `[Unreleased]` 切成版本段；`python scripts/check_release_version.py SanHsien/agentdeck <tag>` 通過；推 `v*` tag 後 Release workflow success；下載的 exe 以 `--doctor` 回報的版本等於 tag，SHA-256 與 release asset 一致 | 維護者 | `pyproject.toml:3`；`gh release list -R SanHsien/agentdeck`（最新 v0.42.1）；`CHANGELOG.md:9-25`；`.github/workflows/release.yml` |
| Windows 實機 smoke：WebView2 在 100%／150%／225% DPI、900×640 與 1280×800 下的系統匣與面板，以及 AI 圓桌 | 自動化測試取代不了真實桌面；`docs/release-evidence/` 目前只有 2026-07-31 的圓桌版面一份，發版與 v1.0 都需要新的實機證據 | 新增一份 `docs/release-evidence/<日期>-smoke.md`：記錄 Windows build、WebView2 Runtime 版本、DPI、邏輯／實體解析度、逐項 checklist 結果與問題截圖；發現的缺陷各開 issue | 維護者 | `docs/release-evidence/2026-07-31-discussion-layout.md`（唯一一份）；`REVIEW_Claude.md`「環境」；接續開發報告（2026-10-25）「需要維護者決定：Windows 實機 smoke」 |
| 新增 `main.py --status --json`（打包後 `agentdeck.exe --status --json`），輸出版本化 schema | 腳本與排程目前只能解析人類可讀文字；`provider_health.py`、`provider_probe.py` 已有統一的健康狀態，可直接投影 | schema 含 provider 額度、資料健康、更新時間；預設不輸出使用者名稱、專案路徑、token、prompt 或對話內容（有 redaction 測試）；schema 相容性測試加一條 PowerShell smoke；`tools/dev_check.ps1` 六道閘門全綠；`CHANGELOG.md` 與英文版同步 | Claude Sonnet | `main.py:198-234`（現有旗標無 `--status`）；`provider_health.py`、`provider_probe.py`、`doctor.py:20,66`（`doctor` 已用 `collect_provider_health`） |
| `autoresume_scheduler.cancel()` 在 zh-TW（OEM 碼頁）認得「找不到」 | 以 UTF-8 解碼 `schtasks` 輸出，中文系統認不出，使用者手動刪掉註冊任務後每個 tick 都叫一次 `schtasks` 並記警告 | 新增測試：以 OEM 碼頁編碼的「找不到」輸出視為成功；`_run` 改用 `encoding="oem"` 或先 `is_scheduled()`；`pytest tests -q` 與六道閘門綠 | Claude Sonnet | `autoresume_scheduler.py:160-168`；深掃報告（2026-10-26）「刻意不修／觀察清單」第一項 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| `main.py --doctor --json`，供 issue 回報與自動診斷 | `--status --json` 的 schema 合併後（共用同一個中立狀態投影） | 輸出版本化 JSON；預設遮蔽使用者名稱、專案路徑與 token（有測試）；無 UI 環境可跑；一個指令即可完成問題回報所需診斷 | Claude Sonnet | `doctor.py`；`main.py:227-231`（現有 `--doctor` 為人類可讀輸出） |
| AI 圓桌歷史：索引、搜尋、重開與「在檔案總管開啟」 | 維護者決定下一輪投入圓桌；先確認失敗或取消後已完成的回合仍完整存檔 | 以日期、主題、參與者與結果搜尋 `~/.agentdeck/discussions/`；重開時看得懂中斷原因；存檔格式有 migration 測試，舊版討論仍可讀；回合硬上限與 token 預算在啟動前可見 | Claude Opus | `council/discussion_bridge.py:63,992-993`（存檔位置，未見索引或搜尋程式）；`council/discussion_session.py` |
| Codex 事件驅動來源評估（plugin／`app-server`）與效能基準（冷啟動、90 天紀錄掃描、檔案事件後刷新延遲、記憶體峰值） | Codex 本機 JSONL 格式變動造成額度空白，或維護者要求更低的更新延遲 | 寫成 `docs/DECISIONS.md` 的採用／不採用決定與實測數字；JSONL 掃描保留為零安裝 fallback；基準可重跑且有 fixture | Claude Opus | 儲存庫內查無 benchmark 程式（`grep -rn benchmark` 只命中舊路線圖）；`docs/DECISIONS.md` 無 Codex 事件來源決策 |
| Antigravity 額度改打正式主機 `cloudcode-pa` | 維護者決定接受「OAuth token 送往另一個 Google 端點」，或實測 Gemini 額度確實缺失 | 實機以真實帳號驗證 Gemini 額度出現；`SECURITY.md` 與 `SECURITY.en.md` 的端點清單同步更新；`docs/UPSTREAM.md` 該列標為已決定並寫理由 | 維護者 | `docs/UPSTREAM.md:69`（待維護者決定）；`providers/agy_quota_probe.py:48` |
| 宣告 v1.0.0：SBOM／依賴清單、release evidence manifest、最近兩個 MINOR 的設定、hook 與存檔 migration 測試 | 近期的實機 smoke 完成，且 `--status --json`、`--doctor --json` schema 已有相容性測試 | 同一個 workflow 可重建 release asset、SHA-256、SBOM 與版本 evidence manifest；migration 測試涵蓋最近兩個 MINOR；Windows 10 與 11 核心流程實機 smoke 有證據；`REVIEW_Claude.md` 無未解的可重現缺陷 | Claude Opus | `.github/workflows/release.yml`（目前無 SBOM 步驟）；`REVIEW_Claude.md`（未解項為 P4） |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 恢復 macOS 支援；發佈 wheel／PyPI 套件 | 本 fork 專注 Windows，macOS 由上游維護；正式產品是 PyInstaller bundle（`docs/DECISIONS.md` D-01、`REVIEW_Claude.md`「發佈模型」） | 維護者明確改變產品範圍 |
| 呼叫 Anthropic／OpenAI 用量 API；雲端帳號或團隊後台；自動多帳號切換、憑證代理；讓 AI 圓桌取得任意寫檔或執行命令的權限 | 核心不變式是只讀本機檔案、零用量 API 呼叫、不上傳對話（`REVIEW_Claude.md`「已確認正常」） | 官方提供不需憑證代理的本機額度來源，且維護者重寫隱私邊界 |
| 加固上游 `5ab47cd` 的三個 native 呼叫（#202） | 上游單一機器回報、已以 not planned 關閉；其 UI Automation 掃描在本 fork 不存在 | 本 fork 出現鎖定／解鎖後閃退，或有人回報 `python313.dll` 存取違規（`docs/UPSTREAM.md:68`） |
| 為 `setup_hook._setup_codex` 在 `config.toml` 的 `tui` 為 inline table 或點號鍵時補上 TOML 編輯器 | 現有字串編輯對這種寫法是 no-op 卻印「已設定」；修正需要真正的 TOML 編輯器，成本高於極少數使用者的收益 | 有使用者回報該 config 形式，或專案已因其他理由引入 TOML 寫入依賴 |

## 維護方式
fork 追蹤上游 `aqua5230/usage`：「上游更新檢查」workflow 每天 02:00 UTC 比對 `docs/UPSTREAM.md` 的 `last_reviewed`，有新項目就開／更新 issue；逐筆判斷後採用（手工移植並補測試，推進 `last_merged` 與 `last_reviewed`）或不採用（只推進 `last_reviewed`、補 Skipped 表與理由）。failure 代表上游有未審項目，不是工具壞。依賴新鮮度每月 1 日檢查；發版採 SemVer（D-05）。查現況：`gh issue list -R SanHsien/agentdeck`、`gh api repos/SanHsien/agentdeck/dependabot/alerts?state=open`、`gh run list -R SanHsien/agentdeck -b main -L 8`。
