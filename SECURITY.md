# 安全政策

> English version: [SECURITY.en.md](SECURITY.en.md)

## 回報安全漏洞

如果你發現 agentdeck 的安全漏洞，**請勿開公開 Issue**。請改用私下管道回報：

📧 **sanhsien@pm.me**

回報時請盡量包含：

- 受影響的版本（或 commit）
- 重現步驟，或概念驗證（PoC）
- 你評估的影響範圍

本專案為單人維護，我會盡力在合理時間內回覆並處理。修復釋出後會在 release notes 中致謝（除非你希望匿名）。

## 支援版本

agentdeck 採滾動發布，安全修復只針對**最新發布版**。回報前請先確認你使用的是 [最新 release](https://github.com/SanHsien/agentdeck/releases/latest)。

## 安全設計

agentdeck **不呼叫任何 LLM 用量 API**——看額度這件事本身永遠不會消耗你的 token。你的提示詞、對話內容與用量數字都不會離開你的電腦。

**Claude Code 與 Codex** 的數字完全來自你本機磁碟上既有的檔案：Claude Code 的狀態列 hook 寫入的狀態檔，以及 Codex 的 session log。讀這兩者完全不需要連網。

**Antigravity 不一樣，這點要講明白**：它的額度不在你的磁碟上，所以 agentdeck 會透過網路取得。

### 所有對外連線

| 用途 | 端點 | 時機 |
|---|---|---|
| Antigravity 額度 | `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` | 程式執行期間定期取得，且僅在 Antigravity 已登入時 |
| Antigravity token 更新 | `https://oauth2.googleapis.com/token` | 本機存的 access token 過期時 |
| 服務狀態警示 | `https://status.claude.com/api/v2/summary.json`<br>`https://status.openai.com/api/v2/summary.json` | 每 5 分鐘（`service_status.CACHE_TTL_SECONDS`） |
| Token 價目表 | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` | 首次需要時，之後每 7 天（`pricing.CACHE_TTL_DAYS`） |
| 更新檢查 | `https://api.github.com/repos/SanHsien/agentdeck/releases/latest` | 最多每 24 小時一次（`update_gate.AUTO_CHECK_TTL_SECONDS`），可從選單關閉 |

以上沒有任何一項會夾帶你的用量資料、提示詞或對話內容。狀態、價目表與更新檢查這三個端點都是不帶驗證的單純 GET。

`tools/check_upstream_updates.py` 也會連 `https://api.github.com`，但它是維護者的 CI 工具，不隨程式散布、不會在你的電腦上執行。

**每個回應都有讀取上限**（`MAX_RESPONSE_BYTES`）：`urlopen().read()` 不帶參數就是對方送多少收多少，所以上述每一處都改為讀「上限+1 位元組」後拒絕。

### 憑證存取

為了讀取 Antigravity 額度，agentdeck 會讀取 Antigravity CLI 本來就存在你電腦上的 OAuth 憑證（Windows 的**認證管理員**）。這個存取是唯讀的：agentdeck 不會寫入或修改該憑證，也不會把它送到 Google 自己的 token 與額度端點以外的任何地方——跟 Antigravity CLI 本身的做法一樣。**如果你沒有使用 Antigravity，agentdeck 永遠不會讀取任何憑證。**

Claude Code 與 Codex 則完全不需要任何憑證存取。

### 關於原始碼裡的 OAuth client 常數

`providers/agy_quota_probe.py` 裡有明文的 `_CLIENT_ID` 與 `_CLIENT_SECRET`（`GOCSPX-` 開頭）。**這不是外洩的憑證**：依 [RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252)，安裝在使用者電腦上的應用程式無法保密 client secret，因此這是一個 *public client*，不構成安全邊界。它不是你的憑證，本身也不授予任何權限——授權來自你電腦上那份 Antigravity 的 OAuth token。祕密掃描工具會標記這個前綴，這是預期內的。若 Google 輪替這組常數，token 請求會失敗、探測回傳 `None`，只有 Antigravity 額度會消失。
