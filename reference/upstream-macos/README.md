# reference/upstream-macos

上游 [`aqua5230/usage`](https://github.com/aqua5230/usage) 的 macOS 實作，於 2026-07-29 從本 repo 移除後，在此保留一份唯讀副本。

## 用途只有一個：移植功能時對照原本的行為

本 fork 的目的是**把 macOS 的功能搬到 Windows**，不是接受平台落差（見 [`../../AGENTS.md`](../../AGENTS.md) 開頭）。要移植某個功能時，來這裡看它原本怎麼做，再用 Windows 的方式重寫。

## 這裡的檔案不參與任何流程

- **不匯入**：沒有任何執行中的程式碼 import 這個目錄。
- **不檢查**：`pyproject.toml` 已把 `reference` 排除在 ruff 與 mypy 之外——這些檔案需要 PyObjC，在 Windows 上根本無法通過檢查。
- **不打包**：`scripts/build_windows.ps1` 不會收錄。
- **不修改**：這是上游的快照。要改就改 Windows 版的實作，不要改這裡。

## 內容

| 檔案 | 原本負責 | Windows 對應 |
|---|---|---|
| `menubar.py` | PyObjC 選單列主控 | `wintray.py` |
| `panels/web_panel.py`、`panels/base.py`、`panels/__init__.py` | NSPopover + WKWebView 面板與面板註冊表 | `wintray.py` 的 WebView2 面板 + `WINDOWS_PANELS` |
| `login_item.py` | LaunchAgent 開機自啟 | `win_login_item.py` |
| `setup_app.py`、`scripts/build_app.sh`、`scripts/build_icns.sh`、`scripts/make_app_icon.py`、`scripts/*.plist`、`scripts/*launchagent.sh` | py2app 打包與 LaunchAgent 安裝 | `scripts/build_windows.ps1` |
| `tests/test_*.py` | 上述模組的測試 | 對應的 Windows 測試 |

`tests/test_packaged_resources.py` 值得特別一提：它守著「程式碼要求的資源都有宣告給打包器」。移除時這道防護一度消失，後來以 PyInstaller 版重寫回來（`../../tests/test_packaged_resources.py`），並藉此發現 `--add-data` 的目的地與資源名稱不一致。**刪掉一個測試前，先想清楚它在擋什麼。**

## 授權

與本專案相同：AGPL-3.0-only，著作權屬上游作者 lollapalooza。保留這份副本不改變任何授權義務。
