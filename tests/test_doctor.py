# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

import doctor
import setup_hook
from providers import codex_loader


def test_doctor_handles_missing_settings_and_status_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(setup_hook, "CLAUDE_SETTINGS", tmp_path / ".claude" / "settings.json")
    monkeypatch.setattr(setup_hook, "HOOK_TARGET", tmp_path / ".claude" / "agentdeck-statusline.py")
    monkeypatch.setattr(
        setup_hook,
        "FORWARDER_TARGET",
        tmp_path / ".claude" / "agentdeck-statusline-forwarder.py",
    )
    monkeypatch.setattr(setup_hook, "STATUS_FILE", tmp_path / ".claude" / "agentdeck-status.json")
    monkeypatch.setattr(codex_loader, "SESSIONS_DIR", tmp_path / ".codex" / "sessions")
    monkeypatch.setattr(codex_loader, "LOGS_DB", tmp_path / ".codex" / "logs_2.sqlite")
    monkeypatch.setattr(codex_loader, "STATE_DB", tmp_path / ".codex" / "state_5.sqlite")
    monkeypatch.setattr(codex_loader, "load_rate_limits", lambda: None)

    output = doctor.render()

    assert "agentdeck v" in output
    assert "hook state:        none" in output
    assert "status file:" in output
    assert "self-heal log (last 5):\n  none" in output


def test_doctor_reports_external_hook_keyword(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    settings.write_text(
        json.dumps({"statusLine": {"type": "command", "command": "node /opt/ccusage/bin/cli"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_hook, "CLAUDE_SETTINGS", settings)
    monkeypatch.setattr(setup_hook, "STATUS_FILE", claude_dir / "agentdeck-status.json")
    monkeypatch.setattr(codex_loader, "SESSIONS_DIR", tmp_path / ".codex" / "sessions")
    monkeypatch.setattr(codex_loader, "LOGS_DB", tmp_path / ".codex" / "logs_2.sqlite")
    monkeypatch.setattr(codex_loader, "STATE_DB", tmp_path / ".codex" / "state_5.sqlite")
    monkeypatch.setattr(codex_loader, "load_rate_limits", lambda: None)

    output = doctor.render()

    assert "hook state:        external" in output
    assert "external hooks:    ccusage" in output


def test_doctor_flags_windows_backslash_statusline_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": (
                        r"C:\Python\python.exe "
                        r"C:\Users\test\.claude\agentdeck-statusline.py"
                    ),
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(setup_hook, "CLAUDE_SETTINGS", settings)

    output = doctor.render()

    assert "status command:    Windows Git Bash-incompatible paths" in output


def test_doctor_reports_codex_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    claude_dir = tmp_path / ".claude"
    codex_dir = tmp_path / ".codex"
    sessions_dir = codex_dir / "sessions"
    logs_db = codex_dir / "logs_2.sqlite"
    state_db = codex_dir / "state_5.sqlite"
    session_path = sessions_dir / "2026" / "01" / "01" / "session.jsonl"
    session_path.parent.mkdir(parents=True)
    session_path.write_text("{}", encoding="utf-8")
    now = datetime.now(UTC)
    os.utime(session_path, (now.timestamp(), now.timestamp()))
    codex_dir.mkdir(exist_ok=True)
    with sqlite3.connect(logs_db) as conn:
        conn.execute("CREATE TABLE logs (feedback_log_body TEXT)")
        conn.executemany(
            "INSERT INTO logs (feedback_log_body) VALUES (?)",
            [
                ("websocket event: {\"type\":\"codex.rate_limits\"}",),
                ("websocket event: {\"type\":\"error\",\"error\":\"usage_limit_reached\"}",),
                ("other",),
            ],
        )
    state_db.write_text("", encoding="utf-8")
    monkeypatch.setattr(setup_hook, "CLAUDE_SETTINGS", claude_dir / "settings.json")
    monkeypatch.setattr(setup_hook, "STATUS_FILE", claude_dir / "agentdeck-status.json")
    monkeypatch.setattr(codex_loader, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(codex_loader, "LOGS_DB", logs_db)
    monkeypatch.setattr(codex_loader, "STATE_DB", state_db)
    monkeypatch.setattr(
        codex_loader,
        "load_rate_limits",
        lambda: codex_loader.CodexRateLimits(
            five_hour_pct=None,
            five_hour_resets_at=None,
            seven_day_pct=12.0,
            seven_day_resets_at=now.timestamp() + 3600,
            model="gpt-test",
            updated_at=now.isoformat(),
        ),
    )

    output = doctor.render()

    assert "codex jsonl:       1 files, latest wrote" in output
    assert "codex logs:" in output
    assert "[ok], rate_limit rows: 2" in output
    assert "codex state:" in output
    assert "[ok]" in output
    assert "codex rate limits: 5h: no, weekly: yes, updated:" in output


@pytest.fixture
def isolated_doctor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import status_projection

    for name in ("HOOK_TARGET", "FORWARDER_TARGET", "STATUS_FILE", "CLAUDE_SETTINGS"):
        monkeypatch.setattr(setup_hook, name, tmp_path / name)
    for name in ("SESSIONS_DIR", "LOGS_DB", "STATE_DB"):
        monkeypatch.setattr(codex_loader, name, tmp_path / name)
    monkeypatch.setattr(codex_loader, "load_rate_limits", lambda: None)
    monkeypatch.setattr(setup_hook, "_load_settings", lambda: {})
    monkeypatch.setattr(
        status_projection, "build_status_payload",
        lambda: {"schema_version": 1, "app_version": "0.42.2",
                 "generated_at": "2026-11-02T00:00:00+00:00", "timestamp": 1793577600,
                 "providers": {"claude": {"health": {"detail": ""}, "quota": None}}},
    )


def test_doctor_json_schema_and_missing_files(isolated_doctor: None) -> None:
    payload = json.loads(doctor.render_json())
    assert payload["schema_version"] == 1
    assert payload["app_version"] == "0.42.2"
    assert payload["generated_at"] == "2026-11-02T00:00:00+00:00"
    assert "providers" in payload
    diagnostics = payload["diagnostics"]
    assert set(diagnostics) == {"environment", "checks", "files", "self_heal_log"}
    assert diagnostics["environment"]["python_version"]
    assert diagnostics["checks"]["hook_state"] == "none"
    assert diagnostics["checks"]["codex_rate_limits"] == "none"
    assert diagnostics["files"]["hook_script"]["exists"] is False
    assert diagnostics["files"]["status_file"]["exists"] is False
    assert diagnostics["self_heal_log"] == []


def test_doctor_json_redacts_untrusted_diagnostics(
    isolated_doctor: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import status_projection

    user = "FixtureMaintainer"
    project = str(tmp_path / "private project")
    token = "fixture-credential-do-not-disclose"
    message = f"{user} {project} {token}"
    monkeypatch.setattr(status_projection, "_user_names", lambda: {user})
    monkeypatch.setattr(setup_hook, "HOOK_TARGET", tmp_path / "private project" / "hook.py")
    monkeypatch.setattr(setup_hook, "_load_settings", lambda: {
        setup_hook.BACKUP_KEY: {"selfHealLog": [
            {"timestamp": "2026-11-02T00:00:00+00:00", "action": message, "detail": message}
        ]},
    })

    def broken() -> str:
        raise OSError(message)

    monkeypatch.setattr(doctor, "_codex_sessions", broken)
    payload = json.loads(doctor.render_json())
    text = json.dumps(payload)
    for private in (user, project, token):
        assert private not in text
    assert payload["diagnostics"]["checks"]["codex_sessions"] == {"error": "OSError"}
    assert "[REDACTED]" in text


def test_main_doctor_json_is_headless(
    isolated_doctor: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    import main

    def forbidden() -> None:
        pytest.fail("doctor must not initialize UI, repair hooks or launch a provider")

    monkeypatch.setattr(main, "_self_heal", forbidden)
    monkeypatch.setattr(main, "health_check", forbidden)
    monkeypatch.setattr(main, "run_tui", forbidden)
    monkeypatch.setattr(sys, "argv", ["main.py", "--doctor", "--json"])
    with pytest.raises(SystemExit) as result:
        main.main()
    assert result.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "diagnostics" in json.loads(captured.out)


def test_doctor_and_status_are_mutually_exclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    import main

    monkeypatch.setattr(sys, "argv", ["main.py", "--doctor", "--status", "--json"])
    with pytest.raises(SystemExit) as result:
        main.parse_args()
    assert result.value.code == 2


def test_doctor_json_uses_real_shared_projection_without_ui_or_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main
    import provider_health
    import provider_probe
    import status_projection

    private = "fixture-credential-do-not-disclose"
    calls = []

    def healths(*, now: float) -> list[provider_health.ProviderHealth]:
        calls.append(now)
        return [provider_health.ProviderHealth(
            provider="claude", state=provider_health.HealthState.ERROR,
            reason_key="health_claude_error", detail=private,
        )]

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("headless diagnostics must not write settings or initialize UI")

    for name in ("HOOK_TARGET", "FORWARDER_TARGET", "STATUS_FILE", "CLAUDE_SETTINGS"):
        monkeypatch.setattr(setup_hook, name, tmp_path / name)
    monkeypatch.setattr(setup_hook, "_load_settings", lambda: {})
    monkeypatch.setattr(setup_hook, "_save_settings", forbidden)
    monkeypatch.setattr(provider_probe, "collect_provider_health", healths)
    for name in ("_collect_claude_quota", "_collect_codex_quota", "_collect_antigravity_quota"):
        monkeypatch.setattr(status_projection, name, lambda **kwargs: None)
    monkeypatch.setattr(codex_loader, "load_rate_limits", lambda: None)
    for name in ("wintray", "webview", "pystray", "tui"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(main, "_self_heal", forbidden)
    monkeypatch.setattr(sys, "argv", ["main.py", "--doctor", "--json"])
    with pytest.raises(SystemExit) as result:
        main.main()
    assert result.value.code == 0
    output = capsys.readouterr()
    payload = json.loads(output.out)
    assert output.err == ""
    assert len(calls) == 1
    assert payload["schema_version"] == 1
    assert set(payload) == {
        "schema_version", "app_version", "generated_at", "timestamp", "providers", "diagnostics"
    }
    assert set(payload["providers"]) == {"claude", "codex", "antigravity"}
    assert payload["providers"]["claude"]["health"]["state"] == "error"
    assert private not in output.out
    assert payload["providers"]["codex"]["health"]["state"] == "missing"
    assert not list(tmp_path.iterdir())


def test_doctor_json_log_retains_last_five_safe_actions(
    isolated_doctor: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(setup_hook, "_load_settings", lambda: {
        setup_hook.BACKUP_KEY: {"selfHealLog": [
            {"timestamp": f"2026-11-02T00:00:0{index}Z", "action": "update_hook", "detail": ""}
            for index in range(7)
        ]},
    })
    entries = json.loads(doctor.render_json())["diagnostics"]["self_heal_log"]
    assert len(entries) == 5
    assert entries[0]["timestamp"] == "2026-11-02T00:00:02+00:00"
    assert entries[-1]["action"] == "update_hook"


def test_doctor_json_failed_file_and_corrupt_log_are_reported(
    isolated_doctor: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_file(path: Path) -> dict[str, object]:
        raise PermissionError("fixture-private-project")

    monkeypatch.setattr(doctor, "_file_info", broken_file)
    monkeypatch.setattr(setup_hook, "_load_settings", lambda: {
        setup_hook.BACKUP_KEY: {"selfHealLog": [None, {"timestamp": "invalid"}]},
    })
    payload = json.loads(doctor.render_json())
    assert payload["diagnostics"]["files"]["hook_script"] == {"error": "PermissionError"}
    assert payload["diagnostics"]["self_heal_log"][0]["timestamp"] == "unknown"
    assert "fixture-private-project" not in json.dumps(payload)


@pytest.mark.parametrize("installed", ["1.9", "fixture-credential-do-not-disclose"])
def test_doctor_json_validates_installed_hook_version(
    isolated_doctor: None, monkeypatch: pytest.MonkeyPatch, installed: str,
) -> None:
    monkeypatch.setattr(setup_hook, "_installed_hook_version", lambda: installed)
    check = json.loads(doctor.render_json())["diagnostics"]["checks"]["hook_version"]
    assert check == {
        "installed": installed if installed == "1.9" else "[REDACTED]",
        "current": setup_hook.HOOK_VERSION,
    }
