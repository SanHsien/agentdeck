# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import getpass
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import main
import provider_health
import status_projection

ROOT = Path(__file__).resolve().parents[1]


def test_status_schema_version_and_keys() -> None:
    payload = status_projection.build_status_payload(mock=True)

    assert payload["schema_version"] == 1
    assert isinstance(payload["app_version"], str)
    assert isinstance(payload["generated_at"], str)
    assert isinstance(payload["timestamp"], (int, float))
    assert "providers" in payload

    providers = payload["providers"]
    for name in ("claude", "codex", "antigravity"):
        assert name in providers, f"provider '{name}' missing from status payload"
        entry = providers[name]
        assert "health" in entry
        assert "quota" in entry
        assert "updated_at" in entry

        health = entry["health"]
        assert "state" in health
        assert isinstance(health["usable"], bool)
        assert "reason_key" in health
        assert "next_step_key" in health
        assert "last_updated" in health
        assert "detail" in health


def test_render_json_is_valid_json() -> None:
    raw_json = status_projection.render_json(mock=True)
    decoded = json.loads(raw_json)

    assert decoded["schema_version"] == 1
    assert "providers" in decoded
    assert decoded["providers"]["claude"]["health"]["state"] == "ready"


def test_render_text_contains_summary() -> None:
    text = status_projection.render_text(mock=True)

    assert "agentdeck status (schema v1" in text
    assert "claude" in text
    assert "codex" in text
    assert "antigravity" in text


def test_redaction_masks_usernames_paths_and_tokens() -> None:
    user = getpass.getuser()
    secret_path = r"C:\Users\SecretAgent\workspace\confidential_project"
    secret_posix = "/home/secretagent/keys/id_rsa"
    secret_token = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789"
    secret_ghp = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"

    synthetic_health = [
        provider_health.ProviderHealth(
            provider="claude",
            state=provider_health.HealthState.ERROR,
            reason_key="health_claude_error",
            detail=f"failed for user {user} at {secret_path} with {secret_token}",
        ),
        provider_health.ProviderHealth(
            provider="codex",
            state=provider_health.HealthState.ERROR,
            reason_key="health_codex_error",
            detail=f"posix path {secret_posix} and token {secret_ghp}",
        ),
    ]

    payload = status_projection.build_status_payload(healths=synthetic_health)
    raw_json = json.dumps(payload, ensure_ascii=False)

    assert secret_path not in raw_json
    assert secret_posix not in raw_json
    assert secret_token not in raw_json
    assert secret_ghp not in raw_json
    if len(user) >= 2:
        assert user not in raw_json

    assert "[REDACTED_PATH]" in raw_json
    assert "[REDACTED_TOKEN]" in raw_json


def test_redaction_preserves_standard_model_names() -> None:
    clean = status_projection.redact_text("gpt-5.6-terra")
    assert clean == "gpt-5.6-terra"

    clean_claude = status_projection.redact_text("claude-3-7-sonnet")
    assert clean_claude == "claude-3-7-sonnet"


def test_handles_missing_quota_gracefully() -> None:
    payload = status_projection.build_status_payload(
        healths=[
            provider_health.ProviderHealth(
                provider="claude",
                state=provider_health.HealthState.MISSING,
                reason_key="health_claude_missing",
            )
        ]
    )
    assert payload["schema_version"] == 1
    assert payload["providers"]["claude"]["health"]["state"] == "missing"


def test_main_cli_status_json_flag(capsys: pytest.CaptureFixture[str]) -> None:
    test_args = ["main.py", "--mock", "--status", "--json"]
    sys_argv_backup = sys.argv
    try:
        sys.argv = test_args
        with pytest.raises(SystemExit) as excinfo:
            main.main()
        assert excinfo.value.code == 0
    finally:
        sys.argv = sys_argv_backup

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["schema_version"] == 1
    assert "providers" in data


def test_main_cli_status_text_flag(capsys: pytest.CaptureFixture[str]) -> None:
    test_args = ["main.py", "--mock", "--status"]
    sys_argv_backup = sys.argv
    try:
        sys.argv = test_args
        with pytest.raises(SystemExit) as excinfo:
            main.main()
        assert excinfo.value.code == 0
    finally:
        sys.argv = sys_argv_backup

    captured = capsys.readouterr()
    assert "agentdeck status (schema v1" in captured.out


def test_main_cli_json_without_status_fails() -> None:
    test_args = ["main.py", "--json"]
    sys_argv_backup = sys.argv
    try:
        sys.argv = test_args
        with pytest.raises(SystemExit) as excinfo:
            main.parse_args()
        assert excinfo.value.code != 0
    finally:
        sys.argv = sys_argv_backup


@pytest.mark.skipif(
    shutil.which("powershell") is None and shutil.which("pwsh") is None,
    reason="PowerShell not available",
)
def test_status_json_powershell_smoke() -> None:
    shell = "pwsh" if shutil.which("pwsh") else "powershell"
    script = (
        f"Set-Location '{ROOT}'; "
        "$out = uv run --no-sync python main.py --mock --status --json | ConvertFrom-Json; "
        "if ($out.schema_version -ne 1) { exit 10 }; "
        "if (-not $out.providers.claude) { exit 11 }; "
        "if (-not $out.providers.codex) { exit 12 }; "
        "if (-not $out.providers.antigravity) { exit 13 }; "
        "exit 0"
    )
    res = subprocess.run(  # noqa: S603
        [shell, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, (
        f"PowerShell smoke failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}"
    )
