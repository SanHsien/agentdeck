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
- 專案更名為 **agentdeck**。上游的美術資產沿用並依 AGPL-3.0 修改：`docs/hero.png` 移除了上游的應用程式圖示，並把字標與副標改為 agentdeck／Windows Tray App；`docs/showcase.*.png`（macOS 實機照）不再於文件中引用。上游原始檔可自[上游 repo](https://github.com/aqua5230/usage) 取得。

逐項變更與日期見 [`CHANGELOG.md`](CHANGELOG.md)；完整修改歷程見本 repo 的 git commit 紀錄。

AGPL-3.0 的重點義務（僅為摘要，以 `LICENSE` 全文為準）：

- 散布本軟體或其修改版時，必須一併提供對應的完整原始碼，並沿用 AGPL-3.0。
- **透過網路提供本軟體的服務**時，也必須讓使用者能取得該版本的原始碼。
- 不得移除或變更原著作權聲明與授權聲明。

本 fork 的所有修改同樣以 AGPL-3.0-only 釋出。

## fork 說明

- 上游：<https://github.com/aqua5230/usage>
- 本 fork：<https://github.com/SanHsien/agentdeck>
- fork 目的：個人使用與 Windows 環境相容性調整，獨立維護、不回貢上游。
- fork 專屬檔案清單與同步流程見 [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。
- 本 fork 與上游維護者、Anthropic、OpenAI 皆無隸屬關係，也未獲其背書。

## 設計參考

`v0.38.0` 的「額度重置後自動續跑」在設計上參考了兩個既有專案。**未複製任何程式碼**——本 repo 的實作為重新撰寫，此處記錄的是概念與設計上的借鑑。查證日期 2026-08-09，記下當時的 commit 與授權狀態，以便日後對照（來源 repo 可能變動或消失）。

### [`chenlu-hung/my-skills` 的 autocontinue](https://github.com/chenlu-hung/my-skills/tree/main/autocontinue)

- 查證版本：`7304f6d65aa6`（2026-08-07）
- 授權：**repo 未附授權聲明**。因此僅參考其架構概念，未取用任何程式碼或檔案。
- 借鑑：整體流程——偵測到額度耗盡後寫入佇列、到重置時間執行續跑、失敗重新入列。其排程載體為 macOS launchd，本專案改用 Windows 排程。

### [`drpwchen/claude-pacer`](https://github.com/drpwchen/claude-pacer)

- 查證版本：`3e31cda9ae22`（2026-08-05）
- 授權：MIT
- 借鑑四項實作細節，取自 `extras/windows/schedule-resume.ps1` 與 `extras/windows/resume-runner.ps1`：
  1. 觸發時間取 `resets_at` 再加緩衝，不卡在重置的當下。
  2. 排程任務設定 `StartWhenAvailable`，錯過觸發時間可在喚醒後補跑。
  3. 一次性任務在執行後自行刪除，不留殘骸。
  4. 使用非互動的 `claude -p` 而非互動式的 `claude --resume`——排程任務沒有終端機，互動模式會無限期等待。

本專案未採用其閾值硬停（hard stop）機制：額度告警沿用既有的 `usage_notifications`，不中止使用者正在進行的工作。

兩者皆與本專案無隸屬關係，亦未對本專案背書。

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
