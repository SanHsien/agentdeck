# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import win_tray_menu
import wintray
from i18n import _t
from state import menubar_prefs as prefs
from usage_notifications import QuotaNotifier


def test_set_thresholds_keeps_observations_and_waits_for_crossing() -> None:
    notifier = QuotaNotifier()
    channel = "claude_session"
    assert notifier.update({channel: (85.0, True)}) == []
    state = notifier._channels[channel]
    notifier.set_thresholds([95.0, 70.0, 90.0, 70.0])
    assert notifier.thresholds == [70.0, 90.0, 95.0]
    assert notifier._channels[channel] is state
    assert state.last_percent == 85.0
    assert notifier.update({channel: (85.0, True)}) == []
    assert notifier.update({channel: (86.0, True)}) == []
    events = notifier.update({channel: (90.0, True)})
    assert [event.threshold for event in events] == [90.0]
    notifier.set_thresholds([70.0, 90.0])
    assert state.warned_thresholds == {90.0}
    assert notifier.update({channel: (90.0, True)}) == []
    assert notifier.update({channel: (20.0, True)}) == []
    assert [event.threshold for event in notifier.update({channel: (70.0, True)})] == [70.0]


def test_set_thresholds_preserves_depleted_state() -> None:
    notifier = QuotaNotifier()
    notifier.update({"codex_weekly": (100.0, True)})
    notifier.set_thresholds([50.0, 90.0])
    assert notifier.update({"codex_weekly": (100.0, True)}) == []
    assert [event.kind for event in notifier.update({"codex_weekly": (0.0, True)})] == ["restored"]


@pytest.fixture
def saved_prefs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    data: dict[str, Any] = {}
    monkeypatch.setattr(prefs, "_load_preferences", lambda: data.copy())
    monkeypatch.setattr(prefs, "_save_preferences", lambda values: data.update(values))
    return data


def test_preset_toggle_updates_prefs_and_running_notifier(saved_prefs: dict[str, Any]) -> None:
    notifier = QuotaNotifier()
    notifier.update({"claude_session": (85.0, True)})
    assert prefs.toggle_quota_threshold(70, notifier)
    assert saved_prefs["quota_notification_thresholds"] == [70.0, 90.0]
    assert all(type(value) is float for value in saved_prefs["quota_notification_thresholds"])
    assert notifier.update({"claude_session": (86.0, True)}) == []
    assert prefs.toggle_quota_threshold(90, notifier)
    assert saved_prefs["quota_notification_thresholds"] == [70.0]
    assert notifier.thresholds == [70.0]


def test_last_threshold_cannot_be_unchecked(saved_prefs: dict[str, Any]) -> None:
    notifier = QuotaNotifier()
    assert not prefs.toggle_quota_threshold(90, notifier)
    assert saved_prefs == {}
    assert notifier.thresholds == [90.0]


def test_custom_thresholds_are_preserved(saved_prefs: dict[str, Any]) -> None:
    saved_prefs["quota_notification_thresholds"] = [92.5, 90.0, 42.0, 92.5]
    notifier = QuotaNotifier(prefs._quota_notification_thresholds())
    assert prefs.toggle_quota_threshold(90, notifier)
    assert saved_prefs["quota_notification_thresholds"] == [42.0, 92.5]
    assert prefs.toggle_quota_threshold(50, notifier)
    assert saved_prefs["quota_notification_thresholds"] == [42.0, 50.0, 92.5]


def test_disabled_notifications_ignore_threshold_changes(saved_prefs: dict[str, Any]) -> None:
    saved_prefs["quota_notifications"] = False
    notifier = QuotaNotifier()
    assert not prefs.toggle_quota_threshold(50, notifier)
    assert not prefs.toggle_quota_threshold(25, notifier)
    assert saved_prefs == {"quota_notifications": False}
    assert notifier.thresholds == [90.0]


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("language", ["zh-TW", "en"])
def test_windows_threshold_submenu(
    saved_prefs: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    language: str,
) -> None:
    pytest.importorskip("pystray")
    saved_prefs["quota_notifications"] = enabled
    monkeypatch.setattr(wintray, "_load_preferences", lambda: saved_prefs.copy())
    monkeypatch.setattr(wintray, "_save_preferences", lambda values: saved_prefs.update(values))
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.language = language
    updates: list[bool] = []
    controller.icon = SimpleNamespace(update_menu=lambda: updates.append(True))
    notifier = controller._quota_notifier
    menu = win_tray_menu._menu(controller)
    parent = next(
        item for item in menu.items if item.text == _t(language, "quota_notifications_menu")
    )
    assert parent.checked is enabled
    toggle, _, header, *items = parent.submenu.items
    assert toggle.text == _t(language, "quota_notifications_toggle")
    assert not header.enabled
    assert [item.text for item in items] == [
        _t(language, "quota_threshold_item", percent=percent) for percent in (50, 70, 80, 90, 95)
    ]
    assert [item.checked for item in items] == [False, False, False, True, False]
    assert all(item.enabled is enabled for item in items)
    if enabled:
        for item, percent in zip(items[:3], (50, 70, 80), strict=True):
            item(None)
            assert float(percent) in notifier.thresholds
        assert len(updates) == 3
    toggle(None)
    assert parent.checked is not enabled
    assert all(item.enabled is not enabled for item in items)
    assert updates
    assert controller._quota_notifier is notifier
