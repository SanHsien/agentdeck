# 決策記錄

記錄「為什麼選 A 不選 B」，避免日後重複討論同一個問題。只記**有取捨**的決定，例行做法寫進 [`AGENTS.md`](../AGENTS.md) 即可。

新決策往下追加，不覆寫舊的；決策被推翻時保留原條目並標註「已被 D-xx 取代」。

---

## D-01：本 fork 獨立維護，不回貢上游

**日期**：2026-07-29

**決定**：`SanHsien/agentdeck` 獨立維護，不送 PR 回 [`aqua5230/usage`](https://github.com/aqua5230/usage)。`main` 允許與上游分叉，上游更新選擇性撿。

**考慮過的替代方案**：把 `main` 當上游的唯讀鏡像，所有改動走 `fork/*`、`fix/*` 分支，同步時用 `git merge --ff-only`。

**為什麼**：唯讀鏡像模式的唯一好處是「同步永遠不會衝突」，代價是每個本地決定都要繞開共用檔案，文件與設定被迫拆得零碎。既然沒有回貢計畫，這個代價換不到東西。分叉的實際成本只有「撿上游更新時要解衝突」，而那是低頻、可控的。

**後果**：任何檔案都可以改，包含 `CLAUDE.md`、`README*`、`.py`、`.github/`。撿上游更新的流程與已分叉清單見 [`FORK.zh-TW.md`](FORK.zh-TW.md)。

---

## D-02：README 改為繁體中文預設，刪除簡中／日／韓版本（已被 D-11 部分取代）

**日期**：2026-07-29

**決定**：`README.md` 放繁體中文，英文移到 `README.en.md`，刪除 `README.zh-CN.md` / `README.ja.md` / `README.ko.md`。其他文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT）**維持上游慣例**：英文為預設 `.md`，繁中為 `.zh-TW.md`。

**考慮過的替代方案**：沿用上游的五語 README（英文預設）。

**為什麼**：上游把英文當預設是為了國際訪客；本 fork 的主要讀者是自己，繁中當落地頁比較合用。五個語言版本要手動保持同步，其中三個（zh-CN / ja / ko）連 CI 都沒有 gate，實務上必然漂移——沒有讀者的翻譯不值得維護成本。

**取捨**：GitHub 的 community tab 只認不帶後綴的 `CONTRIBUTING.md` / `SECURITY.md`，所以那幾份保留英文預設，沒有跟著一起翻轉。README 沒有這個限制。

**後果**：
- `scripts/check_doc_parity.py` 的 `DOC_PAIRS` 改為比對 `README.en.md` ↔ `README.md`，CI 仍然 gate 兩份 README 的 `##` 章節數一致。
- **app UI 的五語支援（`i18n.json`）完全沒動**——這是兩件事，不要因為刪了 README 語言版本就去砍 UI 語言。

---

## D-03：不在 Windows 上重新產生 `uv.lock`（已被 D-12 取代）

**日期**：2026-07-29

**決定**：`uv lock` 只在 macOS 或 CI 執行，Windows 開發一律用 `uv sync --frozen`。`.claude/settings.json` 已 deny `uv lock`。

**為什麼**：`pyproject.toml` 的 `[tool.uv] environments` 鎖定三個平台。在 Windows 跑 `uv lock` 時，uv 會針對執行中的直譯器解析，把它能證明為假的平台 marker 重寫掉——所有 `sys_platform == 'darwin'` 的 PyObjC 相依會變成 `python_version < '0'`，無聲地從 lock 檔消失，直接弄壞 macOS 打包。上游已在 `pyproject.toml` 留下註解說明這個坑。

**後果**：需要更新相依時，在 macOS 上做，或改由 CI 產生。

---

## D-04：純環境限制在 `tools/dev_check.ps1` 處理，真實缺陷要修掉

**日期**：2026-07-29（2026-07-29 更新：環境變數那項已修根因）

**決定**：Windows 上非 code bug 的測試失敗，在 `tools/dev_check.ps1` 這一層處理，不去動 `tests/` 本身。但**「環境問題」不是免死金牌**——先判斷根因到底在環境還是在程式碼，是程式碼就修掉，不要用執行腳本繞過去。

**考慮過的替代方案**：在測試加 `pytest.mark.skipif` 直接跳過。

**為什麼**：這些測試在 CI 上是會過、也**應該**過的。在測試裡永久 skip 會讓真實的迴歸能力縮水；放在本機執行腳本這層，CI 的覆蓋率完全不受影響。

**目前狀態**：
- **符號連結權限** —— 真的是環境限制（本機沒開開發人員模式，CI runner 有權限）。dev_check 先實測能不能建連結，不能才 `--deselect` 該條並印出說明。**保留**。
- **環境變數塗銷** —— 一開始也被歸類為「環境汙染」，dev_check 曾移除短值的機密名稱環境變數來繞過。但根因其實在程式碼（`discussion_cli` 的塗銷沒有值長度下限），**已修復**（見 [`REVIEW_Claude.md`](../REVIEW_Claude.md) P3），繞道程式碼已從 dev_check 移除。

**教訓**：繞道留在本機腳本裡，會讓本機的執行環境跟 CI 不一致，反而遮蔽同類回歸。根因修掉後要記得把繞道一起拆掉。

---

## D-05：版本一律採語意化版本（SemVer 2.0.0）

**日期**：2026-07-29

**決定**：本 fork 之後發的所有版本都用 `MAJOR.MINOR.PATCH`、tag 為 `vX.Y.Z`。不用日期版號、不用 build number、不加任意後綴。規則寫進 [`CLAUDE.md`](../CLAUDE.md) 的 Versioning 段與 [`AGENTS.md`](../AGENTS.md)，讓之後接手的 AI 一律遵守。

**為什麼**：版號是給人與工具讀的合約——看到 PATCH 就知道可以無腦升，看到 MINOR 就知道要看 changelog。日期版號完全不帶這個訊息，升級風險得自己翻 diff 才知道。上游本來就用 `vX.Y.Z`，只是從未把規則寫下來，所以判斷標準散在各人腦裡。

**目前處於 `0.y.z`**：SemVer 明定 `0.y.z` 的公開介面不穩定，所以破壞相容性的改動升 **MINOR** 而非 MAJOR。要進 `1.0.0` 必須是刻意宣告，不是自然長到那裡。

**已知的判斷範例**：
- 介面語言從五種減到兩種（D-02）→ 對日／韓使用者是破壞性改動 → **MINOR**。
- 塗銷長度下限（P3 修復）→ 純修 bug、介面不動 → **PATCH**。

**硬性約束**：`pyproject.toml` 的 `version` 是唯一真相，`vX.Y.Z` tag 必須指向版號相符的 commit。**版號與程式碼不符的 tag，比沒有 tag 更糟**——這正是本次 fork 一度出現的狀況（見 D-06）。

---

## D-06：吃下上游 v0.29.8，讓 tag 與程式碼相符

**日期**：2026-07-29

**背景**：清理 tag 時選擇只保留上游最新的 `v0.29.8`，但那個 tag 指向的 commit 並不在本 fork 的 `main` 歷史中——`pyproject.toml` 當時仍是 `0.29.7`。等於 repo 裡有一個宣稱 v0.29.8、實際不是 v0.29.8 的 tag。

**決定**：合併 `upstream/main` 的那 2 個 commit（多螢幕面板位置、mypy 的 `ctypes.windll` 檢查，都是 Windows 修復），讓 tag 名副其實。

**同時處理的分支清理**：fork 繼承自上游的 4 個分支全部刪除。
- `feat/ai-council`、`fix/burn-rate-exclude-cache-read`：已完全併入 `main`，直接刪。
- `fix/windows-claude-quota-fallback`、`fix/windows-project-resolver-drive-root`：初看像「上游未合併的 Windows 修復」，**實際比對後發現是過時的舊實作**——`main` 早已有同功能且更完整的版本（例如 `_encoded_path_root` 在 `main` 同時處理 `"C"` 與 `"C:"`，分支版只處理 `"C:"`），分支版的 `usage_session_resume.py` 甚至還帶著 D-02 已刪除的語言表。合併會退步，因此一併刪除。

**教訓**：`git log main..branch` 顯示「分支領先 N 個 commit」只說明 commit 不在歷史中，**不代表改動沒進去**——上游可能 squash 合併或重新實作過。判斷分支要不要留，得比對**當前檔案內容**，不是比對 commit 圖。

---

## D-07：面板不貼齊系統匣圖示——上游也放棄了這個做法

**日期**：2026-07-30

**背景**：先前把「Windows 面板開在工作區右下角，而非貼齊系統匣圖示」列為待移植的落差，打算用 Win32 `Shell_NotifyIconGetRect` 取得圖示座標來貼齊。

**決定**：**不做**，把它從落差清單移除。

**為什麼**：審視上游 `4dbf916`（feat: let the panel float free of the menu bar icon）時發現，上游把 NSPopover 換成了可自由拖曳、記住位置、失焦不關閉的浮動 NSPanel——**理由正是 NSPopover 被 AppKit 綁在狀態列項目上、無法手動定位**。也就是說上游是在**放棄**貼齊圖示，往 Windows 早就有的行為收斂（`_place_window` + `usage.windowPosition` 記憶位置）。

實作 `Shell_NotifyIconGetRect` 會讓本 fork 背離上游剛剛選定的方向，而且是為了一個上游認定為缺點的行為。

**但保留了其中真正的缺陷（2026-07-30 補做）**：預設角落原本寫死在工作區右下，那是「工作列在底部」的假設。工作列在上方時托盤圖示在右上，面板卻開在右下——離剛點下的圖示最遠。改用 `SHAppBarMessage(ABM_GETTASKBARPOS)` 取工作列邊緣來決定首次開啟的角落，浮動與記憶位置的行為完全不變。

**為什麼不用 `Shell_NotifyIconGetRect`**：它要拿到托盤圖示的視窗 handle，而 pystray 只有私有的 `icon._hwnd`。工作列邊緣不需要任何私有 API，就足以解決真正的失敗情境——精確到圖示像素並沒有多帶來什麼，因為使用者一拖曳就覆蓋掉了。

**教訓**：把落差寫進待辦之後，仍要在動手前確認上游現在怎麼想。這條落差在盤點時是真的，兩個上游 commit 之後就不是了——**盤點有保存期限**。但「上游放棄了 A」不等於「A 想解決的問題不存在」：拆開來看，貼齊圖示是錯的解法，而它要解決的「面板開得離圖示很遠」在非底部工作列上仍是真問題。

---

## D-08：上游 v0.29.9 全數審視後未採用

**日期**：2026-07-30

**決定**：`616d48f`、`4dbf916`、`c2af3a9`、`d2d36c8`、`e94cd4d` 五筆全部不採用，`last_reviewed` 推進至 `e94cd4d`，`last_merged` 維持 `5fbf0ba`。

**為什麼**：五筆動到的檔案全部是本 fork 已刪除的 macOS 模組（`menubar.py`、`panels/web_panel.py`、`panels/__init__.py`）、上游新建而本 fork 沒有的檔案（`panel_window_state.py`），或已刪除的 README 語言版本。逐筆理由記在 [`UPSTREAM.md`](UPSTREAM.md) 的 Skipped 表。

**這是第一次實際跑完那套流程**，而它立刻產出了 D-07 這個非顯而易見的結論——證明「逐筆讀內容」而非「看標題決定」是對的。

---

## D-09：改名為 `agentdeck`

**日期**：2026-07-30

**決定**：專案與程式改名 `usage` → **`agentdeck`**。

**為什麼換掉 `usage`**：它只描述了額度監看，但這個程式現在還有多模型圓桌討論、角色（persona）安裝、報告分析、省 token 模式、浪費健檢。名字說不出一半的功能。

**為什麼也換掉先前選的 `quotatray`**：同樣偏窄（quota + tray），只涵蓋監看那一半。

**為什麼是 `agentdeck`**：現在的定位是「AI 編碼工具的駕駛艙」——既看儀表（額度、成本、燃燒率、服務狀態）也操作（召開圓桌、部署角色、切換模式）。`deck` 一詞剛好雙關：**儀表盤**（dashboard）＋**一副牌**（a deck of roles，正是人才市場的角色名單）。短、好念、不綁任何廠商——這點重要，因為它同時支援 Claude、Codex 與 Antigravity。

**考慮過**：`aicockpit`（意思最直白，但 `ai` 前綴過於常見、識別度低）、`aitower`（航管塔比喻漂亮，但與「面板／系統匣」的直覺聯結弱）。

**刻意不改的東西**：內部 Python 模組檔名（`usage_client.py`、`usage_statusline.py` 等 12 個）。理由是「程式名稱」指的是使用者看得到的東西——執行檔、hook 檔名、設定路徑、環境變數；模組檔名是內部實作，改它要動到每一個 import，產生大量無使用者價值的 churn。**但 `usage_statusline.py` 安裝到 `~/.claude/` 時的檔名要改**（那是使用者看得到的）。若日後仍想改模組名，那是獨立一次重構。

---

## D-10：fork 繼承的四個 workflow，逐一決定開或不開

**日期**：2026-07-30

**背景**：GitHub 對 fork 預設停用繼承來的 workflow。啟用 Actions 時只有一部分被開起來，其餘停在 `disabled_fork`——即使它們設定了 `push: main` 也從來沒觸發過。實測 `gh api .../actions/workflows` 才看得出來，只看 `.github/workflows/` 有哪些檔案會誤判成「有在跑」。

**決定**（不是全開，也不是全關）：

| Workflow | 處置 | 理由 |
|---|---|---|
| `codeql.yml` | **啟用** | 真實的安全掃描，成本低。已實測跑綠並掛上徽章 |
| `cflite_batch.yml` | **啟用** | fuzz 目標是本 repo 真實存在的 `fuzz/fuzz_codex_loader.py`、`fuzz_history_loader.py`，打的正是解析磁碟上 JSONL 的程式碼——那是最容易被畸形輸入弄壞的地方。實測 build 與 30 分鐘 fuzzing 全綠 |
| `cflite_pr.yml` | **保留但預期不會觸發** | 只在 PR 時跑，而目前的工作流程是直接推 main，所以它幾乎不會啟動。**這不是缺陷，不要當成死設定清掉**：它是 `mode: code-change`、只跑 5 分鐘，休眠時成本為零；本 repo 是公開的且 `CONTRIBUTING.md` 邀請外部 PR，而外部貢獻正是最需要在合併前 fuzz 的場景。batch 顧「推 main」這條路徑，PR 模式顧「外部貢獻」那條，兩條都有守 |
| `scorecard.yml` | **當時維持停用；2026-07-31 起實際為 active** | 決策當下的理由是「產出的 OpenSSF 分數沒有徽章要掛」。後續推 tag 時由 GitHub 自行啟用並執行成功——本專案未主動開啟。跑著不花成本、也提供供應鏈掃描，故不關回去；此處保留原始理由與後續實況，因為**決策紀錄的價值在於記下當時怎麼想，不是假裝從沒改變過** |

**啟用前必須先修的東西**：`.clusterfuzzlite/project.yaml` 仍寫著上游的 `homepage`、`main_repo` 與**原作者的聯絡信箱**；容器也還把原始碼解到 `$SRC/usage`，而 `build.sh` 用「macOS-only 相依」替自己的 `PYTHONPATH` 辯護——那些相依早在移除 macOS 支援時就刪光了。**繼承來的設定會沉默地繼續指向上游**，啟用它等於用上游的身分對外運作。

**教訓**：「workflow 檔案存在」不等於「workflow 有在跑」，「workflow 有在跑」也不等於「它跑的是你的專案」。兩件都要實測。

---

## D-11：面向讀者的預設文件與 app UI 都採繁中／英文雙語

**日期**：2026-07-30

**取代範圍**：D-02 中「CONTRIBUTING／SECURITY 維持英文預設」與「app UI 五語不動」兩項。

**決定**：`README.md`、`CONTRIBUTING.md`、`SECURITY.md` 都以繁體中文為預設，英文放在對應的 `*.en.md`；CHANGELOG 與 `docs/DEVELOPMENT` 維持原本後綴規則。app UI 只出貨 `zh-TW` 與 `en`，所有中文語系落到 `zh-TW`，其餘落到 `en`。

**為什麼**：GitHub community tab 會直接打開無後綴檔案，這正是讓主要讀者先看到繁中的理由，不是保留英文的理由。UI 也採同一組兩語契約，避免五套手動翻譯逐漸漂移。

**後果**：README、CONTRIBUTING、SECURITY、CHANGELOG、DEVELOPMENT 的中英配對都由 `scripts/check_doc_parity.py` 檢查；UI key 由 `tests/test_i18n_key_parity.py` 檢查。

**2026-07-31 補充**：新增產品路線圖後，`ROADMAP.md`／`ROADMAP.en.md` 也納入同一道雙語 parity gate。

---

## D-12：Windows 可更新 lock；本 repo 是 uv virtual root，不是 wheel package

**日期**：2026-07-31

**取代範圍**：D-03 全部。

**決定**：`pyproject.toml` 以 `[tool.uv] package = false` 把本 repo 定義為 flat application／virtual root；正式發佈走 PyInstaller，不發佈 wheel 或 PyPI 套件。`[tool.uv] environments` 只包含 Windows 與 Linux，因此在 Windows 上可以於相依或專案模式變更時執行 `uv lock`。單純改版號仍照 AGENTS.md 手動同步 root package 版號，避免無意義重解析。

**為什麼**：macOS、PyObjC 與 `.app` 建置已全部移除，D-03 防止 Windows lock 弄丟 darwin 相依的前提不再存在。舊 setuptools 清單還漏掉多個現行模組並指向已刪除的 `discussion_window.py`；它會產出表面成功、實際缺模組與資源的 wheel。應明確宣告「這不是 wheel package」，而非繼續維護一條不發佈的錯誤路徑。

**後果**：本機與 CI 先跑 `uv lock --check`，後續 gate 全部使用 `uv run --no-sync`；release workflow 也先拒絕陳舊 lock，再以 frozen environment 執行 PyInstaller。

---

## D-13：產品先建立信任合約，再擴張 provider 與功能

**日期**：2026-07-31

**決定**：[`ROADMAP.md`](../ROADMAP.md) 的優先序固定為「發版與資料正確性 → 錯誤可見與可修復 → 可腳本化 → AI 圓桌工作產物 → 新 provider／主題」。進入 `1.0.0` 的條件由版本、資料來源、升級、隱私與實機驗收是否可信決定，不以功能數量決定。

**考慮過的替代方案**：優先加入更多 AI provider、主題、雲端同步、團隊後台或自動帳號切換，以功能數量擴大受眾。

**為什麼**：v0.31.2 已有三個 provider、十款主題、報告、persona 與 AI 圓桌，功能廣度不是目前瓶頸；同時仍有 P5 的實機裁切與 P6 的本機錯版號 artifact。繼續加功能會放大維護面，卻不會解決「使用者能不能相信畫面與 release」這個核心問題。Windows-first、local-first 與從監控到行動，才是本 fork 相對同類工具的清楚位置。

**後果**：新 provider 必須先證明有可靠、合法、可測的 Windows 資料來源；新 UI 不得插隊於已知可信度缺口；roadmap 項目只有在自動化與實機證據齊全時才算完成。若日後要改成雲端或帳號路由產品，必須另立決策推翻本條，而不是在單一功能中偷偷擴張。

---

## D-11：ProviderHealth——三個 provider 共用一套狀態語彙

**日期**：2026-07-31

**問題**：Claude、Codex、Antigravity 各自長出一套「資料還能不能用」的判斷，而且彼此不一致——Codex 15 分鐘算舊、Antigravity 20 分鐘算舊；健康時一個回 `None`、一個回 dict；`--doctor` 又印第三套措辭，面板從來沒顯示過。使用者看到 `--` 時分不出「這個工具我從沒用過」「檔案在但很舊」「查詢失敗」三種完全不同的處境。

**決定**：新增 `provider_health.py`，六個狀態：`ready` / `stale` / `missing` / `misconfigured` / `unavailable` / `error`。每個結果一律帶著**原因**與**下一步**兩個 i18n key，面板與 `--doctor` 透過同一組 key 渲染。

**刻意的設計選擇**：

- **純投影、零 IO。** 呼叫端先蒐集事實再傳進來，所以每個分支都能在沒安裝任何 provider 的機器上測到。IO 留在 `doctor.collect_provider_health()`。
- **stale 門檻維持各自不同**（Claude／Codex 15 分、Antigravity 20 分）。那是刷新節奏、不是政策：Codex 每輪對話寫檔，Antigravity 是定時輪詢；壓成同一個數字會讓健康的 Antigravity 被誤報為舊，或讓死了十分鐘的 Codex session 不出聲。
- **i18n key 全部顯式傳入，不用 f-string 組。** 用 `f"health_{provider}_missing"` 讀起來很順，然後會去要一個沒人寫過的 key——`antigravity` 會找 `health_antigravity_missing`，但檔案其他地方寫的是 `health_agy_*`。顯式寫死才能讓 parity 測試靠 grep 找得到每一個 key。
- **`unavailable` 與 `error` 分開。** 前者是遠端暫時不回應、快取數字仍然可以顯示；後者是本機讀取失敗。合併就沒辦法告訴使用者「畫面上的數字是舊的但可信」。
- **順序即嚴重度**，`worst_of()` 靠它把多個 provider 收斂成一個徽章。

**沒有做的**：把面板改成用這個模型。`--doctor` 是第一個消費者，面板接線排在 ROADMAP 的 v0.32.0。先讓模型有真實使用者驗證形狀，再改動 UI。

---

## D-12：建置工具進 lock；OneDrive 內的 checkout 把 venv 移出去

**日期**：2026-07-31

**症狀**：`uv sync` 反覆把虛擬環境弄成半殘——PyInstaller 連同 pefile、setuptools、packaging 等被刪到一半，`Access denied`，接著就建不出 exe。發生四次，每次都在發版路徑上。

**先排除的錯誤結論**：一開始歸咎於 OneDrive。實測**暫停同步後第一次 `uv sync` 仍然失敗**，所以「暫停同步」不是修復；而失敗的目錄是空的、`Remove-Item` 一秒就刪得掉，代表不是持續性的檔案鎖。

**真正的根因**（`uv sync --dry-run` 直接看出來）：

```
Would uninstall 7 packages
 - altgraph - pefile - pyinstaller - pyinstaller-hooks-contrib
 - pywin32-ctypes - setuptools - usage==0.30.0
```

PyInstaller **不在 `uv.lock` 裡**，是用 `uv pip install pyinstaller` 另外裝的。而 `uv sync` 的職責是讓環境與 lock 一致——**不在 lock 裡的一律視為多餘並刪除**。所以每一次 sync 都會刪掉整個建置工具鏈再要求重裝。

對照組很清楚：`yt_fetch` 的 venv **也在 OneDrive 裡**，但用 pip + `requirements.txt`，而 **pip 只裝不刪**，所以從來沒壞過。

**決定一：把 PyInstaller 放進 `dev` 依賴群組。** 放進 `build` 之類的獨立群組反而沒用——標準指令 `uv sync --frozen --group dev --extra windows`（CI、`dev_check.ps1`、文件都用它）不會裝它，於是照樣刪。放 `dev` 是唯一不用同步修改所有指令的正解。`release.yml` 的 `uv pip install pyinstaller` 隨之移除。

**決定二：checkout 在 OneDrive 裡時，用 `UV_PROJECT_ENVIRONMENT` 把 venv 移出去。** 這是縱深防禦，不是根因修復——根因已由決定一解掉。但 OneDrive 樹裡每個目錄都是 Files On-Demand 佔位目錄（reparse tag `IO_REPARSE_TAG_CLOUD_E`，實測 repo 根目錄與 `.venv` 皆是），雲端過濾驅動在每次檔案操作的路徑上，暫停同步不會卸載它。移出去同時省下同步 5,134 個「`uv.lock` 幾秒可重建」的檔案，並讓路徑脫離含中文的 `...\OneDrive\文件\...`（該路徑已造成多次工具輸出亂碼）。

`tools/dev_check.ps1` 改為尊重該變數；CI 從不設定它，runner 照舊用 `.venv`。

**驗證**：改動後連續三次 `uv sync` 皆為「移除 0 個套件、零失敗」（先前每次移除 7 個）。新環境跑完六道閘門與完整建置，exe 版號 guard 通過。

**教訓**：**「我的環境有問題」跟「我的設定在跟工具對打」長得一模一樣。** 分辨方法是問「這個工具正在做的事，是它被要求做的嗎」——`uv sync` 刪掉不在 lock 裡的套件是完全正確的行為，錯的是把建置工具裝在 lock 外面。環境（OneDrive）只是讓這個錯誤從「浪費」升級成「損壞」。

---

## D-14：審視上游 v0.29.11 至 v0.29.16，移植四項可驗證修正

**日期**：2026-08-02

**決定**：審視 `ec24f50..33641bc` 共 36 筆 commit；移植 `75292da`（429 `Retry-After`）、`32d27d7`（即將重置）、`83f77ba`（非 UTF-8 狀態檔容錯）與 `276a4a2`（CJK token 估算）。純資料同步直接略過，其餘逐筆不採用理由記在 [`UPSTREAM.md`](UPSTREAM.md)。`last_reviewed` 推進到 `33641bc`，`last_merged` 推進到最後採用的 `276a4a2`。

**取捨**：不把「上游有新功能」等同於「本 fork 現在就要加入」。`doctor --json`、cache quarantine 與對話標題都有價值，但分別牽涉 schema/redaction、證據留存與報告相容性，應走 Phase A–B 的產品契約；macOS 面板、通知、shell 安裝與獨立版號則不適用 Windows-first fork。

**驗證方式**：四項移植都補 fork 內的直接回歸測試；完整品質閘門通過後才關閉追蹤 issue。

---

## D-15：面板改用系統標題列，關閉與最小化都收進系統匣

**日期**：2026-08-04

**決定**：面板從無邊框視窗改為一般標題列（`frameless=False`、`resizable=False`），並攔截 `closing` 事件回傳 `False`，讓 X、標題列最小化、Alt+F4 全部走「隱藏到系統匣」。面板內自繪的 `−` 按鈕、`minimize` JS 動作與 `minimize_window` 翻譯字串一併移除。離開程式的唯一入口是系統匣選單的「結束」。

**取捨**：另一個選項是「乾脆不要關閉按鈕」。WinForms 做不到只拿掉 X——`ControlBox = False` 會連最小化一起拿掉，`GetSystemMenu` + `DeleteMenu(SC_CLOSE)` 只是把它變灰。更關鍵的是**Alt+F4 照樣送出 `WM_CLOSE`**，所以無論按鈕在不在，`closing` 都必須攔截。既然攔截是必要的，保留一顆行為正確的 X 比拿掉它更簡單，也不會少任何安全性。

**驗證方式**：不是讀文件推論，是開真視窗用 Win32 量測（225% DPI、3840×2160）：`WS_CAPTION` 存在、`WS_MAXIMIZEBOX` 與 `WS_THICKFRAME` 皆不存在；`PostMessage(WM_CLOSE)` 走真實訊息路徑後 `IsWindowVisible` 為 0 而行程仍在，再開啟又回到可見。刻意不從非 GUI 執行緒直接觸發 `closing` 事件——pywebview 的 `should_lock=True` 會同步執行處理常式，那會是一條真實使用者永遠走不到的路徑。

**過程中發現的真缺陷**：`resize()` 設定的是**外框**尺寸。加上標題列之後，量到 `clientH=1919` 而面板要的是 888 邏輯像素（1998 物理），也就是內容區短少一整條標題列，底部會被切掉。改為向即時視窗量測 `Height - ClientSize.Height` 再換算回邏輯像素加上去（實測 35），修正後 `clientH=1997`。**不寫死常數**：這個差值隨 DPI 與使用者的標題列設定改變，寫錯只會表現成「少了幾像素」——沒有例外、沒有紅燈，只有看起來怪怪的畫面。

**教訓**：換掉視窗外框不是換一個旗標，是換掉整套尺寸座標系。UI 改動要**量**，不能推論——這次若沒量，送出去的就是一個底部被裁掉的面板。

---

## D-16：審視上游 v0.29.17 至 v0.29.18，移植繁中修正與離線價目表

**日期**：2026-08-08

**決定**：審視 `c33e260..73b71d4` 共 11 筆 commit。移植 `843505e`（zh-TW 52 個鍵是簡體字）與 `c33e260`（離線價目表），並採用 `bc28b5a` 的兩條檢查概念（空字串翻譯、`{placeholder}` 與英文不一致）。`86bde4a`、`57f207b` 與兩筆發版 chore 不採用，理由逐筆記在 [`UPSTREAM.md`](UPSTREAM.md)。

**為什麼繁中那筆特別重要**：本 fork 只出繁中與英文兩種語言，繁中是維護者自己的語言——而它有 52 個鍵是簡體（「暂无数据」「加载数据」「消息」「会话」「限额」）。這種錯誤**任何既有閘門都看不到**：鍵在、值非空、格式正確，一個寫錯字體的字串仍然是完全合法的字串。

**不照抄上游的地方**：價目表沒有直接套上游的數字，而是拿本機 `~/.agentdeck/pricing_cache.json`（2525 筆真實 LiteLLM 線上表）逐項比對。結果證實上游是對的，同時查出本 fork 另有 `claude-fable-5`、`claude-sonnet-5` 兩筆上游沒有的項目也要一併核對。缺 `claude-opus-5` 的後果是**離線時 Opus 5 成本顯示 $0**——不是報錯，是安靜地算成零。

**`57f207b` 為什麼不適用**：根因是 `NSUserDefaults` 回傳 `NSDictionary`、`isinstance(x, dict)` 永遠 False，於是存下的實測高度被判無效、視窗在實測值與估算值之間來回。本 fork 的 `_content_height` 只活在記憶體裡，不經任何持久化字典，這條路徑不存在。**「macOS 專屬」不是跳過的理由，「機制不存在」才是**——判斷要走到根因，不能停在檔名。

**留下兩道閘門**：`tests/test_i18n_traditional.py`（繁中字體）與 `test_i18n_key_parity.py` 新增的兩條。字體那條是字元黑名單、不是轉換器——它不可能知道「分布」該是「分佈」，但簡體專用字一出現就會紅。繁簡同形字（目、置、配、段、消、加、字、周、布、余、退）刻意排除在外，還多寫一條測試守著這件事:**會對正確文字誤報的檢查，最後會被關掉而不是被修好**。

**驗證方式**：兩道閘門都注入錯誤實測會紅、還原會綠；價目表修完再次與線上快取全表比對，8 個模型零差異。

---

## D-17：越過審視順序先移植上游資安修正 `537e56f`

**日期**：2026-08-08

**決定**：上游 `537e56f`（收緊狀態列輸出、發版流程與網路讀取的信任邊界）不排隊等常規審視，立即移植六項全部。`last_merged` 推進到 `537e56f`，但 `last_reviewed` **維持 73b71d4**——中間十幾筆還沒看過，把標記一起往前推等於謊稱已審視。上游檢查工具只依 `last_reviewed` 報告，所以這樣做不會漏掉任何一筆。

**每一項都先在本機重現，不是照著上游描述套用**：

- **狀態列 ANSI 注入**（`usage_statusline.py`）——實測成立。惡意 repo 的 `.git/HEAD` 裡，ref 名稱之後全是攻擊者可控文字；寫入 `\x1b[2K\r` 就能清掉整行狀態列並印出偽造的配額讀數。門檻只是「解開一包 repo、cd 進去、開 Claude Code」，不需事先取得執行權。`safe_text()` 只濾控制字元、不動內容——修完偽造文字仍在，但變成分支欄位裡的惰性純文字。這是正確的邊界：repo 可以有奇怪的分支名，不可以驅動終端機。
- **`javascript:` 更新網址**（`update_checker.py`）——`html_url` 未驗 scheme 就交給 `webbrowser.open()`。實測 `javascript:` 與 `http://` 現在都會被拒。這條在本 fork 特別要緊：v0.37.3 才剛把這個網址放到更新對話框最顯眼的位置，當成「可以信任、點下去」的東西。
- **四處無上限網路讀取**（`pricing`、`service_status`、`update_checker`、`providers/agy_quota_probe`）——`urlopen().read()` 不帶參數就是「對方送多少收多少」。改為讀「上限+1」後拒絕。本 fork 另有上游沒有的第五處 `tools/check_upstream_updates.py`，一併處理。
- **逐字稿權限**（`council/discussion_bridge.py`）——這項**沒有照抄，先做了對照實驗**。`os.chmod` 在 Windows 只切換唯讀屬性，直覺上 POSIX 的修法應該無效。實測結果相反：CPython 3.13 的 `mkdir(mode=0o700)` 在 Windows 上會建立真正的限制性 DACL。無 mode 建立的目錄會繼承 `BUILTIN\Users:(I)(OI)(CI)(RX)`，帶 mode 建立的則沒有，裡面的檔案也沒有。**因此上游的修法原封不動就能移植,我原本寫的 `icacls` 輔助函式是多餘的,寫完就刪掉。** 這件事在本機不是理論問題——`~/.agentdeck` 上有一條明確的 `CodexSandboxUsers:(RX)`，逐字稿目錄本來會整條繼承。
- **`release.yml` 的 shell 插值**——三處 `${{ }}` 直接插進 `run:`，其中 `inputs.tag` 在 `workflow_dispatch` 時是觸發者輸入的任意字串，而同一個 job 帶著寫入權杖。全改走 `env:`。順手掃了全部七個 workflow，其餘本來就乾淨。
- **遮蔽名單**（`council/discussion_cli.py`）——補 `COOKIE`／`PRIVATE`／`PAT`，`PAT` 用 `(?!H)` 排除 `PATH`：直接加會把 PATH 的值從所有錯誤訊息裡整段遮掉，而**會摧毀診斷資訊的過濾器最後會被關掉，不會被調整**。

**順帶修掉的**：`pricing.py` 與 `service_status.py` 的 `USER_AGENT` 還是 `"usage/0.9"`——既是舊程式名，又把版號凍在 0.9,而且是發送給外部服務的識別字串。v0.37.1 的品牌閘門只看 `i18n.json`，看不到這裡。

**測試替身的教訓**：四個 `FakeResponse.read()` 都不收參數，與真實 `HTTPResponse.read(amt)` 介面不符——加上讀取上限後它們立刻炸了 15 條測試。**比真實介面寬鬆的替身，會讓真實介面上的 bug 永遠測不出來**；這和上游 `57f207b` 用 `dict` 當 `NSDictionary` 替身踩到的是同一件事。

---

## D-18：補齊 `73b71d4..6a498ea`，兩個追蹤標記重新對齊

**日期**：2026-08-08

**決定**：把 D-17 越過的區間補審完，`last_reviewed` 與 `last_merged` 同時推到上游 tip `6a498ea`。採用 `21d0141`（對外連線揭露、OAuth public client 說明）、`c413af3` 與 `6a498ea` 的 i18n 部分、`8fa5809` 的測試覆蓋概念；其餘八筆逐列記在 [`UPSTREAM.md`](UPSTREAM.md)。

**三個 i18n 字串是本 fork 的實際缺陷，不只是同步**：

- `hook_broken_not_installed` 與 `usage_status_missing` 叫使用者去跑 `python3 main.py --setup`——**我們的使用者跑的是 `agentdeck.exe`，而且面板上就有「設定狀態列」按鈕**（`install_hook`）。這和 v0.37.1 修掉的 `usage setup` 是同一類錯誤，當時漏掉了這兩則。
- `talent_empty_hint` 一句話裡有兩個缺陷：叫使用者「重新打包 **.app**」（macOS 產物，本 fork 是 Windows-only），以及用「角色市集」這個 UI 別處都不用的舊術語（其餘 `talent_*` 全部寫「人才市場」）。

掃過整份 i18n 找同類問題（`python`／`main.py`／`.app`／`brew`／`sudo`／`Finder`），只剩「終端」這個正常的面板標籤。

**`21d0141` 表面是文件 commit，實際帶了程式改動**——`agy_quota_probe.py` 加了七行註解。這是分流不能只看標題的例子：`docs:` 開頭的 commit 動了 `SECURITY.md`（+34 行）與一個 `.py`。

兩項都採用，而且對本 fork 更要緊：

- **對外連線揭露**：原本 `SECURITY.md` 只有一段散文，指向 README。現在列出全部五類端點、觸發時機，以及對應的常數名（`service_status.CACHE_TTL_SECONDS`、`pricing.CACHE_TTL_DAYS`、`update_gate.AUTO_CHECK_TTL_SECONDS`）——**時機是從程式碼讀出來的，不是抄上游的數字**。上游沒有的 `MAX_RESPONSE_BYTES` 上限與 `tools/check_upstream_updates.py`（維護者工具，不隨程式散布）也一併寫明。
- **`GOCSPX-` 常數的說明**：`providers/agy_quota_probe.py` 裡有明文 OAuth client secret，對任何掃描 repo 的人（或我們自己跑的 CodeQL／Scorecard）看起來就是外洩憑證。依 RFC 8252，安裝在使用者電腦上的應用程式無法保密 client secret，這是 public client、不構成安全邊界。**會被誤判為漏洞的東西，理由必須跟著程式一起出貨。**

**新增 `tests/test_security_disclosure.py`**：「這是本程式連線的全部端點」這種宣告，只有在有東西強制它為真時才值得寫。散文清單會在下一次有人加 fetch 時安靜過期——程式照跑，文件默默變成一句關於隱私的謊。這道閘門從**程式碼**讀出網址，要求每一個都出現在雙語 SECURITY 裡。排除項比對 host+path 而非只比 host，所以 `api.openai.com/auth`（JWT claim 的鍵名）不會順便赦免整個 `api.openai.com`。實測:注入一個假的 telemetry 端點 → 紅燈。

**`agy_disk_cache` 是三個磁碟快取裡唯一沒有測試的**（`test_disk_cache_shards.py` 只涵蓋 history 與 codex），和上游 `8fa5809` 補的是同一個洞。補了 10 條。這個模組整份契約就是「遇到任何錯誤都安靜復原」——**正是最會藏壞掉的形狀**：每條失敗路徑都靜靜返回，快取徹底失效看起來會跟冷啟動一模一樣，代價只是每次啟動重新解析一次，沒有任何訊號。實測:把 `thinking_tokens` 序列化成 0、把上限淘汰關掉，兩條測試分別紅燈。

---

## D-19：人才市場退出主題清單、World Cup 主題移除、面板高度改以實測為準

**日期**：2026-08-10

**AI 人才市場的故障是真的，機制在切換順序**：`_build_state()` 只在「當前面板是 talent_market」時才讀角色名冊，而 `switch_panel()` 重載頁面後是用**先前那個面板建立的** `latest_state` 初始化。於是每次開啟人才市場都顯示「元件尚未安裝」，要等下一次背景輪詢（最多 60 秒）才會有內容——對使用者而言，這和功能壞掉沒有區別。`open_talent_market()` 現在切換後強制 `refresh()`。實機驗證：修正前截圖是空狀態，修正後同一條路徑出現搜尋框、「資料分析組」與 `0/3` 安裝計數。

**它同時不該是「主題」**：它顯示角色卡與安裝按鈕，完全沒有額度資訊。列在主題清單裡等於讓清單謊稱自己提供的東西，也讓使用者可能因為「挑一個外觀」而卡在裡面。現在它保留 panel id（同一個視窗渲染），但只從系統匣選單進入，且**刻意不記成開機面板**——開機開進人才市場會蓋掉這個程式存在的理由。`available_panels()`（主題）與 `renderable_panels()`（全部可載入）因此分家。

**World Cup 主題移除**：`world_cup.html` **完全沒有 `agy`**，而其他九張額度面板各有 24–33 處。用那個主題的人會靜靜少掉 Antigravity 一整個來源，畫面上沒有任何提示。上游同樣是 0 且未修（最近兩次動到該檔都是別的修正），符合「上游也故障且未修正就先移除」的判準。它另外還把 `USAGE 2026` 寫死在 HTML 裡——v0.37.1 的品牌閘門只看 `i18n.json`，看不到面板 HTML。

**面板高度改用實測值**：上游 `1ac8961` 指出 Windows 那組數字停在 Mac 校正之前。**但直接抄上游的 Mac 校正值一樣是錯的**——那是不同引擎畫的不同面板。改為實際量測本 fork 自己的面板：Windows 11、225% DPI、mock 資料，攔截 `_apply_content_height` **clamp 之前**的原始回報值（第一次量全部都是 888，因為工作區高度上限把每張都壓平了——這件事本身也值得記下來：在高 DPI 小工作區上，這張表的精確值影響不大，真正會差的是低 DPI 大螢幕）。`talent_market` 維持原值，因為 mock 下沒有角色可畫，量到的 108 不代表它需要的高度。

**卡片排序驗證改成補齊**：`_valid_quota_card_order` 原本要求存檔的排序長度剛好等於預設值。日後新增第四張額度卡時，**每一位既有使用者的排序都會被判定無效、悄悄還原成預設**，而且沒有任何訊息說明。改成只擋重複／未知 id／非字串，缺的卡片補到最後。

**順帶修掉別的 session 留下的定時炸彈**：v0.38.0 新增的 `tests/test_autoresume_wiring.py` 把 `NOW` 寫死成 `2026-08-09 10:00 UTC`，而 `tick()` 讀的是真實時鐘。寫的當天全綠，隔一天真實時間越過 `NOW + 3600`，排程時間變成過去式，三條測試自己變紅、程式一行沒改。改為相對於真實時鐘取基準——這些案例本來的語意就是「從現在起一小時後」。

---

## D-20：設定檔的跨行程鎖——對照組證明了競態，也證明它比上游描述的更嚴重

**日期**：2026-08-10

**決定**：新增 `settings_lock.py`（POSIX 用 `fcntl.flock`，Windows 用 `msvcrt.locking` 輪詢），把 `_append_self_heal_log` 的 load → modify → save 整段包起來。鎖檔獨立為 `~/.claude/agentdeck-settings.lock`，**不共用狀態列那把**——那把每分鐘被取用好幾次，設定檔的編輯沒有理由排在它後面。這樣 `e16c5c0` 三項全部到位，`last_merged` 推進到 `e16c5c0`。

**不共用 `usage_statusline.py` 裡那份實作**：那個檔必須維持 stdlib-only 且獨立，它會被複製到 `~/.claude` 由使用者的 `python3` 執行，身邊沒有可以 import 的套件。重複是刻意的，和 CLAUDE.md 對那五個 hook 腳本的既有規定一致。

**為什麼一定要雙行程測試**：這個 bug 單行程測不出來。失敗模式是兩個 OS 行程交錯執行 load-modify-save，而**每一次 save 本身都是原子的**——所以檔案永遠不會壞，後寫的人只是把他讀到的舊副本寫回去，先寫的那筆就這樣消失，沒有任何痕跡。因此測試會實際生出四個直譯器行程。

**對照組是這組測試的重點**：同一個情境把鎖關掉必須**掉資料**，否則「有鎖那組全過」只證明了機器剛好沒有交錯。實測：

| | 保留的紀錄 |
|---|---|
| 有鎖 | 20 / 20 |
| 無鎖 | 5 / 20 |

**順帶查出比上游描述更嚴重的事實**：無鎖那組除了掉紀錄，還噴出 `PermissionError: [WinError 5]`——**Windows 上另一個行程開著目標檔時 `os.replace` 會直接失敗**。上游在 POSIX 上只會看到「安靜地掉一筆」，在本 fork 的平台上它是會拋例外的。這是「平台落差要移植、不是接受」的另一面：同一個 bug 在不同平台的嚴重度不同，判斷不能只讀上游的描述。

---

## D-21：CODEX_HOME 支援與發版版號守門——兩筆都不是照抄

**日期**：2026-08-10

**`CODEX_HOME`（上游 `ab03f92`）**：本 fork 有 11 處寫死 `~/.codex`。設過 `CODEX_HOME` 的人（第二個帳號、容器化的 Codex）拿到的不是錯誤訊息，而是**一張空白的 Codex 卡**——「Codex 沒有用量」和「我們找錯地方」在畫面上長得一模一樣。全部改走 `codex_paths.codex_home()`。常數在 import 時計算，所以改了環境變數要重啟才生效；這個限制寫進測試（測試用 `importlib.reload`）與 CLAUDE.md，而不是留給下一個人踩。

**發版版號守門（上游 `45397d8`）——照抄會擋掉我們每一次發版**：上游的腳本拿「已發布 release 的最大版號」比對正在發的 tag，而**本 fork 是先 `gh release create` 再由 tag push 觸發 workflow**，所以檢查執行時，被檢查的版號早就在清單裡了，`compare_versions(x, x) == 0` 會直接判失敗。改成**把正在發的 tag 排除在比較集合外**。

順帶把上游那個新步驟的反模式修掉：它把 `${{ }}` 直接插進 `run:`，正是上游自己在 `537e56f` 教的事（我們在 v0.37.5 已全面清掉）。我們的版本走 `env:`。

**這個守門有一個抓不到的情況，寫成測試而不是假裝沒有**：因為檢查發生在 release 已存在之後，「重切最新那一版」和「第一次發那一版」在資料上無法區分。其餘都抓得到——版號變舊、或重切任何不是最新的版本，因為取代它的那個 release 還在集合裡。

**真實資料驗證**（對 `SanHsien/agentdeck` 實跑）：`v0.39.1` 放行、`v0.39.0` 擋下、`v0.30.0` 擋下、`v0.40.0` 放行。第一項最重要——它證明這道閘門不會擋住我們自己的正常流程。

**寫測試時抓到自己腳本的 bug**：`latest()` 對第一個候選值不做解析就採用，於是遇到 `nightly` 這種舊 tag 會把它當成「最新版」，之後每次比較都拋 ValueError、把當天的發版擋下來。改成每個候選先自我驗證。**這是「先寫會紅的測試」的價值**：這個 bug 只在 repo 有格式不符的歷史 tag 時才出現，靠讀程式碼不會發現。

**兩張新面板暫不移植**：`3e0fc4e`（共用 `panel_core.js`）、`7743649`（彩繪玻璃）、`417ff01`（摺紙）三者耦合，而本 fork 的面板已與上游分歧。先確認過**兩張新面板都有 Antigravity 欄位**（13／17 處），不是 World Cup 那種缺一整個來源的問題——確認這件事本身就是 D-19 留下的檢查習慣。列為後續獨立工作。

---

## D-22：燃燒速率短跨度誤判；面板架構已與上游分家

**日期**：2026-08-12

**燃燒速率誤判 Heavy（上游 `d92f683`）**：`usage_rate.py` 的 `elapsed_minutes` 下限是 1 分鐘，所以極短跨度內的單一 `cache_creation`——一段肥的系統提示詞——會被除成看起來持續很兇的速率。**本機重現**：兩則訊息相隔 30 秒、其中一則 20,000 cache_creation，判定為 **Heavy**，動畫就照 Heavy 跑。

下限改為 `burn_rate.MIN_FORECAST_SPAN_SECONDS`（本 fork 自己的 5 分鐘門檻）**而不是抄上游寫死的 5.0**——兩處對「多短算太短」若各有一個答案，遲早會漂開，屆時速率讀數與預測會對同一批資料給出不同說法，這件事本身寫成了測試。

修完重測:同一組資料變成 **Active**；另外驗證連續 20 分鐘的真實重度燃燒**仍然是 Heavy**——只會壓低不會誤放的修正，跟拿掉功能沒兩樣。

**既有測試因此紅了三條,而它們紅得有道理**：那些 fixture 用同一個時間戳建資料（span = 0），等於在用「隱含的 1 分鐘分母」斷言門檻。改成 `_entries_at_rate()`，把速率寫明白——原本的寫法在下限一改就默默換了語意。

**面板架構分家（`d01f38a` 等）**：想移植 Catppuccin，實測發現 `catppuccin.html` **完全沒有 JS 狀態入口**（`applyState` 出現 0 次、沒有任何 `window.*` 指派）。原因是上游 `3e0fc4e` 之後面板狀態改由共用核心供應——**上游連 `classic.html` 都已經不定義 `window.usageApplyState`**，而本 fork 九張面板全都定義它。

照抄會得到一張畫得出來、但**永遠收不到額度資料、也永遠不回報高度**的主題——正是這個 session 一路在修的那種無聲缺陷。所以三張新主題（Catppuccin／彩繪玻璃／摺紙）不是三件小事，而是同一個架構決定的下游：要嘛移植共用核心並改寫我們九張面板，要嘛照本 fork 的契約重寫新面板。列為單一項後續工作。

**順帶查證（結果是好的）**：上游 `0014773` 提到他們跑一次測試就會改寫開發者真實的 `~/.codex/config.toml`。本 fork 實測——記錄 sha 與 mtime、跑完整套 1381 條測試、再比對——`~/.codex/config.toml` 與 `~/.claude/settings.json` **位元組完全相同**。那個隔離漏洞來自他們新增的 self_heal Codex 分支，我們沒有。

---

## D-23：改用共用面板核心，只保留預設與三張新主題

**日期**：2026-08-12

**決定**：移植上游的 `panel_core.js`，九張舊主題全部移除，保留 Classic（預設）與三張新主題（Catppuccin、彩繪玻璃、摺紙）。

**先量再決定**：九張面板共 **11,263 行**，其中 `<script>` 佔 **3,675 行**，彼此相似度 **89–96%**——每張主題真正獨特的只有 600–700 行 CSS，另外 ~350 行邏輯是抄的。上游那次重構是 **−3,205／+1,012** 加一個 429 行核心，數字幾乎完全吻合。

這個成本已經現形過不只一次：移除最小化按鈕、拖曳區、`data-i18n` 契約，每一項都要改九次；而 **World Cup 面板完全沒有 Antigravity 欄位**，上游和本 fork 一路出貨到有人 grep 才發現。九份幾乎相同的檔案就是這樣漏掉一份的。

**為什麼不是「只留一張」**：主人的偏好檔顯示他實際在用 `cloud_observation`，不是預設的 `classic`——「只留預設」會拿掉他正在用的那張。最後主人選擇留預設加三張新的，等於同時砍掉維護成本又保住可選擇性。

**移植前先確認新主題沒有 World Cup 的病**：Catppuccin 19 處、彩繪玻璃／摺紙各 13／17 處 `agy`，三張都完整支援 Antigravity。這個檢查現在是移植面板的固定步驟。

**保留本 fork 的既有決定，不因為對齊上游而回退**：新面板的切換按鈕標籤是 `switch_panel`（「更換面板」），但那顆按鈕開的是整個功能表——主題、設定、關於、結束。本 fork 早就改成 `panel_menu`（「功能表」），四張新面板一律改回來。**對齊架構不等於接受對方的每一個 UI 判斷。**

**移植暴露的真缺陷（不是上游的錯，是我們螢幕的事實）**：新面板把 `html, body` 釘在 `100vh; overflow: hidden`、`.wrap` 用 `height: 100%`，所以在比面板矮的螢幕上每張卡都被 flex 壓縮並裁掉自己的最後一列。實測對照——**舊面板 `firstCardClipped: false`，四張新面板全部 `true`**，而且 `overflow: hidden` 代表被裁掉的內容**沒有任何辦法看到**。

修法放在**本 fork 的注入層**而不是改四份 HTML：`html, body { height: auto; overflow-y: auto }`、`.wrap { height: auto; min-height: 100% }`、`.card, .footer { flex-shrink: 0 }`。這樣以後每一張上游新主題都自動適用。修完實測 `scroll` 1016–1058 > `client` 888、`overflowY: auto`、不再裁切。

**視窗位置的連帶修正**：高度上限原本先套用工作區、**之後才加上標題列高度**，於是外框比工作區高出整整一條 caption，下緣壓在工作列上。改成先扣 chrome 再取上限，並用外框高度夾邊界。同時首次開啟改為錨定**上緣**：面板是比工作區還高的長條，錨在下緣會把它推出螢幕，也讓使用者要抓的標題列位置隨主題高度浮動。實測（邏輯像素）:視窗 `(1315, 12, 1695, 900)`、工作區 `(0, 0, 1707, 912)`，下緣 900 ≤ 912，上／右邊距各 12px。

**Catppuccin 的四款配色**：`{{PANEL_FLAVOR}}` 由偏好設定填入，系統匣多一個子選單。實測切換:`latte` → 頁面屬性 `latte`、背景 `rgb(230,233,239)`；`mocha` → `mocha`、`rgb(24,24,37)`。

**一次誤報值得記下來**：我用 `scrollHeight > clientHeight` 判斷「卡片被裁」，修完後 Catppuccin 仍回報 `true`。實際量每張卡才發現四張都是 `diff: 7` 且 `overflow: visible`——那 7px 是裝飾邊框畫在框外，不是裁切。**判斷式本身也需要被驗證**，否則會追一個不存在的 bug。
