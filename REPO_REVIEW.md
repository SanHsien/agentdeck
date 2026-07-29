# Repo Review

覆核日期：2026-07-29

覆核範圍：fork 初始化。`main` @ `81b89e1`（`usage` v0.29.7，與 `upstream/main` 完全同步，0 ahead / 0 behind）、Windows 11 原生開發環境、三道 CI gate 實跑。

本檔維持 **latest-only**：只記當前狀態與未解問題。修掉任一項就回到對應段落補上修復 commit hash 與日期。

## 結論

- 開發環境已建立並實跑驗證：`ruff check` 綠、`mypy .` 綠（159 個檔案）、`pytest` 1171 passed / 21 skipped / **2 failed**。
- 套用兩項環境處置後（`pwsh tools/dev_check.ps1`）：ruff / mypy / pytest 全綠，1172 passed / 21 skipped / 1 deselected，exit 0。
- 兩個 failed **都是環境問題，不是 code bug**，根因已確認並各有處置（見下）。其中一項暴露了一個真實但低嚴重度的上游缺陷。
- 21 個 skip 全為 macOS / POSIX 專屬（PyObjC、process-group signal、`/bin/sh` quoting），在 Windows 上 skip 是正確行為。
- 尚未在 macOS 驗收任何 menu bar / `.app` 打包路徑——本機是 Windows，這部分**無法**由本次覆核背書。

## 環境

| 項目 | 值 |
|---|---|
| OS | Windows 11 Pro 10.0.26200（原生，非 WSL2） |
| Python | 3.13.14（`.venv`，由 uv 安裝） |
| uv | 0.12.0 |
| 建置指令 | `uv sync --frozen --group dev --extra windows`（等同上游 Windows CI job） |
| 已安裝套件 | 27 個，含 `ruff` 0.16.0、`mypy` 2.3.0、`pytest` 9.1.1、`pystray` 0.19.5、`pywebview` 6.2.1 |

本機預設 `python` 是 3.14.6，**未**用於本專案：`pyproject.toml` 要求 `>=3.13`、mypy 釘 3.13，上游 CI 也是 3.13。

## 未解問題

### P3：短值的「機密」環境變數會讓 `discussion_cli` 的塗銷邏輯誤傷普通輸出

`discussion_cli._redact_environment_values()`（`discussion_cli.py:836`）對名稱符合
`TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH`（`SENSITIVE_ENV_NAME_RE`，`discussion_cli.py:68`）
的環境變數，用 `str.replace()` 把它的值從子行程輸出中無條件塗成 `[REDACTED]`，**沒有長度下限**。

在 Claude Code SDK session 裡，環境有 `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH=1`（名稱含 `AUTH`，值只有一個字元 `"1"`）。
於是輸出中每一個 `1` 都被塗掉：`test_stdout_diagnostic_tail_has_fixed_line_limit` 期望
`lines[0] == "stdout-10"`，實得 `"stdout-[REDACTED]0"`。

- 影響：診斷輸出被無意義地打碎，使用者看不懂錯誤訊息。不是安全漏洞（方向是過度塗銷，不是洩漏）。
- 驗證：`env -u CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH -u CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH uv run pytest tests/test_discussion_cli.py -q`
  → 53 passed / 4 skipped，全綠。確認為環境注入所致。
- 建議修法：塗銷前加值長度下限（例如 `len(value) >= 8`），或改以 word-boundary 比對；並補一個「短值不塗銷」的迴歸測試。
- 本機處置：`tools/dev_check.ps1` 預設把值長度 ≤ 4 的機密名稱環境變數從子行程環境移除（`-SkipEnvScrub` 可還原原始行為）。
- 上游狀態：**未回報**。本 fork 獨立維護、不回貢上游，直接在本 repo 修即可。
- 修復：_未修復_

### P4：`test_keeps_matching_directory_and_symlink` 在無符號連結權限的 Windows 上必定失敗

`tests/test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink` 呼叫 `Path.symlink_to()`，
在未開啟開發人員模式、也非系統管理員的 Windows 上丟 `OSError: [WinError 1314]`。

- 影響：純本機環境限制。上游 Windows CI（`windows-latest`）有建立符號連結的權限，CI 不受影響。
- 處置（擇一）：開啟 Windows 開發人員模式，或以系統管理員身分執行 pytest。
  `tools/dev_check.ps1` 會先實測本機能否建立符號連結，不能才 `--deselect` 這一條並明確告知。
- 上游可考慮的改善：在測試加 `pytest.mark.skipif` 條件（無 symlink 權限則 skip），讓本機結果乾淨。屬體感改善，非必要。
- 修復：_不需修復（環境限制）_

## 已確認正常

- **不呼叫用量 API 的核心不變式**：程式碼中沒有任何 Anthropic / OpenAI 用量 API 呼叫；對外連線僅限 LiteLLM 公開價格表、Claude/OpenAI 公開服務狀態頁、GitHub Releases 更新檢查。與 `CLAUDE.md` 的聲明一致。
- **`uv.lock` 未被污染**：`[tool.uv] environments` 已針對三平台鎖定，`--frozen` 安裝未觸發重新解析，macOS 的 PyObjC 相依仍在 lock 中。
- **`.gitignore` 覆蓋充分**：`.venv/`、`vendor/`（私有 instate-cli 二進位）、`SESSION.md`、各式本機快取均已排除。
- **fork remote 配置正確**：`origin` → `SanHsien/usage`，`upstream` → `aqua5230/usage`。

## 待辦

- [ ] 在本 repo 修掉 P3（含迴歸測試）。
- [ ] 若之後要動 macOS 專屬路徑（`menubar*.py`、`panels/`、`setup_app.py`），需安排 macOS 實測，本機無法驗收。

## 本 fork 的分叉決定（2026-07-29）

- 定位改為**獨立維護、不回貢上游**；`main` 允許與上游分叉，上游更新選擇性撿。
- README 改為繁中預設（`README.md`）、英文為 `README.en.md`；刪除 `zh-CN` / `ja` / `ko` 三個語言版本。
- 連帶調整 `scripts/check_doc_parity.py` 的 `DOC_PAIRS`（改比對 `README.en.md` ↔ `README.md`）與 `CLAUDE.md` 的文件慣例段落，避免文件與實際結構互相矛盾。
- app UI 仍維持五語（`i18n.json` 未動）——只有 README 檔案減為中英兩版。
- 完整分叉清單與撿上游更新的流程見 [`docs/FORK.zh-TW.md`](docs/FORK.zh-TW.md)。
