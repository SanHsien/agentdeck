# OpenSSF Best Practices Badge 申請

本檔是給維護者的操作手冊。**目前本專案沒有 badge**，這份文件記錄要怎麼拿到、為什麼需要有人親自申請，以及**問卷答案的事前查證結果**——那才是這份文件真正的用處。

## 為什麼要做

Scorecard 的 `CIIBestPracticesID` 警告（code scanning alert #7）就是在說這件事：偵測不到這個專案有在爭取 OpenSSF Best Practices badge。這是目前唯一還沒收掉的 code scanning 警告。

badge 本身不會讓程式變安全，它回答的是另一個問題：**這個專案有沒有把基本功做到，而且願意公開對照一份業界清單自我檢核。** 對一個要求使用者從 GitHub Releases 下載 exe 並安裝 hook 進 `~/.claude/` 的工具來說，這個訊號有它的價值。

## 為什麼 AI 助理做不完這件事

badge 是**自我認證**（self-certification）:必須用一個具名的 GitHub 帳號登入 <https://www.bestpractices.dev/>，逐題回答 passing 等級的全部準則（六大類、數十條），而每個答案都是以送件者的身分做出的聲明。這不是我能代替主人做的事——跟 [SignPath](SIGNING.zh-TW.md) 同一個道理，只是那邊卡在人工審核，這邊卡在具名聲明。

**但問卷可以事前準備。** 下面的對照表是實查本 repo 之後的答案，主人登入後照著填即可；需要先改東西的兩項也標出來了。

## 目前狀態

| 項目 | 狀態 |
|---|---|
| 專案本身符合 passing 準則 | ✅ 絕大多數已滿足（見下表） |
| 到 bestpractices.dev 建立專案並填答 | ❌ 需主人本人 |
| README 掛上 badge | ❌ 等拿到 badge 才有得掛 |
| 兩項需要先補的準則 | ⚠️ 見「送件前先補這兩項」 |

## 送件前先補這兩項

**1. 漏洞回報的回應時限沒有明確承諾。**

準則 `vulnerability_report_response` 要求**回應時間 ≤14 天**且寫在文件裡。目前 [`SECURITY.md`](../SECURITY.md) 寫的是「我會盡力在合理時間內回覆並處理」——這句話無法對照那條準則。需要改成明確的天數。

單人維護給 14 天是合理的；寫得出來就答得過，寫不出來這題就得答 Met 以外的選項。

**2. GitHub 的私下漏洞回報管道未啟用。**

實查 `repos/SanHsien/agentdeck/private-vulnerability-reporting` → `enabled: false`。目前 `SECURITY.md` 指向 email（`sanhsien@pm.me`），準則上是**足夠的**，這一項不是必須。

但啟用 GitHub 內建的私下回報有兩個好處:回報者不必信任一個 email 地址、而且 GitHub 的 Security tab 會直接顯示管道。設定位置在 repo 的 **Settings → Advanced Security → Private vulnerability reporting**，一個開關。

## 問卷答案對照表（實查結果）

準則分六類（Basics／Change Control／Reporting／Quality／Security／Analysis）。下面只列需要判斷或有憑據可附的；其餘（FLOSS 授權、版本控制公開可讀等）在填答時是顯而易見的 Met。

### Basics

| 準則 | 答案 | 憑據 |
|---|---|---|
| `description_good` | Met | [`README.md`](../README.md) 開頭一段話說明它做什麼 |
| `interact` / `contribution` | Met | [`CONTRIBUTING.md`](../CONTRIBUTING.md)，含開 Issue、PR 前必跑檢查、commit 風格 |
| `contribution_requirements` | Met | `CONTRIBUTING.md` 的「開 PR 前的必跑檢查」與「改 code 的方針」 |
| `floss_license` / `license_location` | Met | AGPL-3.0-only，[`LICENSE`](../LICENSE) 在 repo 根目錄；GitHub 也辨識為 `AGPL-3.0` |
| `documentation_basics` | Met | `README.md` 有安裝與使用；[`docs/DEVELOPMENT.md`](DEVELOPMENT.md) 給貢獻者 |
| `documentation_interface` | Met | `README.md` 的 CLI 旗標說明、`--doctor` 診斷 |
| `sites_https` | Met | GitHub repo、Releases、GitHub Pages 全部 HTTPS |

### Change Control

| 準則 | 答案 | 憑據 |
|---|---|---|
| `repo_public` / `repo_track` / `repo_interim` | Met | 公開 GitHub repo，每次改動都是獨立 commit，不是只推發布版 |
| `repo_distributed` | Met | git |
| `version_unique` / `version_semver` | Met | SemVer 2.0.0 是本專案的硬性規定，見 [`CLAUDE.md`](../CLAUDE.md) 的 Versioning 段；`pyproject.toml` 是唯一真實來源，並有 `scripts/check_release_version.py` 在 CI 擋掉不比舊版新的 tag |
| `release_notes` | Met | 雙語 CHANGELOG，每個 release 都有 notes |
| `release_notes_vulns` | Met | 安全性修正列在 CHANGELOG 的「安全性」小節（例:v0.41.4） |

### Reporting

| 準則 | 答案 | 憑據 |
|---|---|---|
| `report_process` | Met | GitHub Issues，且有 `.github/ISSUE_TEMPLATE` |
| `report_tracker` | Met | GitHub Issues |
| `report_responses` / `enhancement_responses` | Met | 單人維護但實際有在回應與關閉 issue |
| `report_archive` | Met | GitHub Issues 公開可搜尋 |
| `vulnerability_report_process` | Met | [`SECURITY.md`](../SECURITY.md) 明確要求不要開公開 Issue，給出私下管道 |
| `vulnerability_report_private` | Met | email 管道（若啟用 GitHub 私下回報則更強） |
| `vulnerability_report_response` | ⚠️ **先補** | 見上面「送件前先補這兩項」第 1 點 |

### Quality

| 準則 | 答案 | 憑據 |
|---|---|---|
| `build` / `build_common_tools` / `build_floss` | Met | `uv`（`uv.lock` 為唯一真實來源）+ PyInstaller，`scripts/build_windows.ps1` |
| `test` / `test_invocation` | Met | pytest，`pwsh tools/dev_check.ps1` 一行跑完 CI 的六道閘門 |
| `test_most` | Met | **1,213 個測試、80 個測試檔**（實查） |
| `test_continuous_integration` | Met | `.github/workflows/check.yml`，每次 push 都跑 |
| `test_policy` / `tests_are_added` / `tests_documented_added` | Met | `CONTRIBUTING.md` 要求改動附測試；本專案更進一步要求**新增的閘門必須先證明非空洞**（注入缺陷會紅燈才留下），這個做法記在 [`DECISIONS.md`](DECISIONS.md) 多處 |
| `warnings` / `warnings_fixed` / `warnings_strict` | Met | ruff + mypy **strict**，兩者都是 CI 閘門，紅燈不得合併 |

### Security

| 準則 | 答案 | 憑據 |
|---|---|---|
| `know_secure_design` / `know_common_errors` | Met | 由維護者填答 |
| `crypto_*` | **N/A** | 本專案**不實作任何加密**，也不做身分驗證。唯一的雜湊用途是 release 的 `sha256`。多數 crypto 準則可答 N/A，填答時在說明欄寫明理由 |
| `crypto_used_network` / `crypto_tls12` | Met | 所有對外連線（GitHub API、LiteLLM 價目表、status page）皆為 HTTPS |
| `delivery_mitm` | Met | GitHub Releases over HTTPS，並附 `agentdeck-windows.zip.sha256` |
| `delivery_unsigned` | ⚠️ 部分 | exe **尚未簽章**，見 [`SIGNING.zh-TW.md`](SIGNING.zh-TW.md)。sha256 已提供，這條可答 Met 並在說明欄註明簽章進度 |
| `vulnerabilities_fixed_60_days` | Met | 沒有公開超過 60 天未修的中／高風險漏洞 |
| `no_leaked_credentials` | Met | GitHub secret scanning 已啟用（實查 `secret_scanning: enabled`）；本專案**不呼叫任何需要 API key 的用量 API** |

### Analysis

| 準則 | 答案 | 憑據 |
|---|---|---|
| `static_analysis` | Met | **CodeQL**（`.github/workflows/codeql.yml`）+ ruff + mypy strict |
| `static_analysis_common_vulnerabilities` | Met | CodeQL 的 security query 套件 |
| `static_analysis_fixed` | Met | code scanning 警告都有處置紀錄，見 [`DECISIONS.md`](DECISIONS.md) 的「Code scanning 警告的處置」 |
| `static_analysis_often` | Met | 每次 push |
| `dynamic_analysis` | Met | **ClusterFuzzLite**（`.github/workflows/cflite_pr.yml`、`cflite_batch.yml`） |
| `dynamic_analysis_unsafe` | **N/A** | Python，非記憶體不安全語言 |

## 步驟 1：先補上面那兩項（可交給我）

改 `SECURITY.md` 的回應時限；要的話一併啟用 GitHub 私下回報。這兩件我可以做，說一聲即可。

## 步驟 2：登入並建立專案（需主人本人）

1. 到 <https://www.bestpractices.dev/>，用 GitHub 帳號登入。
2. 點 **Get Your Badge Now!**，填入 repo 網址 `https://github.com/SanHsien/agentdeck`。
3. 網站會自動抓取部分資訊（授權、語言、repo 統計），並自動判定一部分準則。

## 步驟 3：逐題填答（需主人本人）

照上面的對照表填。幾個提醒：

- **crypto 類多半是 N/A**，但要在說明欄寫理由，空白的 N/A 會被視為未答。
- 每題都有 **Met / Unmet / N/A** 與一個說明欄。說明欄填上憑據網址（例如指向 `CONTRIBUTING.md`、`check.yml`）比只勾 Met 更站得住，日後也方便自己回頭查。
- 達到 **100%** 才會發 passing badge，中途可以存檔離開。

## 步驟 4：掛上 badge 並驗證（可交給我）

拿到之後：

1. 把 badge markdown 加進 `README.md` 的 badge 列（第 13～17 行那一區）與 `README.en.md`——**兩邊都要改**，`scripts/check_doc_parity.py` 會擋。
2. 等 Scorecard 下次執行，確認 `CIIBestPracticesID` 這個 alert 自動關閉。
3. 在 [`DECISIONS.md`](DECISIONS.md) 把「Code scanning 警告的處置」那節的 #7 狀態更新掉。

## 之後的等級

passing 之上還有 **Silver** 與 **Gold**。Gold 要求「至少兩位主要開發者」，單人專案拿不到；Silver 部分準則（例如需要有其他人 review 變更）也受同一個限制擋住——這跟 Scorecard 的 `CodeReviewID` 在單人 repo 永遠是 0 分是同一件事。**先拿 passing 就好**，這也是 Scorecard 偵測的那一級。
