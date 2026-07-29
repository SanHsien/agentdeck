# Fork 維護指南

本倉庫 fork 自 [`aqua5230/usage`](https://github.com/aqua5230/usage)，但**獨立維護、不回貢上游**。這份文件講只有 fork 才需要知道的事：跟上游的關係、已經分叉了哪些地方、要撿上游更新時怎麼做。

專案本身怎麼運作看 [`CLAUDE.md`](../CLAUDE.md)；Windows 開發環境看 [`DEVELOPMENT.win.zh-TW.md`](DEVELOPMENT.win.zh-TW.md)；agent 工作規則看 [`AGENTS.md`](../AGENTS.md)。

## 定位

- **不打算送 PR 回上游**，所以不需要為了「保持可 PR 的乾淨度」而限制自己。
- `main` 是主線，可以自由發展、允許與上游分叉。
- 任何檔案都可以改，包含上游原有的 `.py`、`CLAUDE.md`、`README*`、`.github/`。
- 上游的更新是**選擇性**撿的，不是義務。

唯一持續有效的約束是授權：上游是 AGPL-3.0-only，本 fork 的所有修改同樣以 AGPL-3.0-only 釋出，`LICENSE` 與上游 attribution 不可移除。詳見 [`NOTICE.md`](../NOTICE.md)。

## Remote 配置

```
origin    https://github.com/SanHsien/usage.git      (本 repo，可推)
upstream  https://github.com/aqua5230/usage.git      (上游，唯讀)
```

`upstream` 已設定好。若在新機器 clone，補上：

```powershell
git remote add upstream https://github.com/aqua5230/usage.git
```

**永遠不要 push 到 `upstream`**（`.claude/settings.json` 已 deny 這條指令）。

## 已與上游分叉之處

改到這些地方時，不要「照上游的樣子改回去」；撿上游更新撞到衝突時，以本欄為準：

| 項目 | 上游 | 本 fork |
|---|---|---|
| README 預設語言 | 英文（`README.md`） | **繁體中文**（`README.md`），英文在 `README.en.md` |
| README 其他語言 | 另有 `README.zh-CN.md` / `README.ja.md` / `README.ko.md` | **已刪除**，不要重新加回 |
| `scripts/check_doc_parity.py` | `DOC_PAIRS` 比對 `README.md` ↔ `README.zh-TW.md` | 改為 `README.en.md` ↔ `README.md` |
| CLAUDE.md 的 Release/changelog 段 | 描述五語 README 與英文預設 | 改寫為中英雙語、繁中預設 |
| 其他文件（CONTRIBUTING / SECURITY / CHANGELOG / docs/DEVELOPMENT） | 英文為預設 `.md`，中文為 `.zh-TW.md` | **維持上游慣例不變** |

新增檔案（上游沒有，不會有衝突）：`AGENTS.md`、`SKILL.md`、`NOTICE.md`、`REPO_REVIEW.md`、`docs/FORK.zh-TW.md`、`docs/DEVELOPMENT.win.zh-TW.md`、`tools/`、`.claude/settings.json`。

## 撿上游更新

不是例行工作，想要某個上游修復時再做：

```powershell
git fetch upstream
git log --oneline HEAD..upstream/main     # 先看上游有什麼
```

決定要全部吃進來：

```powershell
git merge upstream/main
```

只想要某幾個 commit：

```powershell
git cherry-pick <sha>
```

**衝突多半會落在上表列的分叉點上**（尤其 README 與 `check_doc_parity.py`）。解衝突的原則：功能性的改動吃上游，語言／文件結構的決定保留本 fork 的。

合併完**一定要重跑三道 gate**：

```powershell
pwsh tools/dev_check.ps1
```

上游若動了 `uv.lock`，先重新同步相依：

```powershell
uv sync --frozen --group dev --extra windows
```

## 改動須知

- **改 README 要兩邊一起改**：`README.md`（繁中）與 `README.en.md`（英文）的 `##` 章節數必須一致，CI 的 `scripts/check_doc_parity.py` 會擋下不一致。內容也要互相對應翻譯，不要只補一邊。
- **不要在 Windows 上跑 `uv lock`**：`pyproject.toml` 的 `[tool.uv] environments` 是刻意設定的，在 Windows 重 lock 會把 macOS 的 PyObjC 相依標記成不可能達成、無聲地從 lock 檔裡丟掉，直接弄壞 macOS 打包。`.claude/settings.json` 已 deny 這條指令。
- **不要自己 bump 版本或打 `v*` tag**，除非真的要從本 fork 發版——那會觸發 `.github/workflows/release.yml`。
- menu bar（PyObjC）與 `.app` 打包**只能在 macOS 驗收**。動到 `menubar*.py`、`panels/`、`setup_app.py`、`scripts/build_app.sh` 的改動，在 Windows 上無法證明它能跑，要標明「未在 macOS 實測」。
