# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import session_hooks
import setup_hook
import statusline_settings as settings
import win_login_item
import wintray
from tests.helpers import SetupHookPaths


@pytest.mark.parametrize("state", ["external", "legacy-tt"])
def test_custom_statusline_does_not_block_session_repairs(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(session_hooks, "_load_settings", lambda: {})
    monkeypatch.setattr(session_hooks, "_detect_current_state", lambda *args: state)
    monkeypatch.setattr(session_hooks, "_self_heal_resume", lambda: calls.append("resume"))
    monkeypatch.setattr(session_hooks, "_self_heal_terse_mode", lambda: calls.append("terse"))
    session_hooks.self_heal()
    assert calls == ["resume", "terse"]


@pytest.mark.parametrize("operation", ["enabled", "disable", "enable"])
def test_custom_statusline_switch(
    monkeypatch: pytest.MonkeyPatch, patch_setup_hook_paths: Any, operation: str
) -> None:
    paths: SetupHookPaths = patch_setup_hook_paths()
    original = {"statusLine": {"type": "command", "command": "echo custom"}}
    paths.settings.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(settings, "_claude_settings_path", lambda: paths.settings)
    monkeypatch.setattr(settings, "_sync_agy_statusline", lambda enabled: None)
    if operation == "enabled":
        assert not settings._statusline_enabled()
    elif operation == "disable":
        assert settings._disable_statusline_settings() == 0
        assert json.loads(paths.settings.read_text(encoding="utf-8")) == original
    else:
        assert settings._enable_statusline_settings() == 0
        assert setup_hook._detect_current_state() in {"us-direct", "us-forwarder"}
        assert setup_hook.unsetup() == 0
        assert json.loads(paths.settings.read_text(encoding="utf-8")) == original


def test_failed_statusline_return_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    refreshed: list[bool] = []
    controller = SimpleNamespace(
        language="en",
        refresh=lambda: refreshed.append(True),
        _report_action_result=lambda *args, **kwargs: messages.append((args, kwargs)),
    )
    monkeypatch.setattr(settings, "_toggle_statusline_settings", lambda: ("install", 1))
    wintray._WindowsTrayController._toggle_statusline(controller)  # type: ignore[arg-type]
    assert len(messages) == 1
    assert messages[0][1]["failed"] is True
    assert refreshed == [True]


@pytest.mark.parametrize("enabled", [True, False])
def test_failed_login_toggle_is_reported(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    messages: list[str] = []

    def denied() -> None:
        raise PermissionError("registration denied")

    monkeypatch.setattr(win_login_item, "is_enabled", lambda: enabled)
    monkeypatch.setattr(win_login_item, "enable", denied)
    monkeypatch.setattr(win_login_item, "disable", denied)
    controller = SimpleNamespace(language="en", _message_box=messages.append)
    wintray._WindowsTrayController.toggle_login(controller)  # type: ignore[arg-type]
    assert len(messages) == 1
    assert "registration denied" in messages[0]
