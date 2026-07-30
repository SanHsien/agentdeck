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

## D-02：README 改為繁體中文預設，刪除簡中／日／韓版本

**日期**：2026-07-29

**決定**：`README.md` 放繁體中文，英文移到 `README.en.md`，刪除 `README.zh-CN.md` / `README.ja.md` / `README.ko.md`。其他文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT）**維持上游慣例**：英文為預設 `.md`，繁中為 `.zh-TW.md`。

**考慮過的替代方案**：沿用上游的五語 README（英文預設）。

**為什麼**：上游把英文當預設是為了國際訪客；本 fork 的主要讀者是自己，繁中當落地頁比較合用。五個語言版本要手動保持同步，其中三個（zh-CN / ja / ko）連 CI 都沒有 gate，實務上必然漂移——沒有讀者的翻譯不值得維護成本。

**取捨**：GitHub 的 community tab 只認不帶後綴的 `CONTRIBUTING.md` / `SECURITY.md`，所以那幾份保留英文預設，沒有跟著一起翻轉。README 沒有這個限制。

**後果**：
- `scripts/check_doc_parity.py` 的 `DOC_PAIRS` 改為比對 `README.en.md` ↔ `README.md`，CI 仍然 gate 兩份 README 的 `##` 章節數一致。
- **app UI 的五語支援（`i18n.json`）完全沒動**——這是兩件事，不要因為刪了 README 語言版本就去砍 UI 語言。

---

## D-03：不在 Windows 上重新產生 `uv.lock`

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
- **環境變數塗銷** —— 一開始也被歸類為「環境汙染」，dev_check 曾移除短值的機密名稱環境變數來繞過。但根因其實在程式碼（`discussion_cli` 的塗銷沒有值長度下限），**已修復**（見 [`REPO_REVIEW.md`](../REPO_REVIEW.md) P3），繞道程式碼已從 dev_check 移除。

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
