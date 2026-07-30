# 移植手冊：把 macOS 功能搬到 Windows

本 fork 的目的是**把上游 macOS 的功能搬到 Windows,不是記錄落差然後接受它**（規則見 [`../AGENTS.md`](../AGENTS.md) 開頭）。這份文件記錄實際做過一輪之後歸納出的方法,以及**踩過的坑**。

對照素材在 [`../reference/upstream-macos/`](../reference/upstream-macos/)：已從本 repo 移除的上游 macOS 實作,唯讀。

---

## 一、先盤點：找出「macOS 有、Windows 沒有」的東西

### ⚠️ 這一步我連續錯了三次,方法比直覺重要

盤點的自然做法是比對兩邊用到的 i18n key。**但用錯的 grep 會給出錯的清單**,而錯的清單會讓你去實作早就存在的功能。實際踩到的三個坑：

| 坑 | 症狀 | 正確做法 |
|---|---|---|
| 只比對雙引號 | `grep '"key"'` 漏掉 f-string 裡的 `_t(self.language, 'key')` | **引號無關**：`grep "['\"]key['\"]"` |
| 用單行 regex 掃 `_t(...)` | 跨行的 `_t(\n  self.language,\n  "key"\n)` 完全看不到 | 直接搜 key 本身,不要搜呼叫模式 |
| 假設 key 名稱一致 | Windows 用 `window_keeper_sleep_body_windows`（平台變體）,搜 `window_keeper_sleep_body` 得 0 | 得 0 時**先確認有沒有 `_windows` 之類的變體** |

可靠的盤點指令：

```bash
# 上游用到、但本 repo 沒用到的 i18n key
for k in $(grep -o "\"[a-z_]*\"" reference/upstream-macos/menubar.py | tr -d '"' | sort -u); do
  grep -q "['\"]$k['\"]" wintray.py || echo "$k"
done
```

### 盤點完必做：確認落差是誰造成的

拿 fork 的基準 commit 驗證,不要假設是自己刪出來的：

```bash
git show <base-commit>:wintray.py > /tmp/base.py
grep -c "['\"]the_key['\"]" /tmp/base.py    # 0 = 上游本來就缺,不是你弄掉的
```

這一步救過一次誤判：17 個落差看起來像是移除 macOS 造成的,實測後全部 `base=0`,證明上游本來就缺。**沒驗證就寫進 changelog 說「修復迴歸」是假話。**

---

## 二、判斷可行性：三種結果,不准有第四種

對每個落差,結論只能是這三種。**「平台差異,符合預期」不是可接受的結論。**

### A. 直接可做 → 排進待辦、動手

Windows 有對應的 API 或既有機制。例：上游用 `NSAlert` 顯示 hook 安裝結果,Windows 用 `MessageBoxW`，語意一樣。

### B. 字面上做不到,但**目的**可以達成 → 移植目的

這是最容易被偷懶跳過的一類。做法是問：**這個 UI 存在的目的是什麼?**

實例：上游選單項有 tooltip 說明功能用途,但 pystray 的 `MenuItem` 根本沒有 tooltip 參數。
- ❌ 錯誤結論：「pystray 不支援,無法移植」
- ✅ 正確結論：tooltip 的目的是「讓使用者知道這功能幹什麼」→ 改成**啟用該功能時用對話框說明一次**。目的達成,只是載體不同。

這個 repo 裡 `window_keeper` 早就這樣做（啟用時彈說明）,所以照抄既有模式,不要另創一套。

### C. 真的受阻 → 記下**具體**技術限制

只有這種才准擱置,而且必須寫明卡在什麼,不是含糊的「平台不同」。

實例：AI 人才市場依賴 `vendor/instate-cli` 二進位,由上游一個私有專案建置且已 gitignore —— **跨平台都缺**,不是 Windows 的問題。要做得先自己實作 persona 安裝邏輯。這樣寫,下一個人才知道該從哪裡下手。

---

## 三、實作時的三個規矩

### 1. 平台中立的邏輯不要寫進 `wintray.py`

`wintray.py` 是 UI 外殼,塞進去的判斷邏輯就測不到。凡是「輸入→輸出」的純函式,放進中立模組。

實例：MessageBox 回傳碼要對應到「下載／跳過／稍後」。這段放進 `update_gate.py` 而不是 `wintray.py`,因為前者可以直接單元測試每個回傳碼,後者只能靠開對話框手動點。

### 2. 對話框的按鈕配置要讓「意外」落在安全選項

實作三選項更新提示時我寫錯過一次：把 `MB_YESNOCANCEL` 的 Cancel 對應到「跳過此版本」。但**Escape 與標題列關閉鈕都回傳 `IDCANCEL`** —— 等於使用者按 Escape 就永久跳過該版更新。

原則：**破壞性或不可逆的選項,不能是意外操作會觸發的那一個。** 修正後 No = 跳過（明確點擊）,Cancel/Escape = 稍後（安全）。

### 3. 錯誤不准靜默

移植前 Windows 有五個動作失敗時完全無聲（hook 安裝、statusLine 切換、session resume、terse mode、報告產生）。最糟的是 hook 安裝：失敗後面板永遠顯示 `--`,而那跟「還沒有資料」長得一模一樣,使用者無從判斷。

**動作是使用者主動觸發的,結果就必須回報。** 用 `_report_action_result()`。

---

## 四、驗收

1. `pwsh tools/dev_check.ps1` 全綠（ruff / mypy / doc-parity / ai-updates / pytest）。
2. **純邏輯用測試守,不要靠手動點**。對話框回傳碼、gating 判斷、資源路徑對應,都寫成測試。
3. **UI 行為必須實機驗證**。WebView2 開窗、對話框長相、系統匣選單,測試涵蓋不到,要在桌面實際點一次。這一項無法由 AI 代勞,要請維護者確認。
4. 動到打包相關的東西,跑 `pytest tests/test_packaged_resources.py` —— 它守著「程式碼要求的資源都有宣告給 PyInstaller」,曾經抓到 `--add-data` 目的地與資源名稱不一致。

---

## 五、收尾必做

- 更新 `README.md` 與 `README.en.md`**兩份**,把不合時宜的敘述改掉（章節數要一致,CI 會擋）。
- `CHANGELOG.md` 與 `CHANGELOG.zh-TW.md` 兩份都要寫。
- 把 [`../REPO_REVIEW.md`](../REPO_REVIEW.md) 的「Windows 平台落差移植待辦」對應項目標成完成,或更新受阻原因。
- 版號依 SemVer（見 [`DECISIONS.md`](DECISIONS.md) D-05）：補功能算新增 → MINOR。
