# personas/

AI 人才市場的角色定義,**本 fork 自製、AGPL-3.0 授權**。

## 為什麼有這個資料夾

上游的人才市場靠一顆閉源二進位 `vendor/instate-cli` 提供角色內容。那個二進位建自上游作者機器上的私有專案,來源與發佈 repo 對外都是 404,而且是 macOS 執行檔 —— 任何人 clone 公開 repo 都拿不到（在 macOS 上也一樣）。詳細查證見 [`../reference/upstream-macos/README.md`](../reference/upstream-macos/README.md)。

本 fork 的做法不是移除這個功能,而是**自己寫一份開源的角色來源**。`persona_store.py` 讀這個資料夾,提供跟原本 CLI 相同的介面,所以既有的面板 UI 與 AI 圓桌討論的角色選單都能直接用。

## 檔案格式

一個 `.json` 檔就是一個 pack（一組角色）。欄位：

```jsonc
{
  "id": "pack-id",              // 必填,英數與連字號
  "name": "顯示名稱",
  "subtitle": "一行說明",
  "icon": "🧭",                  // 單一 emoji
  "roles": [
    {
      "id": "role-id",          // 必填,全域唯一
      "name": "角色名稱",
      "persona_name": "人格代稱",  // 面板上顯示的暱稱
      "description": "這個角色擅長什麼",
      "icon": "🔍",
      "system_prompt": "指派給 subagent 的系統提示",
      "quick_tasks": ["常用任務一", "常用任務二"]
    }
  ]
}
```

多語欄位（`name`、`subtitle`、`description`、`system_prompt`、`quick_tasks`）可以寫成字串,或寫成 `{"zh-TW": "...", "en": "..."}` 讓兩種介面語言各自對應。只寫字串時兩種語言共用。

## 安裝到哪裡

`install_role()` 會把角色寫成 Claude Code 的 subagent 定義,放在 `~/.claude/agents/<role-id>.md`,格式是 YAML frontmatter + 系統提示本文。安裝後若使用者手動改過那個檔案,`list_state()` 會把該角色標成 `drifted`,面板會顯示提示,可選擇還原或忽略。

## 新增角色

1. 在這裡加一個 `.json`（或改既有的 pack）。
2. 跑 `uv run --no-sync pytest tests/test_persona_store.py` —— 測試會驗證 schema、id 唯一性與多語欄位。
3. 兩種介面語言的文字都要寫,否則會回退到另一種語言。
