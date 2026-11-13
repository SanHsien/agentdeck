# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-11-08 依 `main` `b38f823f615f` 查的快照，開工前先重查 GitHub。

## 現況

`--status --json` 與 `--doctor --json` 已提供 schema v1，兩者共用中立狀態投影；後者另附預設遮蔽敏感資訊的環境與 hook 診斷。

Windows 系統匣駕駛艙（Claude Code、Codex、Antigravity 額度、AI 圓桌、報告），私有，從上游 [`aqua5230/usage`](https://github.com/aqua5230/usage) 分出後獨立維護，定位與邊界見 [`docs/DECISIONS.md`](docs/DECISIONS.md) D-01。健康（`gh` 實查，2026-11-08，`main` `b38f823`）：CI、CodeQL、Scorecard 最近一次 push 執行皆 success（2026-11-02）；ClusterFuzzLite batch（2026-11-07 排程）與上游更新檢查（2026-11-07 排程）success；依賴新鮮度檢查最近一次 success（2026-11-01，產生 #35）；open PR 0；Dependabot 告警 0；Code scanning 告警 0；open issue 2：#36（上游更新檢查，2026-11-02 開，見下方近期列）與 #35（依賴新鮮度檢查，D-39 已處理，推上 main 後關閉）；#34 已於 2026-10-31 關閉。最新 release 是 v0.42.1，`pyproject.toml` 已升到 0.43.0、`CHANGELOG.md` 已切出 `[0.43.0]`，待建立 tag／release。上游已把根目錄模組搬進套件，無法整段 merge，一律手工移植（`docs/UPSTREAM.md`）。卡住的是需要真實 Windows 桌面的驗證與發版決定，不是程式缺陷。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 繼續上游追平（issue #36）：`d044edf4` 之後 30 筆 commit（2026-11-13 本機 ref 快照到 `042b8c56`，非遠端即時數字） | 第五批審完 5 筆，部分移植 Classic 樣式與四款主題的 Codex 更新時間提示。last_reviewed 為 `d044edf4`，last_merged 為 `3f26ca64`；PR 審至 #296／issue #273 | 從 `25493823` 起逐筆讀 patch，接續 PR #297 起內文與 state=all issue；依 `docs/UPSTREAM.md` 記採用／Skipped 理由，手工移植並補紅轉綠測試，只推進已審完的 last_reviewed／last_merged 與 ticket 審視範圍；`tools/dev_check.ps1` 全綠。確認四款主題的 Codex 提示、Classic 深淺色版面，以及第四批 Windows 通知與設定失敗提示；push 後確認 #36 由上游檢查更新或關閉 | Codex | `docs/UPSTREAM.md` 2026-11-13 第五批；`docs/DECISIONS.md` D-40 |
| 發佈 v0.43.0 的 GitHub Release | v0.43.0 的程式碼已在 `main`（f2f2e21），CI 綠；Release 沒發，原因是代理工具的權限檢查擋下 `gh release create`。`.github/workflows/release.yml` 由 tag push 觸發，而且 Release 要先存在；使用者最後一次拿到的仍是 v0.42.1 | 維護者執行：`python scripts/check_release_version.py SanHsien/agentdeck v0.43.0 && gh release create v0.43.0 --repo SanHsien/agentdeck --target f2f2e214a6a7dc8abc76e7be4c2862c47f1ecefd --title v0.43.0 --notes-file <CHANGELOG 0.43.0 段>`（建立 release 時一併建立 `v0.43.0` tag，由 tag push 觸發 Release workflow）；之後看 Release workflow 是否 success，並驗 asset 的 SHA-256 與下載的 exe（`--doctor` 回報 0.43.0）一致；驗收完這列刪掉 | 維護者 | `pyproject.toml:3`；`CHANGELOG.md` `[0.43.0]`；`.github/workflows/release.yml`；`docs/DECISIONS.md` D-38 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| Windows 實機 smoke：WebView2 在 100%／150%／225% DPI、900×640 與 1280×800 下的系統匣與面板，以及 AI 圓桌 | 需要真實 Windows 桌面互動（規劃與派工 session 禁止做桌面互動的 live 測試），自動化測試取代不了；`docs/release-evidence/` 目前只有 2026-07-31 的圓桌版面一份 | 有一個可以互動操作桌面（可調 DPI）的 session 時：新增 `docs/release-evidence/<日期>-smoke.md`，記錄 Windows build、WebView2 Runtime 版本、DPI、邏輯／實體解析度、逐項 checklist 結果與問題截圖；發現的缺陷各開 issue | Claude Sonnet（桌面 session） | `docs/release-evidence/2026-07-31-discussion-layout.md`（唯一一份）；`REVIEW_Claude.md`「環境」 |
| AI 圓桌歷史：索引、搜尋、重開與「在檔案總管開啟」 | 維護者決定下一輪投入圓桌；先確認失敗或取消後已完成的回合仍完整存檔 | 以日期、主題、參與者與結果搜尋 `~/.agentdeck/discussions/`；重開時看得懂中斷原因；存檔格式有 migration 測試，舊版討論仍可讀；回合硬上限與 token 預算在啟動前可見 | Claude Opus | `council/discussion_bridge.py:63,992-993`（存檔位置，未見索引或搜尋程式）；`council/discussion_session.py` |
| Codex 事件驅動來源評估（plugin／`app-server`）與效能基準（冷啟動、90 天紀錄掃描、檔案事件後刷新延遲、記憶體峰值） | Codex 本機 JSONL 格式變動造成額度空白，或維護者要求更低的更新延遲 | 寫成 `docs/DECISIONS.md` 的採用／不採用決定與實測數字；JSONL 掃描保留為零安裝 fallback；基準可重跑且有 fixture | Claude Opus | 儲存庫內查無 benchmark 程式（`grep -rn benchmark` 只命中舊路線圖）；`docs/DECISIONS.md` 無 Codex 事件來源決策 |
| Antigravity 額度改打正式主機 `cloudcode-pa` | 維護者決定接受「OAuth token 送往另一個 Google 端點」，或實測 Gemini 額度確實缺失 | 實機以真實帳號驗證 Gemini 額度出現；`SECURITY.md` 與 `SECURITY.en.md` 的端點清單同步更新；`docs/UPSTREAM.md` 該列標為已決定並寫理由 | 維護者 | `docs/UPSTREAM.md:69`（待維護者決定）；`providers/agy_quota_probe.py:48` |
| 宣告 v1.0.0：SBOM／依賴清單、release evidence manifest、最近兩個 MINOR 的設定、hook 與存檔 migration 測試 | 中期的實機 smoke 完成，且 `--status --json`、`--doctor --json` schema 已有相容性測試 | 同一個 workflow 可重建 release asset、SHA-256、SBOM 與版本 evidence manifest；migration 測試涵蓋最近兩個 MINOR；Windows 10 與 11 核心流程實機 smoke 有證據；`REVIEW_Claude.md` 無未解的可重現缺陷 | Claude Opus | `.github/workflows/release.yml`（目前無 SBOM 步驟）；`REVIEW_Claude.md`（未解項為 P4） |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 恢復 macOS 支援；發佈 wheel／PyPI 套件 | 本 fork 專注 Windows，macOS 由上游維護；正式產品是 PyInstaller bundle（`docs/DECISIONS.md` D-01、`REVIEW_Claude.md`「發佈模型」） | 維護者明確改變產品範圍 |
| 呼叫 Anthropic／OpenAI 用量 API；雲端帳號或團隊後台；自動多帳號切換、憑證代理；讓 AI 圓桌取得任意寫檔或執行命令的權限 | 核心不變式是只讀本機檔案、零用量 API 呼叫、不上傳對話（`REVIEW_Claude.md`「已確認正常」） | 官方提供不需憑證代理的本機額度來源，且維護者重寫隱私邊界 |
| 加固上游 `5ab47cd` 的三個 native 呼叫（#202） | 上游單一機器回報、已以 not planned 關閉；其 UI Automation 掃描在本 fork 不存在 | 本 fork 出現鎖定／解鎖後閃退，或有人回報 `python313.dll` 存取違規（`docs/UPSTREAM.md:68`） |
| 為 `setup_hook._setup_codex` 在 `config.toml` 的 `tui` 為 inline table 或點號鍵時補上 TOML 編輯器 | 現有字串編輯對這種寫法是 no-op 卻印「已設定」；修正需要真正的 TOML 編輯器，成本高於極少數使用者的收益 | 有使用者回報該 config 形式，或專案已因其他理由引入 TOML 寫入依賴 |

## 維護方式
fork 追蹤上游 `aqua5230/usage`：「上游更新檢查」workflow 每天 02:00 UTC 比對 `docs/UPSTREAM.md` 的 `last_reviewed`，有新項目就開／更新 issue；逐筆判斷後採用（手工移植並補測試，推進 `last_merged` 與 `last_reviewed`）或不採用（只推進 `last_reviewed`、補 Skipped 表與理由）。failure 代表上游有未審項目，不是工具壞。依賴新鮮度每月 1 日檢查；發版採 SemVer（D-05）。查現況：`gh issue list -R SanHsien/agentdeck`、`gh api repos/SanHsien/agentdeck/dependabot/alerts?state=open`、`gh run list -R SanHsien/agentdeck -b main -L 8`。
