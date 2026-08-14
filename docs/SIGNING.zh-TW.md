# Windows 程式碼簽章（SignPath）申請與接線

本檔是給維護者的操作手冊。**目前 `agentdeck.exe` 未簽章**，這份文件記錄要怎麼讓它被簽章、為什麼需要有人親自申請，以及申請通過後要改哪些檔案。

## 為什麼要做

未簽章的執行檔在 Windows 上會被 SmartScreen 攔下，顯示「Windows 已保護您的電腦」，使用者得點「其他資訊 → 仍要執行」才能開。對一個從 GitHub Releases 下載 zip 的工具來說，這是安裝流程裡最容易讓人放棄的一步。

簽章不會讓程式變安全，它只回答一個問題：**這個檔案確實是這個專案發布的，而且從發布後沒有被改過。**

## 為什麼 AI 助理做不完這件事

這一步卡在一個**必須由人完成的外部申請**：SignPath Foundation 要人工審核專案是否符合開源條款，並由一個具名的自然人擔任送件者與批准者。API token 也只會發給申請通過的組織。

所以下面的第 1～3 步得由主人本人執行；第 4 步之後我可以接手。

## 目前狀態

| 項目 | 狀態 |
|---|---|
| exe 的版本資源（產品名／版號） | ✅ 已具備（v0.40.1 起，見 `scripts/make_version_file.py`） |
| SignPath 組織與專案 | ❌ 尚未申請 |
| 發版流程的簽章步驟 | ❌ 尚未接線 |
| README 的簽章政策段落 | ❌ 尚未撰寫（**SignPath 條款要求**） |

版本資源先做是有原因的：SignPath Foundation 的 OSS 條款要求每個被簽章的檔案帶有產品名與版本，沒有它連送件都不會過。

## 步驟 1：申請 SignPath Foundation 的 OSS 方案

到 <https://signpath.org/apply> 送出申請。需要準備：

- **專案的 GitHub 網址**：`https://github.com/SanHsien/agentdeck`
- **授權**：AGPL-3.0-only（開源，符合條款）
- **這個專案是 fork**：申請表上要如實說明它 fork 自 `aqua5230/usage`，並指出本 fork 的改動範圍（Windows-only、兩語、面板架構等）。隱瞞 fork 關係會在審核時被查出來。
- **具名的送件者與批准者**：SignPath 要求真實身分，不能是機器人帳號。

審核需要幾個工作天。通過後會拿到一個 **organization ID**。

## 步驟 2：在 SignPath 建立專案與簽章政策

登入 SignPath 後台：

1. 建立 **Project**，slug 設為 `agentdeck`（下面的 workflow 會用到這個字串）。
2. 建立 **Artifact Configuration**，指定要簽的是 zip 內的 `agentdeck-windows/agentdeck.exe`。
3. 建立 **Signing Policy**：
   - `test-signing`：用測試憑證，先跑通流程用的，**簽出來的檔案不會被 Windows 信任**。
   - `release-signing`：正式憑證。要先用 test-signing 把流程跑通，再申請開啟。

> 上游 `aqua5230/usage` 接線後仍停在 `test-signing`，並自陳整條流程尚未在 CI 實跑過。所以這裡不要假設照抄就會動——先用 test-signing 跑到綠，再換正式政策。

## 步驟 3：在 GitHub repo 設定憑證

`Settings → Secrets and variables → Actions`：

| 類型 | 名稱 | 內容 |
|---|---|---|
| Secret | `SIGNPATH_API_TOKEN` | SignPath 後台產生的 API token |
| Variable | `SIGNPATH_ORGANIZATION_ID` | 步驟 1 拿到的組織 ID |

Token 是 secret，組織 ID 是 variable——組織 ID 不是機密，放 variable 才能在日誌裡看到它，出錯時比較好查。

## 步驟 4：接線發版流程（這步我可以做）

在 `.github/workflows/release.yml` 的 `build-windows` job：

1. `permissions` 加上 `actions: read`（Action 要讀取 artifact）。
2. 打包**之前**先把未簽章的 `dist` 上傳成 artifact。
3. 送 SignPath 簽章並等它回傳。
4. 改成壓縮**簽章後**的目錄。

```yaml
      - name: Resolve version
        id: version
        shell: bash
        run: |
          version=$(uv run --no-sync python -c \
            'import tomllib,pathlib; print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])')
          echo "version=$version" >> "$GITHUB_OUTPUT"

      - name: Upload unsigned bundle for signing
        id: upload-unsigned-artifact
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: agentdeck-windows-unsigned
          path: dist

      - name: Submit signing request
        uses: signpath/github-action-submit-signing-request@b9d91eadd323de506c0c81cf0c7fe7438f3360fd # v2
        with:
          api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
          organization-id: ${{ vars.SIGNPATH_ORGANIZATION_ID }}
          project-slug: agentdeck
          signing-policy-slug: test-signing
          github-artifact-id: ${{ steps.upload-unsigned-artifact.outputs.artifact-id }}
          wait-for-completion: true
          wait-for-completion-timeout-in-seconds: 1800
          output-artifact-directory: dist/signed
          parameters: |
            version: ${{ toJSON(steps.version.outputs.version) }}
```

接著把打包步驟的來源從 `dist/agentdeck-windows` 換成 `dist/signed/agentdeck-windows`。

**注意兩件本 repo 的既有規定**：

- Action 一律用 commit SHA 釘選，不用浮動 tag（Scorecard 會檢查）。
- `${{ }}` **不可以**直接插進 `run:` 區塊——這是 v0.37.5 清乾淨的反模式。上面的 `run:` 只用 shell 變數，`${{ }}` 只出現在 `with:` 與 `env:`。

## 步驟 5：README 加上簽章政策段落（**條款要求，不是選配**）

SignPath Foundation 要求被簽章的專案在說明文件裡公開三件事。README.md 與 README.en.md 都要加，內容照下面的骨架填：

```markdown
### 程式碼簽章政策

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

團隊角色：

- 提交者與審查者：[SanHsien](https://github.com/SanHsien)
- 批准者：[SanHsien](https://github.com/SanHsien)

隱私權政策：除非使用者或安裝、操作此程式的人員明確要求，否則本程式不會將任何資訊傳輸至其他網路系統。本程式代為發出的網路呼叫與如何避免，逐條列於 [SECURITY.md](../SECURITY.md#所有對外連線)。
```

隱私那段可以直接指向 `SECURITY.md` 既有的對外連線表——那張表是逐條列出來且有測試把關的（`tests/test_security_disclosure.py`），比另寫一段散文可信。

## 驗收方式

簽章接上之後，這樣確認它真的生效（不要只看 workflow 綠燈）：

```powershell
Get-AuthenticodeSignature .\dist\agentdeck-windows\agentdeck.exe | Format-List Status, SignerCertificate
```

`Status` 要是 `Valid`。用 test-signing 政策簽出來的會是 `UnknownError` 或 `NotTrusted`——那是預期的，代表流程通了但憑證還不是正式的。

---

**這份文件的狀態**：步驟 1～3 需要主人本人執行；完成後告訴我，步驟 4～5 我來接。
