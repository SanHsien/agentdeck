# NOTICE

本倉庫是 [`aqua5230/usage`](https://github.com/aqua5230/usage) 的 fork。

## 授權

`usage`
Copyright (c) aqua5230 與各貢獻者

本專案依 **GNU Affero General Public License v3.0 only（AGPL-3.0-only）** 授權，完整條款見同目錄的 [`LICENSE`](LICENSE)。

## 修改聲明（AGPL-3.0 §5a）

**本作品是上游 `aqua5230/usage` 的修改版本。** 修改始於 **2026-07-29**，由 [@SanHsien](https://github.com/SanHsien) 進行，並持續維護中。

自該日起的主要修改：

- 專案轉為 **Windows 專用**，移除 macOS 專屬程式碼路徑（授權允許修改包含移除功能；此舉不影響上游版本）。
- 介面語言由五種（`zh-TW` / `zh-CN` / `en` / `ja` / `ko`）精簡為繁體中文與英文兩種。
- 修正 Windows 高 DPI 縮放下面板開在螢幕外的缺陷，以及子行程診斷輸出被過度塗銷的缺陷。
- 文件結構調整：README 改以繁體中文為預設。

逐項變更與日期見 [`CHANGELOG.zh-TW.md`](CHANGELOG.zh-TW.md)；完整修改歷程見本 repo 的 git commit 紀錄。

AGPL-3.0 的重點義務（僅為摘要，以 `LICENSE` 全文為準）：

- 散布本軟體或其修改版時，必須一併提供對應的完整原始碼，並沿用 AGPL-3.0。
- **透過網路提供本軟體的服務**時，也必須讓使用者能取得該版本的原始碼。
- 不得移除或變更原著作權聲明與授權聲明。

本 fork 的所有修改同樣以 AGPL-3.0-only 釋出。

## fork 說明

- 上游：<https://github.com/aqua5230/usage>
- 本 fork：<https://github.com/SanHsien/usage>
- fork 目的：個人使用與 Windows 環境相容性調整，獨立維護、不回貢上游。
- fork 專屬檔案清單與同步流程見 [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。
- 本 fork 與上游維護者、Anthropic、OpenAI 皆無隸屬關係，也未獲其背書。

## 隱私與資料

`usage` 不呼叫 Anthropic 或 OpenAI 的用量 API，用量數字全部來自本機檔案。會連外的只有：

- 下載 [LiteLLM](https://github.com/BerriAI/litellm) 的公開價格表，用於成本估算（本機快取）。
- 讀取 Claude / OpenAI 的**公開服務狀態頁**，用於顯示服務中斷。
- 每天最多一次向 GitHub Releases API 查更新（可關閉）。

以上皆不傳送任何對話內容、token 或帳號資訊。

## 免責

本軟體按「現狀」（AS IS）提供，不附帶任何明示或默示之擔保。在法律允許之最大範圍內，著作人與本 fork 維護者對因使用或無法使用本軟體所生之任何損害概不負責。

## 商標

「Claude」「Claude Code」「Anthropic」「OpenAI」「Codex」「macOS」「Windows」等名稱為其各自所有人之商標，於本專案僅作識別與說明用途，與各該公司或專案無任何隸屬或背書關係。
