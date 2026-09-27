# reference/upstream-macos

上游 [`aqua5230/usage`](https://github.com/aqua5230/usage) 的 macOS 實作，於 2026-07-29 從本 repo 移除後，在此保留一份唯讀副本。

## 用途只有一個：移植功能時對照原本的行為

本 fork 的目的是**把 macOS 的功能搬到 Windows**，不是接受平台落差（見 [`../../AGENTS.md`](../../AGENTS.md) 開頭）。要移植某個功能時，來這裡看它原本怎麼做，再用 Windows 的方式重寫。

## 這裡的檔案不參與任何流程

- **不匯入**：沒有任何執行中的程式碼 import 這個目錄。
- **不檢查**：`pyproject.toml` 已把 `reference` 排除在 ruff 與 mypy 之外——這些檔案需要 PyObjC，在 Windows 上根本無法通過檢查。
- **不打包**：`scripts/build_windows.ps1` 不會收錄。
- **不修改**：這是上游的快照。要改就改 Windows 版的實作，不要改這裡。

## 不需要整份複製上游

這裡只放**已從本 repo 刪除**的檔案。上游其餘內容不必複製，因為 `upstream/main` 是已設定的 remote，任何檔案隨時取得：

```bash
git fetch upstream
git show upstream/main:path/to/file.py     # 取任何一個檔案
git log upstream/main -- path/to/file.py   # 連它的歷史都有
git diff HEAD upstream/main -- path/        # 跟我們的版本比對
```

整份複製只會讓資料重複（git 已經存了）、立刻過時（remote 才是活的）、污染 grep 與檢查、膨脹 repo。**要看上游任何東西，用上面的指令，不要往這個資料夾加檔案。**

## 內容

| 檔案 | 原本負責 | Windows 對應 |
|---|---|---|
| `menubar.py` | PyObjC 選單列主控 | `wintray.py` |
| `panels/web_panel.py`、`panels/base.py`、`panels/__init__.py` | NSPopover + WKWebView 面板與面板註冊表 | `wintray.py` 的 WebView2 面板 + `WINDOWS_PANELS` |
| `login_item.py` | LaunchAgent 開機自啟 | `win_login_item.py` |
| `setup_app.py`、`scripts/build_app.sh`、`scripts/build_icns.sh`、`scripts/make_app_icon.py`、`scripts/*.plist`、`scripts/*launchagent.sh` | py2app 打包與 LaunchAgent 安裝 | `scripts/build_windows.ps1` |
| `tests/test_*.py` | 上述模組的測試 | 對應的 Windows 測試 |

## AI 人才市場：為什麼它不是「移植」問題

`talent_market_bridge.py` **還在本 repo 裡，而且早就是平台中立的**。它做的事只是 shell out 到 `vendor/instate-cli`，那個二進位：

- 建自 `/Users/lollapalooza/Developer/instate` —— 上游作者機器上的**私有專案**，路徑寫死在 `scripts/build_app.sh:11`。
- 備援下載自 `aqua5230/instate-cli-dist`，需要 `INSTATE_CLI_TOKEN`（`build_app.sh:26`）。
- 這兩個 repo 對外都是 404（2026-07-30 實測）。
- 內容本身是私有的，不只是程式碼：`.gitignore` 寫「Contains private role content — must never enter usage's public git history」。
- 就算取得，它是在 macOS 上用 `bun run build:cli` 編的，**Windows 無法執行**。

所以任何人 clone 公開 repo，在 macOS 上也拿不到這個功能（`_cli_path()` 回 `missing`）。**缺的不是 Windows 實作，是閉源的內容載荷。**

要在本 fork 有這個功能，得自己寫一套 persona 來源：產生 subagent 定義寫進 `~/.claude/agents/`。那是**開一個新功能**，不是移植既有功能，規模與風險都不同，應當作獨立提案評估。

`tests/test_packaged_resources.py` 值得特別一提：它守著「程式碼要求的資源都有宣告給打包器」。移除時這道防護一度消失，後來以 PyInstaller 版重寫回來（`../../tests/test_packaged_resources.py`），並藉此發現 `--add-data` 的目的地與資源名稱不一致。**刪掉一個測試前，先想清楚它在擋什麼。**

## 授權

與本專案相同：AGPL-3.0-only，著作權屬上游作者 lollapalooza。保留這份副本不改變任何授權義務。
