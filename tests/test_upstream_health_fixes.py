# SPDX-License-Identifier: AGPL-3.0-only
# Ported from aqua5230/usage 709ed56d; adapted for agentdeck.
from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

import session_hooks
import setup_hook
import usage_cli
from i18n import t as _t
from providers.history_loader import UsageEntry
from tests.helpers import SetupHookPaths, expected_statusline_command


@pytest.fixture
def setup_paths(patch_setup_hook_paths: Callable[..., SetupHookPaths]) -> SetupHookPaths:
    return patch_setup_hook_paths()


@pytest.mark.parametrize("parked_kind", ["usage", "external", "null"])
def test_self_heal_respects_disabled_statusline(
    monkeypatch: pytest.MonkeyPatch, setup_paths: SetupHookPaths, parked_kind: str
) -> None:
    parked = {
        "usage": {
            "type": "command",
            "command": expected_statusline_command(setup_paths.hook_target),
        },
        "external": {"type": "command", "command": "echo original"},
        "null": None,
    }[parked_kind]
    setup_paths.settings.write_text(
        json.dumps({setup_hook.BACKUP_KEY: {"disabledStatusLine": parked}})
    )
    calls: list[str] = []

    def install() -> int:
        calls.append("setup")
        return 0

    monkeypatch.setattr(session_hooks, "setup", install)

    session_hooks.self_heal()

    assert calls == []
    assert "statusLine" not in setup_hook._load_settings()
    assert setup_hook._load_settings()[setup_hook.BACKUP_KEY]["disabledStatusLine"] == parked


@pytest.mark.parametrize(
    ("active", "parked", "previous", "expected", "keep_parked"),
    [
        ("usage", None, "original", "original", False),
        (None, "usage", "original", "original", False),
        (None, "external", None, "external", False),
        ("usage", "external", None, "external", False),
        ("external", "parked", None, "external", True),
    ],
)
def test_unsetup_preserves_parked_statusline(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
    active: str | None,
    parked: str | None,
    previous: str | None,
    expected: str,
    keep_parked: bool,
) -> None:
    def statusline(kind: str) -> dict[str, str]:
        command = (
            expected_statusline_command(setup_paths.hook_target)
            if kind == "usage"
            else f"echo {kind}"
        )
        return {"type": "command", "command": command}

    settings: dict[str, Any] = {"env": {"KEEP": "yes"}, setup_hook.BACKUP_KEY: {"keep": True}}
    if active is not None:
        settings["statusLine"] = statusline(active)
    if parked is not None:
        settings[setup_hook.BACKUP_KEY]["disabledStatusLine"] = statusline(parked)
    if previous is not None:
        settings[setup_hook.BACKUP_KEY]["previousStatusLine"] = statusline(previous)
    setup_hook._save_settings(settings)
    monkeypatch.setattr(
        setup_hook, "LEGACY_TT_HOOK_TARGET", setup_paths.settings.parent / "tt-statusline.py"
    )

    assert setup_hook.unsetup() == 0

    result = setup_hook._load_settings()
    assert result["statusLine"] == statusline(expected)
    assert result["env"] == {"KEEP": "yes"}
    assert result[setup_hook.BACKUP_KEY]["keep"] is True
    assert ("disabledStatusLine" in result[setup_hook.BACKUP_KEY]) == keep_parked
    if keep_parked:
        assert result[setup_hook.BACKUP_KEY]["disabledStatusLine"] == statusline("parked")


def test_unsetup_keeps_parked_backup_when_save_fails(
    monkeypatch: pytest.MonkeyPatch, setup_paths: SetupHookPaths
) -> None:
    settings = {
        setup_hook.BACKUP_KEY: {
            "disabledStatusLine": {
                "type": "command",
                "command": expected_statusline_command(setup_paths.hook_target),
            },
            "previousStatusLine": {"type": "command", "command": "echo original"},
        }
    }
    setup_hook._save_settings(settings)
    before = setup_paths.settings.read_bytes()

    def fail_save(_settings: dict[str, Any]) -> None:
        raise OSError("save failed")

    monkeypatch.setattr(setup_hook, "_save_settings", fail_save)
    with pytest.raises(OSError, match="save failed"):
        setup_hook.unsetup()
    assert setup_paths.settings.read_bytes() == before


@pytest.mark.parametrize("operation", ["replace", "insert", "remove", "ensure"])
def test_toml_edits_reject_fake_headers_in_multiline_instructions(operation: str) -> None:
    name = "features" if operation == "ensure" else "tui"
    line = "hooks = false" if operation == "ensure" else 'status_line = ["model"]'
    content = (
        'developer_instructions = """\nKeep this example:\n'
        f'[{name}]\n{line}\n"""\n\n[{name}]\n{line}\n'
    )
    if operation == "replace":
        result = setup_hook._replace_tui_status_line(content, 'status_line = ["usage"]')
    elif operation == "insert":
        content = content.rsplit(line, 1)[0] + "keep = true\n"
        result = setup_hook._insert_tui_status_line(content, 'status_line = ["usage"]')
    elif operation == "remove":
        result = setup_hook._remove_tui_status_line(content)
    else:
        result = setup_hook._ensure_table_line(
            content, "features", session_hooks._FEATURES_HOOKS_REGEX, "hooks = true"
        )
    assert result == content


def test_codex_setup_preserves_multiline_instructions_and_reports_rejected_edit(
    setup_paths: SetupHookPaths, capsys: pytest.CaptureFixture[str]
) -> None:
    content = (
        'developer_instructions = """\nKeep this example:\n[tui]\n'
        'status_line = ["model"]\n"""\n\n[tui]\nstatus_line = ["model"]\n'
    )
    setup_hook.CODEX_CONFIG.parent.mkdir()
    setup_hook.CODEX_CONFIG.write_text(content)
    backup = '{"status_line": ["original"]}'
    setup_hook.CODEX_BACKUP.write_text(backup, encoding="utf-8")

    setup_hook._setup_codex()

    assert setup_hook.CODEX_CONFIG.read_text() == content
    assert setup_hook.CODEX_BACKUP.read_text(encoding="utf-8") == backup
    output = capsys.readouterr().out
    assert _t("setup_codex_config_unmodifiable") in output
    assert _t("setup_codex_configured") not in output


def test_codex_setup_verifies_written_statusline(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_hook.CODEX_CONFIG.parent.mkdir()
    setup_hook.CODEX_CONFIG.write_text('[tui]\nstatus_line = ["model"]\n')
    monkeypatch.setattr(setup_hook, "_atomic_write_text", lambda path, text: None)

    setup_hook._setup_codex()

    output = capsys.readouterr().out
    assert _t("setup_codex_config_unmodifiable") in output
    assert _t("setup_codex_configured") not in output


@pytest.mark.parametrize("sort_key", ["sessions", "unknown"])
def test_session_sort_rejects_missing_attributes_and_lists_only_valid_keys(
    monkeypatch: pytest.MonkeyPatch,
    sort_key: str,
) -> None:
    first = SimpleNamespace(
        start_time=1, total_tokens=1, cost_usd=1, message_count=1, input_tokens=1, output_tokens=1
    )
    second = SimpleNamespace(
        start_time=2, total_tokens=1, cost_usd=1, message_count=1, input_tokens=1, output_tokens=1
    )
    stats = [first, second]
    messages: list[tuple[str, dict[str, str]]] = []

    def translate(key: str, **kwargs: str) -> str:
        messages.append((key, kwargs))
        return key

    monkeypatch.setattr(usage_cli, "t", translate)
    monkeypatch.setattr("usage_cli.console.print", lambda value: None)

    usage_cli._apply_sort(stats, sort_key, False, "start_time", True)

    assert stats == [second, first]
    assert messages == [
        (
            "unknown_sort_field",
            {
                "field": sort_key,
                "valid": "tokens, cost, messages, time, input, output",
            },
        )
    ]


@pytest.mark.parametrize(
    ("now", "timestamp"),
    [
        ("2026-11-01T12:00:00-05:00", "2026-11-01T00:30:00-04:00"),
        ("2026-03-08T12:00:00-04:00", "2026-03-08T00:30:00-05:00"),
    ],
)
def test_project_rows_use_midnight_dst_offset(
    monkeypatch: pytest.MonkeyPatch, now: str, timestamp: str
) -> None:
    from datetime import UTC, datetime, timedelta, timezone

    from state import menubar_state

    # Simulate the host's local offsets across the two US DST transitions.
    # No OS timezone change or optional IANA timezone database is needed.
    offsets = {
        (3, 8, 0): -5,
        (3, 8, 12): -4,
        (3, 9, 0): -4,
        (11, 1, 0): -4,
        (11, 1, 12): -5,
        (11, 2, 0): -5,
    }

    class LocalDateTime(datetime):
        def astimezone(self, tz: Any = None) -> LocalDateTime:
            if self.tzinfo is None or tz is None:
                zone = timezone(timedelta(hours=offsets[(self.month, self.day, self.hour)]))
                if self.tzinfo is None:
                    return self.replace(tzinfo=zone).astimezone(tz)
                return super().astimezone(zone)
            return super().astimezone(tz)

    monkeypatch.setattr(menubar_state, "datetime", LocalDateTime)
    entry = UsageEntry(
        timestamp=datetime.fromisoformat(timestamp).astimezone(UTC),
        session_id="session",
        message_id="message",
        request_id="request",
        model="test",
        input_tokens=100,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        cost_usd=1.0,
        project="today",
    )
    rows = menubar_state.project_rows_for_windows([entry], now=LocalDateTime.fromisoformat(now))
    assert rows[0] == [("today", 100, 1.0)]


@pytest.mark.parametrize("has_backup", [True, False])
def test_codex_unsetup_retains_config_and_backup_when_edit_rejected(
    setup_paths: SetupHookPaths, has_backup: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    content = (
        'developer_instructions = """\n[tui]\nstatus_line = ["example"]\n"""\n'
        + "[tui]\n"
        + setup_hook._status_line_toml(setup_hook.CODEX_STATUS_LINE)
        + "\n"
    )
    setup_hook.CODEX_CONFIG.parent.mkdir()
    setup_hook.CODEX_CONFIG.write_text(content, encoding="utf-8")
    backup = '{"status_line": ["model"]}'
    if has_backup:
        setup_hook.CODEX_BACKUP.write_text(backup, encoding="utf-8")
    setup_hook._unsetup_codex()
    assert setup_hook.CODEX_CONFIG.read_text(encoding="utf-8") == content
    if has_backup:
        assert setup_hook.CODEX_BACKUP.read_text(encoding="utf-8") == backup
    output = capsys.readouterr().out
    assert _t("setup_codex_config_unmodifiable") in output
    assert _t("setup_codex_restored") not in output
    assert _t("setup_codex_removed") not in output


def test_self_heal_respects_legacy_disabled_statusline(
    monkeypatch: pytest.MonkeyPatch, setup_paths: SetupHookPaths
) -> None:
    settings = {setup_hook.LEGACY_DISABLED_SL_CONTAINER: {setup_hook.PREV_SL_KEY: None}}
    setup_paths.settings.write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setattr(session_hooks, "setup", lambda: pytest.fail("must not enable status line"))
    session_hooks.self_heal()
    result = setup_hook._load_settings()
    assert (
        result[setup_hook.LEGACY_DISABLED_SL_CONTAINER]
        == settings[setup_hook.LEGACY_DISABLED_SL_CONTAINER]
    )
    assert "statusLine" not in result
