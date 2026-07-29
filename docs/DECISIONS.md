# 決策記錄

記錄「為什麼選 A 不選 B」，避免日後重複討論同一個問題。只記**有取捨**的決定，例行做法寫進 [`AGENTS.md`](../AGENTS.md) 即可。

新決策往下追加，不覆寫舊的；決策被推翻時保留原條目並標註「已被 D-xx 取代」。

---

## D-01：本 fork 獨立維護，不回貢上游

**日期**：2026-07-29

**決定**：`SanHsien/usage` 獨立維護，不送 PR 回 [`aqua5230/usage`](https://github.com/aqua5230/usage)。`main` 允許與上游分叉，上游更新選擇性撿。

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
