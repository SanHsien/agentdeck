#requires -Version 7.0
<#
.SYNOPSIS
    跑本專案的三道 CI gate：ruff check、mypy .、pytest。

.DESCRIPTION
    等同上游 .github/workflows/check.yml 的 Windows job。三項全綠才能 commit。

    另外會把「名稱看起來像機密、但值短到會誤傷」的環境變數從子行程環境移除，
    理由見 -SkipEnvScrub 的說明。

.PARAMETER SkipTests
    只跑 ruff 與 mypy，跳過比較慢的 pytest（約 3.5 分鐘）。

.PARAMETER SkipEnvScrub
    不移除短值機密環境變數。

    discussion_cli.py 會把「名稱含 TOKEN/KEY/SECRET/PASSWORD/PASSWD/CREDENTIAL/AUTH
    的環境變數值」從子行程輸出裡塗成 [REDACTED]。在 Claude Code SDK session 裡，
    CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH 的值是 "1"（名稱含 AUTH），於是輸出中
    每一個 "1" 都被塗掉，test_stdout_diagnostic_tail_has_fixed_line_limit 就炸了。
    這是測試環境汙染，不是 code bug（一般終端機沒有這個變數）。

    加這個參數可以重現原始行為。

.EXAMPLE
    pwsh tools/dev_check.ps1
.EXAMPLE
    pwsh tools/dev_check.ps1 -SkipTests
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipEnvScrub
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'FAIL: 找不到 uv。請先安裝 uv，再跑 uv sync --frozen --group dev --extra windows' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path '.venv')) {
    Write-Host 'FAIL: 沒有 .venv。請先跑：uv sync --frozen --group dev --extra windows' -ForegroundColor Red
    exit 1
}

# 短值的「機密」環境變數會讓 discussion_cli 的塗銷邏輯誤傷普通輸出（見上方說明）。
$scrubbed = @()
if (-not $SkipEnvScrub) {
    $pattern = 'TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH'
    foreach ($item in Get-ChildItem Env:) {
        if ($item.Name -match $pattern -and $item.Value.Length -gt 0 -and $item.Value.Length -le 4) {
            Remove-Item "Env:$($item.Name)"
            $scrubbed += $item.Name
        }
    }
    if ($scrubbed.Count -gt 0) {
        Write-Host "note: 已從本次執行環境移除短值機密變數：$($scrubbed -join ', ')" -ForegroundColor DarkGray
    }
}

$failed = @()

function Test-SymlinkCapability {
    $probeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("usage-symlink-probe-" + [guid]::NewGuid())
    try {
        New-Item -ItemType Directory -Path $probeDir | Out-Null
        $target = Join-Path $probeDir 'target.txt'
        Set-Content -Path $target -Value 'probe'
        New-Item -ItemType SymbolicLink -Path (Join-Path $probeDir 'link.txt') -Target $target -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
    finally {
        if (Test-Path $probeDir) {
            Remove-Item $probeDir -Recurse -Force -Confirm:$false -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-Gate {
    param([string]$Name, [string[]]$Arguments)

    Write-Host ''
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & uv @Arguments
    if ($LASTEXITCODE -ne 0) {
        $script:failed += $Name
        Write-Host "$Name FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    }
    else {
        Write-Host "$Name OK" -ForegroundColor Green
    }
}

Invoke-Gate 'ruff' @('run', '--no-sync', 'ruff', 'check')
Invoke-Gate 'mypy' @('run', '--no-sync', 'mypy', '.')

if ($SkipTests) {
    Write-Host ''
    Write-Host 'pytest 已跳過 (-SkipTests)' -ForegroundColor Yellow
}
else {
    $pytestArgs = @('run', '--no-sync', 'pytest', '-q')

    # test_keeps_matching_directory_and_symlink 需要建立符號連結的權限（開發人員模式
    # 或系統管理員）。沒有權限時它必定丟 WinError 1314，跟被測邏輯無關；先實測本機
    # 能不能建連結，不能才排除這一個測試，並明講排除了什麼。
    if (-not (Test-SymlinkCapability)) {
        Write-Host ''
        Write-Host 'note: 本機沒有建立符號連結的權限（需開發人員模式或系統管理員）。' -ForegroundColor Yellow
        Write-Host '      已排除 test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink，' -ForegroundColor Yellow
        Write-Host '      這條在 CI 上仍會執行。' -ForegroundColor Yellow
        $pytestArgs += @(
            '--deselect',
            'tests/test_usage_dir_sweeper.py::test_keeps_matching_directory_and_symlink'
        )
    }

    Invoke-Gate 'pytest' $pytestArgs
}

Write-Host ''
if ($failed.Count -gt 0) {
    Write-Host "FAIL: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host 'PASS: 全部通過' -ForegroundColor Green
exit 0
