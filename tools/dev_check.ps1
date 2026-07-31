#requires -Version 7.0
# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.
<#
.SYNOPSIS
    跑本專案的 CI gate：lock、ruff、mypy、雙語文件、AI 更新頁、pytest。

.DESCRIPTION
    等同 .github/workflows/check.yml。全綠才能 commit。

    這個腳本刻意不動執行環境：跑起來的條件要跟 CI 一致，否則本機的綠燈沒有意義。
    唯一的例外是符號連結權限，那是本機權限限制、CI 上不存在（見下方 pytest 段落）。

.PARAMETER SkipTests
    跑 pytest 以外的五道閘門，跳過比較慢的 pytest（約 3.5 分鐘）。

.EXAMPLE
    pwsh tools/dev_check.ps1
.EXAMPLE
    pwsh tools/dev_check.ps1 -SkipTests
#>
[CmdletBinding()]
param(
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'FAIL: 找不到 uv。請先安裝 uv，再跑 uv sync --frozen --group dev --extra windows' -ForegroundColor Red
    exit 1
}

# UV_PROJECT_ENVIRONMENT moves the environment off the default .venv, which is
# how a checkout inside a OneDrive folder keeps its virtualenv out of the cloud
# placeholder tree. Honour it rather than insisting on .venv.
$ProjectEnv = if ($env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT } else { '.venv' }
if (-not (Test-Path $ProjectEnv)) {
    Write-Host "FAIL: 找不到虛擬環境 $ProjectEnv。請先跑：uv sync --frozen --group dev --extra windows" -ForegroundColor Red
    exit 1
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

Invoke-Gate 'lock' @('lock', '--check')
Invoke-Gate 'ruff' @('run', '--no-sync', 'ruff', 'check')
Invoke-Gate 'mypy' @('run', '--no-sync', 'mypy', '.')
# CI 把雙語文件對稱性當獨立一步跑（.github/workflows/check.yml），這裡跟上，
# 免得 README / CHANGELOG 只改了一邊要等 push 之後才發現。
Invoke-Gate 'doc-parity' @('run', '--no-sync', 'python', 'scripts/check_doc_parity.py')
# ai_updates.json arrives refreshed from upstream merges; without this the
# published page would silently drift behind the data it renders.
Invoke-Gate 'ai-updates' @('run', '--no-sync', 'python', 'scripts/build_ai_updates.py', '--check')

if ($SkipTests) {
    Write-Host ''
    Write-Host 'pytest 已跳過 (-SkipTests)' -ForegroundColor Yellow
}
else {
    $pytestArgs = @('run', '--no-sync', 'pytest', '-q')

    # test_keeps_matching_symlink 需要建立符號連結的權限（開發人員模式或系統管理員）。
    # 沒有權限時它必定丟 WinError 1314，跟被測邏輯無關；先實測本機能不能建連結，不能
    # 才排除這一條，並明講排除了什麼。同一個分支另有 directory 與 junction 兩條測試，
    # 都不需要權限，所以本機仍覆蓋得到「非一般檔案不刪」這個行為。
    if (-not (Test-SymlinkCapability)) {
        Write-Host ''
        Write-Host 'note: 本機沒有建立符號連結的權限（需開發人員模式或系統管理員）。' -ForegroundColor Yellow
        Write-Host '      已排除 test_usage_dir_sweeper.py::test_keeps_matching_symlink，' -ForegroundColor Yellow
        Write-Host '      這條在 CI 上仍會執行；同分支的 directory／junction 兩條照跑。' -ForegroundColor Yellow
        $pytestArgs += @(
            '--deselect',
            'tests/test_usage_dir_sweeper.py::test_keeps_matching_symlink'
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
