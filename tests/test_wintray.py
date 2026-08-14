# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

import prefs
import win_login_item
import win_modal
import wintray
from i18n import _t
from providers import codex_loader
from state import menubar_prefs, menubar_state
from usage_notifications import NotificationEvent


class _Key:
    def __enter__(self) -> _Key:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeWinreg:
    HKEY_CURRENT_USER = object()

    def __init__(self, value: int = 1, error: Exception | None = None) -> None:
        self.value = value
        self.error = error

    def OpenKey(self, *args: object) -> _Key:  # noqa: N802 - winreg contract
        if self.error is not None:
            raise self.error
        return _Key()

    def QueryValueEx(self, key: object, name: str) -> tuple[int, int]:  # noqa: N802
        return (self.value, 4)


def _state() -> menubar_state.PopoverState:
    row = menubar_state.QuotaRowState(
        title="Session",
        percent=25.0,
        percent_text="25% used",
        reset_text="Resets in 1h",
        color=menubar_state.CLAUDE_COLOR,
    )
    weekly = menubar_state.QuotaRowState(
        title="Weekly",
        percent=60.0,
        percent_text="60% used",
        reset_text="Resets in 1d",
        color=menubar_state.CLAUDE_COLOR,
    )
    return menubar_state.PopoverState(
        language="en",
        claude_session=row,
        claude_weekly=weekly,
        codex_session=row,
        codex_weekly=weekly,
        agy_session=row,
        agy_weekly=weekly,
        agy_group_name="",
        projects=[],
        projects_7d=[],
        projects_30d=[],
        projects_all=[],
        rate_text="",
        status_text="",
        today_text="",
        statusline={},
    )


@pytest.mark.parametrize(
    ("used", "text", "color"),
    [
        (None, "--", (110, 118, 129, 255)),
        (0.0, "100", (244, 145, 100, 255)),
        (60.0, "40", (255, 196, 57, 255)),
        (95.0, "5", (255, 69, 58, 255)),
        (150.0, "0", (255, 69, 58, 255)),
    ],
)
def test_tray_icon_style(used: float | None, text: str, color: tuple[int, ...]) -> None:
    assert wintray.tray_icon_style(used) == (text, color)


def test_draw_tray_icon_and_tooltip(monkeypatch: pytest.MonkeyPatch) -> None:
    image = SimpleNamespace(size=(64, 64))
    draw = SimpleNamespace(
        rounded_rectangle=lambda *args, **kwargs: None,
        textbbox=lambda *args, **kwargs: (0, 0, 24, 12),
        text=lambda *args, **kwargs: None,
    )
    fake_pil = SimpleNamespace(
        Image=SimpleNamespace(new=lambda *args, **kwargs: image),
        ImageDraw=SimpleNamespace(Draw=lambda value: draw),
        ImageFont=SimpleNamespace(load_default=lambda **kwargs: object()),
    )
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    icon_image = wintray.draw_tray_icon(25.0)

    assert icon_image.size == (64, 64)
    assert wintray.build_tooltip(_state()).splitlines() == [
        "Claude Session: 75%",
        "Claude Weekly: 40%",
        "Codex Session: 75% · Weekly: 40%",
    ]


def test_the_talent_market_is_reachable_but_is_not_a_theme() -> None:
    """It shows role cards and installs them, and displays no quota at all.
    Listing it among the themes made the theme list lie about what it offers and
    let a user land in it by picking what looked like a skin."""
    themes = [panel[0] for panel in wintray.available_panels()]
    renderable = [panel[0] for panel in wintray.renderable_panels()]

    assert "classic" in themes
    assert "talent_market" not in themes
    assert "talent_market" in renderable
    assert len(themes) == len(wintray.WINDOWS_PANELS)


def test_every_panel_has_a_registered_height() -> None:
    # A panel without a height entry raises KeyError in panel_height() the moment
    # the user switches to it.
    for panel_id, _key, _filename in wintray.available_panels():
        assert panel_id in wintray.PANEL_HEIGHTS, panel_id


def test_system_background_color_dark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wintray, "_winreg", lambda: FakeWinreg(value=0))

    assert wintray._system_background_color() == "#080d12"


def test_system_background_color_light(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wintray, "_winreg", lambda: FakeWinreg(value=1))

    assert wintray._system_background_color() == "#eef2f7"


def test_system_background_color_falls_back_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        wintray,
        "_winreg",
        lambda: FakeWinreg(error=OSError("registry unavailable")),
    )

    assert wintray._system_background_color() == "#eef2f7"


def test_panel_html_installs_webkit_shim_without_changing_asset() -> None:
    html = wintray.panel_html("classic.html")

    assert "window.webkit.messageHandlers.usage" in html
    assert "window.pywebview.api.postMessage(message)" in html
    assert "pywebview-drag-region" in html
    assert "usage-window-drag-handle" in html
    assert "post('open_menu')" in html
    assert "usage-panel-menu-backdrop" in html
    assert "usage-panel-menu-accordion" in html
    assert "max-height: 80vh" in html
    assert "overflow-y: auto" in html
    assert "event.stopImmediatePropagation()" in html
    assert "[data-card=\"claude\"]" in html
    assert "usage-card-window-dragging" in html
    assert "card.classList.add('pywebview-drag-region'" in html
    assert "button, a, input, select, textarea, label, summary" in html
    assert "cursor: grab" in html
    assert "cursor: grabbing" in html
    assert "usageApplyStateWithDynamicHeight" in html


def test_panel_html_injects_no_minimize_button() -> None:
    """The title bar supplies minimize now, so an in-page button would be a
    second control for the same thing, sitting under a real one."""
    html = wintray.panel_html("classic.html")

    assert "minimizeButton" not in html
    assert "post('minimize')" not in html


def test_every_panel_uses_the_feature_menu_label_for_its_switch_button() -> None:
    for _panel_id, _key, filename in wintray.available_panels():
        html = wintray.panel_html(filename)

        assert 'data-action="switch"' in html, filename
        assert 'data-action="switch" data-i18n="switch_panel"' not in html, filename
        assert 'data-i18n="panel_menu"' in html, filename


def test_content_height_message_resizes_visible_panel_with_work_area_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    # A window without a `native` attribute drains the mutation queue inline,
    # which is the only way a test can observe work that is now marshalled onto
    # the WinForms UI thread.
    controller.window = SimpleNamespace()
    calls: list[str] = []
    monkeypatch.setattr(controller, "_working_area", lambda: (0, 0, 1000, 800))
    monkeypatch.setattr(
        controller, "_place_window_on_ui_thread", lambda **_kwargs: calls.append("place")
    )

    controller.handle_panel_message(
        json.dumps({"action": "content_height", "height": 510.4})
    )
    controller.handle_panel_message(
        json.dumps({"action": "content_height", "height": 5000})
    )

    assert controller.panel_height() == 776
    assert calls == ["place", "place"]


def test_the_panel_height_message_never_touches_the_window_off_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This is the path that actually mattered. pywebview runs every JS bridge
    message on a fresh worker thread (js_bridge_call does
    ``Thread(target=_call).start()``) and its resize()/move() read WinForms
    Location/Width/Handle and call SetWindowPos with nothing marshalling them.
    The panel reports its height on that path continuously. WinForms raises on
    a cross-thread access only when a debugger is attached, so the rest of the
    time it is undefined behaviour — the shape of a bug nobody can reproduce.

    Asserting the dispatcher in isolation is not enough: it stays green when
    the height path stops calling it, which is exactly the regression to catch.
    """
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    posted: list[Callable[[], None]] = []

    class Native:
        InvokeRequired = True

        @staticmethod
        def BeginInvoke(action: Callable[[], None]) -> None:
            posted.append(action)  # captured, deliberately not run

    controller.window = SimpleNamespace(native=Native())
    monkeypatch.setattr(controller, "_working_area", lambda: (0, 0, 1000, 800))
    monkeypatch.setattr(controller, "_place_window_on_ui_thread", lambda **_kwargs: None)
    fake_system = SimpleNamespace(Action=lambda fn: fn)
    monkeypatch.setattr(
        "win_ui_thread.importlib.import_module",
        lambda name: fake_system if name == "System" else SimpleNamespace(),
    )

    controller.handle_panel_message(json.dumps({"action": "content_height", "height": 510.4}))

    assert controller._content_height is None, (
        "the height was applied on the calling thread instead of being posted to the UI thread"
    )
    assert len(posted) == 1, "nothing was posted to the UI thread"

    posted[0]()

    assert controller._content_height == 510


def test_a_tray_menu_click_never_moves_the_window_off_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pystray runs menu callbacks on its own thread, so "reset position" calls
    move()/resize() from there just as the panel's height message did.
    """
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    posted: list[Callable[[], None]] = []

    class Native:
        InvokeRequired = True

        @staticmethod
        def BeginInvoke(action: Callable[[], None]) -> None:
            posted.append(action)

    controller.window = SimpleNamespace(native=Native())
    placed: list[bool] = []
    monkeypatch.setattr(
        controller,
        "_place_window_on_ui_thread",
        lambda *, force_default=False: placed.append(force_default),
    )
    monkeypatch.setattr(wintray, "_load_preferences", dict)
    monkeypatch.setattr(wintray, "_save_preferences", lambda _prefs: None)
    fake_system = SimpleNamespace(Action=lambda fn: fn)
    monkeypatch.setattr(
        "win_ui_thread.importlib.import_module",
        lambda name: fake_system if name == "System" else SimpleNamespace(),
    )

    controller.reset_panel_position()

    assert placed == [], "the window was moved on the pystray callback thread"
    assert len(posted) == 1

    posted[0]()

    assert placed == [True]


def test_a_mutation_survives_a_window_that_does_not_exist_yet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tray can be clicked before pywebview has built its Form. Dropping
    the mutation there would lose the panel's reported height, so it stays
    queued and on_loaded drains it.
    """
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = None
    ran: list[str] = []

    controller._dispatch_window_mutation(lambda: ran.append("placed"))
    assert ran == []

    controller.window = SimpleNamespace()
    controller.on_loaded()

    assert ran == ["placed"]


def test_mutations_are_dropped_once_shutdown_starts() -> None:
    """Quit tears the window down. A geometry change landing after that would
    resurrect it or touch a destroyed handle."""
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = SimpleNamespace()
    ran: list[str] = []
    controller.stopping.set()

    controller._dispatch_window_mutation(lambda: ran.append("placed"))

    assert ran == []


def test_invalid_content_height_keeps_registered_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    fallback = wintray.PANEL_HEIGHTS[controller.active_panel_id]
    monkeypatch.setattr(controller, "_working_area", lambda: (0, 0, 1000, 800))

    controller.handle_panel_message(
        json.dumps({"action": "content_height", "height": "510"})
    )

    assert controller.panel_height() == fallback


def test_load_preferences_tolerates_non_utf8(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    preferences_path = tmp_path / "agentdeck-preferences.json"
    preferences_path.write_bytes(b"\xff\xfe\x00bad")
    monkeypatch.setattr(prefs, "PREFERENCES_FILE", preferences_path)

    assert prefs._load_preferences() == {}


def test_panel_position_is_clamped_and_persisted_on_hide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    preferences_path = tmp_path / "agentdeck-preferences.json"
    preferences_path.write_text(
        json.dumps({"agentdeck.windowPosition": {"x": 5000, "y": -100}}), encoding="utf-8"
    )
    monkeypatch.setattr(prefs, "PREFERENCES_FILE", preferences_path)
    moves: list[tuple[int, int]] = []
    window = SimpleNamespace(
        x=0,
        y=0,
        resize=lambda *args: None,
        move=lambda x, y: moves.append((x, y)),
        hide=lambda: None,
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = window
    controller.visible = True
    monkeypatch.setattr(controller, "_working_area", lambda: (0, 0, 1000, 1080))
    monkeypatch.setattr(controller, "_work_area_for_point", lambda point: (0, 0, 1000, 1080))

    controller._place_window()

    assert moves == [(608, 12)]
    window.x, window.y = 123, 234
    controller.show_panel()
    assert prefs._load_preferences()["agentdeck.windowPosition"] == {"x": 123, "y": 234}


def test_reset_panel_position_clears_preference_and_repositions_visible_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    preferences_path = tmp_path / "agentdeck-preferences.json"
    preferences_path.write_text(
        json.dumps({"agentdeck.windowPosition": {"x": 123, "y": 234}}), encoding="utf-8"
    )
    monkeypatch.setattr(prefs, "PREFERENCES_FILE", preferences_path)
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    calls: list[bool] = []
    monkeypatch.setattr(
        controller, "_place_window", lambda *, force_default=False: calls.append(force_default)
    )

    controller.reset_panel_position()

    assert prefs._load_preferences() == {}
    assert calls == [True]


def test_switch_panel_keeps_dragged_position_before_new_height_is_measured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: switch_panel() used to reset _content_height to None, so
    # on_loaded() clamped the just-dragged position against PANEL_HEIGHTS'
    # near-fullscreen placeholder for the new panel before its real height
    # was measured, snapping a dragged window back up to the top of the
    # screen on every switch.
    moves: list[tuple[int, int]] = []
    window = SimpleNamespace(
        x=0,
        y=0,
        resize=lambda *args: None,
        move=lambda x, y: moves.append((x, y)),
        show=lambda: None,
        hide=lambda: None,
        load_html=lambda html: None,
        evaluate_js=lambda code: None,
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = window
    controller.visible = True
    controller.active_panel_id = "classic"
    monkeypatch.setattr(controller, "_working_area", lambda: (0, 0, 1920, 1080))
    monkeypatch.setattr(controller, "_work_area_for_point", lambda point: (0, 0, 1920, 1080))

    controller._place_window()
    controller.handle_panel_message(json.dumps({"action": "content_height", "height": 700}))
    window.x, window.y = 300, 200  # simulates the user dragging the window here

    controller.switch_panel("catppuccin")
    controller.on_loaded()

    assert moves[-1] == (300, 200)

    controller.handle_panel_message(json.dumps({"action": "content_height", "height": 650}))

    assert moves[-1] == (300, 200)


def test_switch_panel_keeps_dragged_position_on_secondary_monitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: _working_area() only ever reports the *primary* monitor's
    # work area (that's what SPI_GETWORKAREA returns). Clamping a dragged
    # window against it snapped the window back onto the primary monitor on
    # every panel switch, even when the user deliberately dragged it onto a
    # secondary display.
    primary = (0, 0, 1920, 1080)
    secondary = (1920, 0, 4480, 1400)  # a monitor to the right of the primary

    def work_area_for_point(point: tuple[int, int] | None) -> tuple[int, int, int, int]:
        if point is not None and point[0] >= 1920:
            return secondary
        return primary

    moves: list[tuple[int, int]] = []
    window = SimpleNamespace(
        x=0,
        y=0,
        resize=lambda *args: None,
        move=lambda x, y: moves.append((x, y)),
        show=lambda: None,
        hide=lambda: None,
        load_html=lambda html: None,
        evaluate_js=lambda code: None,
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = window
    controller.visible = True
    controller.active_panel_id = "classic"
    monkeypatch.setattr(controller, "_working_area", lambda: primary)
    monkeypatch.setattr(controller, "_work_area_for_point", work_area_for_point)

    controller._place_window()
    controller.handle_panel_message(json.dumps({"action": "content_height", "height": 700}))
    window.x, window.y = 2200, 300  # simulates dragging the window onto the secondary monitor

    controller.switch_panel("catppuccin")
    controller.on_loaded()

    assert moves[-1] == (2200, 300)


def test_js_api_forwards_panel_message() -> None:
    received: list[object] = []
    controller = SimpleNamespace(handle_panel_message=received.append)

    wintray._JSApi(controller).postMessage("refresh")  # type: ignore[arg-type]

    assert received == ["refresh"]


def test_js_api_returns_panel_menu_data() -> None:
    menu = [{"label": "Menu"}]
    controller = SimpleNamespace(handle_panel_message=lambda _message: menu)

    result = wintray._JSApi(controller).postMessage("open_menu")  # type: ignore[arg-type]

    assert result == menu


def test_switch_panel_message_returns_menu_instead_of_cycling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    switched_to: list[str] = []
    monkeypatch.setattr(controller, "switch_panel", switched_to.append)
    monkeypatch.setattr(win_login_item, "is_enabled", lambda: True)

    menu = controller.handle_panel_message("switch")

    assert isinstance(menu, list)
    assert next(item for item in menu if item.get("i18nKey") == "switch_panel")
    assert switched_to == []


def test_selected_panel_switch_waits_for_bridge_promise_and_debounces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled: list[FakeTimer] = []

    class FakeTimer:
        def __init__(self, delay: float, callback: object) -> None:
            self.delay = delay
            self.callback = callback
            scheduled.append(self)

        def start(self) -> None:
            return None

        def fire(self) -> None:
            assert callable(self.callback)
            self.callback()

    controller = wintray._WindowsTrayController(mock=True, interval=60)
    switched_to: list[str] = []
    monkeypatch.setattr(controller, "switch_panel", switched_to.append)
    monkeypatch.setattr(threading, "Timer", FakeTimer)

    controller.handle_panel_message(
        json.dumps({"action": "switch_panel", "panel_id": "catppuccin"})
    )
    controller.handle_panel_message(json.dumps({"action": "switch_panel", "panel_id": "origami"}))

    assert len(scheduled) == 1
    assert scheduled[0].delay == 0.05
    scheduled[0].fire()

    assert switched_to == ["catppuccin"]


def test_panel_menu_data_is_localized_and_reads_current_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.language = "en"
    controller.active_panel_id = "catppuccin"
    monkeypatch.setattr(wintray, "_hide_claude_enabled", lambda: True)
    monkeypatch.setattr(wintray, "_hide_codex_enabled", lambda: False)
    monkeypatch.setattr(wintray, "_hide_agy_enabled", lambda: True)
    monkeypatch.setattr(win_login_item, "is_enabled", lambda: True)
    monkeypatch.setattr(wintray, "_quota_notifications_enabled", lambda: False)
    monkeypatch.setattr(wintray, "_window_keeper_enabled", lambda: True)
    monkeypatch.setattr(wintray, "_session_resume_enabled", lambda: True)
    monkeypatch.setattr(wintray, "_terse_mode_enabled", lambda: False)

    menu = controller._panel_menu_data()

    assert menu[0] == {
        "i18nKey": "panel_changelog",
        "label": "Changelog",
        "action": "open_changelog",
    }
    assert [entry.get("i18nKey", entry.get("type")) for entry in menu] == [
        "panel_changelog",
        "discussion_window_title",
        "about",
        "separator",
        "switch_panel",
        "hide_sections_menu",
        "separator",
        "launch_at_login",
        "quota_notifications_menu",
        "window_keeper_menu",
        "separator",
        "project_butler",
        "terse_mode_menu",
        "separator",
        "refresh_now",
    ]
    panels = cast(list[dict[str, object]], menu[4]["children"])
    hidden_sections = cast(list[dict[str, object]], menu[5]["children"])
    assert panels[1]["panelId"] == "catppuccin"
    assert panels[1]["checked"] is True
    assert [item["checked"] for item in hidden_sections] == [True, False, True]
    assert menu[7]["checked"] is True
    assert menu[8]["checked"] is False
    assert menu[9]["checked"] is True
    assert menu[11]["checked"] is True
    assert menu[12]["checked"] is False


@pytest.mark.parametrize(
    ("payload", "method", "expected"),
    [
        ({"action": "open_changelog"}, "open_changelog", ()),
        ({"action": "open_discussion"}, "open_discussion", ()),
        ({"action": "show_about"}, "show_about", ()),
        ({"action": "reset_panel_position"}, "reset_panel_position", ()),
        (
            {"action": "switch_panel", "panel_id": "catppuccin"},
            "_schedule_panel_switch",
            ("catppuccin",),
        ),
        (
            {"action": "toggle_hide_section", "preference_key": "hide_codex_section"},
            "toggle_hide_section",
            ("hide_codex_section",),
        ),
        ({"action": "refresh"}, "refresh", ()),
        ({"action": "toggle_login"}, "toggle_login", ()),
        ({"action": "toggle_quota_notifications"}, "toggle_quota_notifications", ()),
        ({"action": "toggle_window_keeper"}, "toggle_window_keeper", ()),
        ({"action": "toggle_session_resume"}, "toggle_session_resume", ()),
        ({"action": "toggle_terse_mode"}, "toggle_terse_mode", ()),
        ({"action": "check_update"}, "check_update", ()),
        ({"action": "quit"}, "quit", ()),
    ],
)
def test_panel_menu_actions_dispatch_to_controller_methods(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, str],
    method: str,
    expected: tuple[str, ...],
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(controller, method, lambda *args: calls.append(args))

    controller.handle_panel_message(json.dumps(payload))

    assert calls == [expected]


def test_about_shows_the_current_version_and_project_homepage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.language = "zh-TW"
    shown: list[str] = []

    def capture_message(text: str, **_kwargs: object) -> int:
        shown.append(text)
        return 0

    monkeypatch.setattr(wintray, "_current_version", lambda: "9.8.7")
    monkeypatch.setattr(controller, "_message_box", capture_message)

    controller.show_about()

    assert shown == [
        "agentdeck\n版本：9.8.7\n程式官網：https://github.com/SanHsien/agentdeck"
    ]


def test_closing_the_window_goes_to_the_tray_and_cancels_the_close() -> None:
    """The X must not quit the app. pywebview cancels the close when a
    ``closing`` handler returns False, so returning anything truthy here --
    including None from an early return -- would tear the window down and leave
    a tray icon pointing at nothing."""
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    controller.window = SimpleNamespace(hide=lambda: calls.append("hide"))
    controller.visible = True

    result = controller.on_closing()

    assert result is False, "a non-False result lets pywebview destroy the window"
    assert calls == ["hide"]
    assert controller._minimized is True
    assert controller.visible is False


def test_an_os_driven_minimize_also_lands_in_the_tray() -> None:
    """The title bar's minimize, Show Desktop and Win+D all minimize natively.

    If those landed on the taskbar while the close button landed in the tray,
    one window would behave two ways depending on which control was used.
    """
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    controller.window = SimpleNamespace(hide=lambda: calls.append("hide"))
    controller.visible = True

    controller.on_minimized()

    assert calls == ["hide"]
    assert controller._minimized is True
    assert controller.visible is False


def test_native_window_events_keep_minimized_state_in_sync() -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    controller.on_minimized()
    assert controller._minimized is True

    controller.on_restored()
    assert controller._minimized is False


def test_tray_click_restores_a_minimized_panel(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    controller.window = SimpleNamespace(
        restore=lambda: calls.append("restore"),
        show=lambda: calls.append("show"),
        hide=lambda: calls.append("hide"),
    )
    controller.visible = True
    controller._minimized = True
    monkeypatch.setattr(controller, "_place_window", lambda **_: calls.append("place"))
    monkeypatch.setattr(
        controller, "inject_state", lambda *, force=False: calls.append(f"inject:{force}")
    )
    monkeypatch.setattr(controller, "refresh", lambda: calls.append("refresh"))

    controller.show_panel()

    assert controller.visible is True
    assert controller._minimized is False
    # show() *then* restore(), and in that order. The title bar's minimize sets
    # the window iconic before our handler hides it, so it is hidden and
    # minimized at once: show() alone brought back only a taskbar button the
    # user had to click a second time, and restore() alone does nothing to a
    # window that is still hidden -- the tray icon would look unresponsive.
    assert calls == ["place", "show", "restore", "inject:True", "refresh"]


@pytest.mark.parametrize("panel_id", ["catppuccin", "stained_glass", "origami"])
def test_card_order_persists_into_the_next_loaded_panel(
    monkeypatch: pytest.MonkeyPatch,
    panel_id: str,
) -> None:
    preferences: dict[str, object] = {}
    injected: list[str] = []
    loaded: list[str] = []
    window = SimpleNamespace(
        evaluate_js=injected.append,
        load_html=loaded.append,
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = window
    controller.visible = True
    order = ["codex", "claude", "agy"]

    monkeypatch.setattr(wintray, "_load_preferences", lambda: preferences.copy())
    monkeypatch.setattr(menubar_prefs, "_load_preferences", lambda: preferences.copy())
    monkeypatch.setattr(
        wintray,
        "_save_preferences",
        lambda updated: preferences.update(updated),
    )
    monkeypatch.setattr(controller, "_place_window", lambda: None)

    controller.handle_panel_message(
        json.dumps({"action": "set_card_order", "order": order})
    )
    controller.switch_panel(panel_id)
    controller.on_loaded()

    assert preferences["quota_card_order"] == order
    assert controller.latest_state.card_order == tuple(order)
    assert len(loaded) == 1
    payload = injected[-1].removeprefix("window.usageApplyState(").removesuffix(")")
    assert json.loads(payload)["cardOrder"] == order


def test_run_app_wires_pystray_and_pywebview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class FakeMenuItem:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args

    class FakeMenu:
        def __init__(self, *items: object) -> None:
            self.items = items

    class FakeIcon:
        def __init__(self, *args: object) -> None:
            events.append(("icon", args[0]))

        def run_detached(self) -> None:
            events.append("run_detached")

    class Event:
        def __init__(self, name: str) -> None:
            self.name = name

        def __iadd__(self, callback: object) -> Event:
            events.append(f"{self.name}_handler")
            return self

    window = SimpleNamespace(
        events=SimpleNamespace(
            loaded=Event("loaded"),
            closing=Event("closing"),
            minimized=Event("minimized"),
            restored=Event("restored"),
        )
    )

    def create_window(*args: object, **kwargs: object) -> object:
        events.append(
            ("window", args[0], kwargs["hidden"], kwargs["background_color"])
        )
        return window

    FakeMenu.SEPARATOR = object()  # type: ignore[attr-defined]
    fake_pystray = SimpleNamespace(Icon=FakeIcon, Menu=FakeMenu, MenuItem=FakeMenuItem)
    fake_webview = SimpleNamespace(
        create_window=create_window,
        start=lambda **kwargs: events.append(("start", kwargs["gui"])),
    )
    monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(wintray, "draw_tray_icon", lambda value: object())
    monkeypatch.setattr(wintray, "_system_background_color", lambda: "#eef2f7")
    monkeypatch.setattr(wintray._WindowsTrayController, "attach", lambda self, icon, view: None)
    # A tray may genuinely be running on the machine executing the tests.
    monkeypatch.setattr(wintray, "_acquire_single_instance_lock", lambda: True)

    wintray.run_app(mock=True, interval=60)

    assert events == [
        ("window", "agentdeck", True, "#eef2f7"),
        "loaded_handler",
        "closing_handler",
        "minimized_handler",
        "restored_handler",
        ("icon", "agentdeck"),
        "run_detached",
        ("start", "edgechromium"),
    ]


def test_on_loaded_does_not_place_hidden_window() -> None:
    # Regression: pywebview's resize()/move() call SetWindowPos with
    # SWP_SHOWWINDOW, so placing the window at document load dragged the bare
    # unrendered panel onto the screen at every launch.
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    controller.window = SimpleNamespace(
        resize=lambda *args: calls.append("resize"),
        move=lambda *args: calls.append("move"),
        show=lambda: calls.append("show"),
        evaluate_js=lambda code: calls.append("evaluate_js"),
    )

    controller.on_loaded()

    assert calls == []


def test_show_panel_places_window_before_showing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    monkeypatch.setattr(controller, "_place_window", lambda: calls.append("place"))
    monkeypatch.setattr(
        controller, "inject_state", lambda *, force=False: calls.append(f"inject:{force}")
    )
    monkeypatch.setattr(controller, "refresh", lambda: calls.append("refresh"))
    controller.window = SimpleNamespace(
        show=lambda: calls.append("show"), hide=lambda: calls.append("hide")
    )

    controller.show_panel()

    assert controller.visible is True
    assert calls == ["place", "show", "inject:True", "refresh"]


def test_tray_update_skips_unchanged_values(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.latest_state = _state()
    icon = SimpleNamespace(icon=None, title=None)
    controller.icon = icon
    images: list[float | None] = []

    def fake_draw_tray_icon(percent: float | None) -> object:
        images.append(percent)
        return object()

    monkeypatch.setattr(wintray, "draw_tray_icon", fake_draw_tray_icon)

    controller._update_tray()
    first_image = icon.icon
    controller._update_tray()
    controller.latest_state.claude_session.percent = 26.0
    controller._update_tray()

    assert images == [25.0, 26.0]
    assert icon.icon is not first_image


def test_inject_state_skips_duplicate_but_forces_after_panel_reopens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    injected: list[str] = []
    controller.window = SimpleNamespace(
        evaluate_js=injected.append,
        show=lambda: None,
        hide=lambda: None,
    )
    monkeypatch.setattr(controller, "_place_window", lambda: None)
    monkeypatch.setattr(controller, "refresh", lambda: None)

    controller.inject_state()
    controller.inject_state()
    controller.show_panel()
    controller.on_loaded()
    controller.show_panel()
    controller.show_panel()

    assert len(injected) == 4


def test_build_state_reuses_history_until_fingerprint_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    fingerprints = iter([(("history", 1, 10.0),), (("history", 2, 11.0),)])
    monkeypatch.setattr(
        menubar_state,
        "history_source_scan",
        lambda: menubar_state.HistorySourceScan(next(fingerprints), (), ()),
    )
    calls: list[int] = []
    original = controller._load_entries

    def counting_load_entries(scan: menubar_state.HistorySourceScan) -> wintray._RefreshData:
        calls.append(1)
        return original(scan)

    monkeypatch.setattr(controller, "_load_entries", counting_load_entries)
    now = 100.0
    monkeypatch.setattr("wintray.time.monotonic", lambda: now)

    controller._build_state()
    controller._build_state()
    now += wintray.HISTORY_SCAN_CACHE_SECONDS
    controller._build_state()

    assert calls == [1, 1]


def test_codex_rate_limits_reuse_the_history_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex_rows used to be called before the scan existed, so it enumerated
    every jsonl under ~/.codex itself and the scan then walked the same tree
    again — a full recursive directory walk twice per refresh. Measured cold on
    a 54-session machine: 237 ms versus 142 ms. Nothing else would notice the
    regression; a duplicated scan is invisible except as sluggishness.
    """
    controller = wintray._WindowsTrayController(mock=False, interval=60)
    candidates = ((Path("C:/codex/sessions/session.jsonl"), 123.0),)
    scan = menubar_state.HistorySourceScan((("history", 1, 10.0),), (), (), candidates)
    seen: list[tuple[tuple[Path, float], ...] | None] = []

    def recent_jsonl_files(
        *, jsonl_candidates: tuple[tuple[Path, float], ...] | None = None
    ) -> list[Path]:
        seen.append(jsonl_candidates)
        return []

    monkeypatch.setattr(controller, "_history_source_scan", lambda: scan)
    monkeypatch.setattr(controller, "_load_entries", lambda _scan: wintray._RefreshData([], None))
    monkeypatch.setattr(codex_loader, "_load_sqlite_rate_limits", lambda: None)
    monkeypatch.setattr(codex_loader, "_recent_jsonl_files", recent_jsonl_files)

    controller._build_state()

    assert seen == [candidates], "codex_rows walked ~/.codex itself instead of reusing the scan"


def test_history_source_scan_is_cached_between_tray_ticks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    scan = menubar_state.HistorySourceScan((("history", 1, 10.0),), (), ())
    calls: list[int] = []
    now = 100.0
    monkeypatch.setattr("wintray.time.monotonic", lambda: now)

    def scan_history() -> menubar_state.HistorySourceScan:
        calls.append(1)
        return scan

    monkeypatch.setattr(
        menubar_state,
        "history_source_scan",
        scan_history,
    )

    assert controller._history_source_scan() is scan
    assert controller._history_source_scan() is scan
    now += wintray.HISTORY_SCAN_CACHE_SECONDS
    assert controller._history_source_scan() is scan

    assert calls == [1, 1]


def test_hide_section_updates_preferences_and_visible_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferences: dict[str, object] = {}
    saved: list[dict[str, object]] = []
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    injected: list[str] = []
    monkeypatch.setattr(wintray, "_load_preferences", lambda: preferences)
    monkeypatch.setattr(wintray, "_save_preferences", lambda value: saved.append(dict(value)))
    monkeypatch.setattr(wintray, "_hide_claude_enabled", lambda: True)
    monkeypatch.setattr(wintray, "_hide_codex_enabled", lambda: False)
    monkeypatch.setattr(wintray, "_hide_agy_enabled", lambda: False)
    monkeypatch.setattr(controller, "inject_state", lambda: injected.append("state"))

    controller.toggle_hide_section("hide_claude_section")

    assert preferences == {"hide_claude_section": True}
    assert saved == [preferences]
    assert controller.latest_state.hide_claude is True
    assert injected == ["state"]


def test_quota_notifications_use_pystray_notify_and_existing_i18n(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = wintray._WindowsTrayController(mock=False, interval=60)
    controller.language = "en"
    notices: list[tuple[str, str]] = []
    controller.icon = SimpleNamespace(
        notify=lambda message, title: notices.append((message, title))
    )
    monkeypatch.setattr(wintray, "_quota_notifications_enabled", lambda: True)
    state = _state()

    controller._send_quota_notification(
        NotificationEvent("warn", "claude_session", 90.0), state
    )

    assert notices == [("Claude Session is 25% used. Time to wrap up?", "🐾 Almost out")]


def test_session_hook_toggles_run_in_background_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def record(name: str) -> int:
        calls.append(name)
        return 0

    hooks = SimpleNamespace(
        is_resume_enabled=lambda: False,
        enable_session_resume=lambda: record("enable_resume"),
        disable_session_resume=lambda: record("disable_resume"),
        is_terse_mode_enabled=lambda: True,
        enable_terse_mode=lambda: record("enable_terse"),
        disable_terse_mode=lambda: record("disable_terse"),
    )
    monkeypatch.setitem(sys.modules, "session_hooks", hooks)
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    controller._toggle_session_resume_in_background()
    controller._toggle_terse_mode_in_background()

    assert calls == ["enable_resume", "disable_terse"]


def test_run_app_bails_out_when_another_instance_holds_the_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: a second tray instance used to fight the first over the
    # WebView2 user-data directory and linger as a bare white window.
    notices: list[str] = []
    monkeypatch.setattr(wintray, "_acquire_single_instance_lock", lambda: False)
    monkeypatch.setattr(wintray, "_show_already_running_notice", lambda: notices.append("shown"))
    fake_webview = SimpleNamespace(
        create_window=lambda *args, **kwargs: pytest.fail("window must not be created"),
        start=lambda **kwargs: pytest.fail("webview must not start"),
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    wintray.run_app(mock=True, interval=60)

    assert notices == ["shown"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows named mutex")
def test_single_instance_lock_blocks_second_acquire_until_released(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use a test-specific mutex name so a real tray running on this machine
    # cannot interfere.
    monkeypatch.setattr(
        wintray, "_SINGLE_INSTANCE_MUTEX", "usage-tray-single-instance-pytest"
    )
    assert wintray._acquire_single_instance_lock() is True
    try:
        assert wintray._acquire_single_instance_lock() is False
    finally:
        wintray._release_single_instance_lock()
    assert wintray._acquire_single_instance_lock() is True
    wintray._release_single_instance_lock()


def test_menu_actions_pass_real_pystray_signature_validation() -> None:
    # Regression: pystray validates every action's co_argcount when a MenuItem
    # is constructed, and the panel-switch lambda used to carry a third
    # defaulted positional parameter, raising ValueError before the tray icon
    # ever appeared. Build the menu against the real pystray to catch that.
    pytest.importorskip("pystray", reason="pystray is a Windows-only extra")
    controller = SimpleNamespace(
        language="en",
        active_panel_id="classic",
        switch_panel=lambda panel_id: None,
        open_talent_market=lambda _icon=None, _item=None: None,
        show_panel=lambda: None,
        reset_panel_position=lambda: None,
        refresh=lambda: None,
        toggle_login=lambda: None,
        open_changelog=lambda: None,
        open_discussion=lambda: None,
        show_about=lambda: None,
        toggle_hide_section=lambda key: None,
        toggle_quota_notifications=lambda: None,
        toggle_window_keeper=lambda: None,
        toggle_session_resume=lambda: None,
        toggle_terse_mode=lambda: None,
        check_update=lambda: None,
        quit=lambda: None,
    )

    menu = wintray._menu(controller)  # type: ignore[arg-type]

    assert menu is not None


@pytest.mark.parametrize(
    ("rect", "scale", "expected"),
    [
        ((0, 0, 3840, 2052), 2.25, (0, 0, 1707, 912)),  # 4K at 225%
        ((0, 0, 2560, 1372), 1.5, (0, 0, 1707, 915)),  # 1440p at 150%
        ((0, 0, 1920, 1032), 1.0, (0, 0, 1920, 1032)),  # unscaled: untouched
        ((0, 0, 1920, 1032), 0.0, (0, 0, 1920, 1032)),  # bad scale: untouched
        ((1920, 0, 4480, 1400), 2.0, (960, 0, 2240, 700)),  # non-zero origin
    ],
)
def test_to_logical_rect_converts_physical_win32_rects(
    rect: tuple[int, int, int, int],
    scale: float,
    expected: tuple[int, int, int, int],
) -> None:
    assert wintray._to_logical_rect(rect, scale) == expected


def test_place_window_keeps_panel_on_screen_at_225_percent_scaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: pywebview calls SetProcessDPIAware(), so Win32 work areas come
    # back in physical pixels while pywebview's move()/resize() take logical
    # ones and multiply by the monitor scale themselves. Feeding the physical
    # rect straight through scaled the coordinate twice: on a 3840x2160 display
    # at 225% the panel was sent to x=3408 logical -> 7668 physical, which is off
    # the right edge of a 3840px screen, so the window never appeared at all.
    scale = 2.25
    physical_work_area = (0, 0, 3840, 2052)
    logical_work_area = wintray._to_logical_rect(physical_work_area, scale)

    moves: list[tuple[int, int]] = []
    resizes: list[tuple[int, int]] = []
    window = SimpleNamespace(
        x=0,
        y=0,
        resize=lambda w, h: resizes.append((w, h)),
        move=lambda x, y: moves.append((x, y)),
        show=lambda: None,
        hide=lambda: None,
        load_html=lambda html: None,
        evaluate_js=lambda code: None,
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = window
    monkeypatch.setattr(controller, "_working_area", lambda: logical_work_area)
    monkeypatch.setattr(controller, "_work_area_for_point", lambda point: logical_work_area)

    controller._place_window(force_default=True)

    assert moves, "the panel was never placed"
    logical_x, logical_y = moves[-1]
    physical_x, physical_y = round(logical_x * scale), round(logical_y * scale)
    assert 0 <= physical_x <= physical_work_area[2] - 1, physical_x
    assert 0 <= physical_y <= physical_work_area[3] - 1, physical_y

    # The panel must also stay a panel: a physical height fed to resize() would
    # be multiplied by 2.25 and tower far past the top of the screen.
    assert resizes
    _, logical_height = resizes[-1]
    assert logical_height * scale <= physical_work_area[3]


def test_monitor_dpi_scale_is_neutral_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wintray.os.name", "posix")

    assert wintray._monitor_dpi_scale(None) == 1.0


@pytest.mark.skipif(sys.platform != "win32", reason="DPI scale lookup is Windows-only")
def test_monitor_dpi_scale_reports_a_usable_ratio_on_windows() -> None:
    scale = wintray._monitor_dpi_scale(None)

    assert isinstance(scale, float)
    assert 0.5 <= scale <= 8.0, scale


def test_open_discussion_creates_the_controller_once(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[object] = []

    class _Controller:
        def __init__(self) -> None:
            created.append(self)
            self.shown = 0

        def show(self) -> None:
            self.shown += 1

    from council import discussion_window_win

    monkeypatch.setattr(
        discussion_window_win, "WindowsDiscussionWindowController", _Controller
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    controller.open_discussion()
    controller.open_discussion()

    # The bridge is expensive, so the controller is built on first use and reused.
    assert len(created) == 1
    assert controller.discussion is not None
    assert controller.discussion.shown == 2


def test_open_discussion_failure_does_not_take_the_tray_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from council import discussion_window_win

    def _explode() -> None:
        raise RuntimeError("no webview")

    monkeypatch.setattr(
        discussion_window_win, "WindowsDiscussionWindowController", _explode
    )
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    controller.open_discussion()  # must not raise: the tray is the only way back

    assert controller.discussion is None


def test_quit_shuts_the_discussion_bridge_down(monkeypatch: pytest.MonkeyPatch) -> None:
    shutdowns: list[bool] = []
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.discussion = SimpleNamespace(shutdown=lambda: shutdowns.append(True))

    controller.quit()

    # A live DiscussionBridge owns worker threads; leaking them blocks exit.
    assert shutdowns == [True]
    assert controller.discussion is None


def test_tray_menu_offers_the_ai_council() -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    menu = wintray._menu(controller)
    labels = [getattr(item, "text", None) for item in menu]

    assert _t(controller.language, "discussion_window_title") in labels


@pytest.mark.parametrize(
    ("edge", "expected"),
    [
        ("bottom", (1315, 12)),
        ("top", (1315, 12)),
        ("left", (12, 12)),  # tray on the left: hug the left edge, still at the top
        ("right", (1315, 12)),
    ],
)
def test_default_position_follows_the_taskbar_edge(
    edge: str, expected: tuple[int, int]
) -> None:
    """The side follows the tray; the top is fixed.

    The panel is a tall column -- taller than the work area on a scaled display
    -- so anchoring it to the bottom pushed its lower edge onto the taskbar and
    moved the title bar people grab depending on how tall the theme happened to
    be. From the top the grab handle is always in the same corner, and anything
    that does not fit scrolls.
    """
    work_area = (0, 0, 1707, 912)

    assert (
        wintray._WindowsTrayController._default_window_position(work_area, 560, edge) == expected
    )


def test_default_position_assumes_bottom_when_the_edge_is_unknown() -> None:
    work_area = (0, 0, 1707, 912)

    assert wintray._WindowsTrayController._default_window_position(
        work_area, 560, "nonsense"
    ) == wintray._WindowsTrayController._default_window_position(work_area, 560, "bottom")


def test_taskbar_edge_is_bottom_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("wintray.os.name", "posix")

    assert wintray._taskbar_edge() == "bottom"


@pytest.mark.skipif(sys.platform != "win32", reason="SHAppBarMessage is Windows-only")
def test_taskbar_edge_reports_a_real_edge_on_windows() -> None:
    assert wintray._taskbar_edge() in {"top", "bottom", "left", "right"}


def test_explaining_a_feature_never_blocks_on_a_modal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: _explain_feature used MessageBoxW, which blocks until someone
    # clicks it. The toggles that call it run on daemon threads, so enabling a
    # feature waited forever for a click — and it hung the whole test suite.
    # Unsolicited information belongs in a tray balloon, not a modal.
    notes: list[tuple[str, str]] = []
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.icon = SimpleNamespace(notify=lambda body, title: notes.append((body, title)))
    monkeypatch.setattr(
        controller,
        "_message_box",
        lambda *args, **kwargs: pytest.fail("_explain_feature must not open a modal"),
    )

    controller._explain_feature("terse_mode_tooltip")

    assert notes, "the explanation was dropped instead of shown"
    assert notes[0][0] == _t(controller.language, "terse_mode_tooltip")


def test_explaining_a_feature_is_a_no_op_before_the_tray_exists() -> None:
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.icon = None

    controller._explain_feature("terse_mode_tooltip")  # must not raise


def test_chrome_height_is_measured_from_the_live_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resize() sets the outer size, so a framed window handed the content
    height it needs comes up one title bar short and clips its own last rows.
    The delta is physical pixels and the resize argument is logical ones."""
    monkeypatch.setattr(wintray, "_monitor_dpi_scale", lambda *a: 2.25)
    window = SimpleNamespace(
        native=SimpleNamespace(Height=1998, ClientSize=SimpleNamespace(Height=1919))
    )

    assert wintray._window_chrome_height(window) == 35  # 79 physical / 2.25


def test_chrome_height_is_zero_when_the_form_is_not_reachable() -> None:
    """Before the window is realised there is nothing to measure. Guessing a
    caption height here would misplace every panel on the first show."""
    assert wintray._window_chrome_height(None) == 0
    assert wintray._window_chrome_height(SimpleNamespace()) == 0
    assert wintray._window_chrome_height(SimpleNamespace(native=SimpleNamespace())) == 0


def test_quit_is_not_cancelled_by_the_close_to_tray_handler() -> None:
    """quit() shuts the window down with destroy(), which fires `closing` just
    like the X does. Cancelling that close stranded the app: the tray icon was
    already stopped, so the process kept running with no window and no icon
    while the single-instance lock told the next launch it was already
    running."""
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    calls: list[str] = []
    controller.window = SimpleNamespace(
        hide=lambda: calls.append("hide"),
        destroy=lambda: calls.append("destroy"),
    )
    controller.icon = SimpleNamespace(stop=lambda: calls.append("icon.stop"))

    controller.quit()

    assert calls == ["icon.stop", "destroy"]
    assert controller.on_closing() is True, "quit's own close must not be cancelled"
    assert "hide" not in calls, "quitting must not fall back to hiding the window"


def test_update_prompt_shows_the_version_and_address_not_the_release_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A MessageBoxW has no scrollbar, so pasting a full changelog in turned
    the prompt into a wall of Markdown the user had to read past to reach the
    buttons -- and the notes are one click away on the page this dialog offers
    to open."""
    shown: list[str] = []
    controller = wintray._WindowsTrayController(mock=True, interval=60)

    def capture(text: str, **_: object) -> int:
        shown.append(text)
        return 2  # IDCANCEL -- "later", the choice that changes no state

    monkeypatch.setattr(controller, "_message_box", capture)
    release = SimpleNamespace(
        version="9.9.9",
        html_url="https://example.test/releases/tag/v9.9.9",
        # Present on the real object; the prompt must simply not reach for it.
        body="## Changed\n- a very long changelog that must stay out of the box",
    )

    controller._show_update_prompt(release)

    assert shown, "the prompt was never shown"
    text = shown[0]
    assert "9.9.9" in text
    assert "https://example.test/releases/tag/v9.9.9" in text
    assert _t(controller.language, "update_btn_download") in text
    assert "changelog" not in text, "release notes are back in the prompt"


def test_opening_the_talent_market_rebuilds_state_before_showing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The roster is only read while this panel is active, and a switch renders
    from the state built for the *previous* panel. Without a refresh the market
    showed "component is not installed" on every open until the next poll --
    indistinguishable, to a user, from a broken feature."""
    calls: list[str] = []
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.visible = True
    monkeypatch.setattr(
        controller, "switch_panel", lambda panel_id, **kw: calls.append(f"switch:{panel_id}:{kw}")
    )
    monkeypatch.setattr(controller, "refresh", lambda: calls.append("refresh"))

    controller.open_talent_market()

    assert calls == ["switch:talent_market:{'remember': False}", "refresh"]


def test_the_talent_market_is_never_restored_as_the_startup_panel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It is somewhere you visit to install a role. Opening the app into it
    would hide the quota the app exists to show."""
    saved: list[str] = []
    monkeypatch.setattr(wintray, "_save_active_panel_id", lambda panel_id: saved.append(panel_id))
    controller = wintray._WindowsTrayController(mock=True, interval=60)
    controller.window = SimpleNamespace(load_html=lambda html: None)

    controller.switch_panel("talent_market", remember=False)
    controller.switch_panel("origami")

    assert saved == ["origami"]


def test_only_one_modal_can_be_open_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every click used to add another dialog. They open behind the window and
    never take focus, so the first click looks like it did nothing and the user
    clicks again -- three clicks, three dialogs, each needing its own dismissal.
    That is what "the About box will not close" actually was."""
    import ctypes

    shown: list[str] = []

    def blocking_box(hwnd: int, text: str, title: str, style: int) -> int:
        shown.append(text)
        # Stands in for MessageBoxW blocking until dismissed: ask for a second
        # one from inside the first, exactly as a second click would.
        win_modal.show("second")
        return 1

    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(user32=SimpleNamespace(MessageBoxW=blocking_box))
    )

    win_modal.show("first")

    assert shown == ["first"], "a modal opened while another was already up"


def test_a_modal_is_owned_by_the_panel_so_it_sits_above_it() -> None:
    """The panel is always-on-top. An unowned dialog can be covered by it, and
    an owned one is placed above it and greys it out while it waits."""
    window = SimpleNamespace(native=SimpleNamespace(Handle=SimpleNamespace(ToInt64=lambda: 4242)))

    assert win_modal.owner_handle(window, visible=True) == 4242


def test_the_owner_handle_survives_a_dotnet_intptr() -> None:
    """WinForms returns a .NET IntPtr, and int() refuses it outright. Letting
    that raise and catching it turned the whole fix into a silent no-op."""

    class IntPtrLike:
        def __int__(self) -> int:
            raise TypeError("int() argument must be a real number, not 'IntPtr'")

        def __str__(self) -> str:
            return "9182"

    window = SimpleNamespace(native=SimpleNamespace(Handle=IntPtrLike()))

    assert win_modal.owner_handle(window, visible=True) == 9182


def test_a_hidden_panel_owns_nothing() -> None:
    """An owner the user cannot see gives the dialog nothing to sit above and
    nothing to disable."""
    window = SimpleNamespace(native=SimpleNamespace(Handle=SimpleNamespace(ToInt64=lambda: 4242)))

    assert win_modal.owner_handle(window, visible=False) == 0
