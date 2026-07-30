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

agentdeck **不呼叫 Anthropic / OpenAI 的用量 API**：Claude Code 與 Codex 的用量數字來自本機狀態檔與 session log，不會上傳這些紀錄。程式會連線到公開價格表、Claude／Codex 公開服務狀態頁、GitHub Release 更新端點，以及使用者已登入的 Antigravity 額度端點；完整範圍見 README 的「隱私」段落。
