# SPDX-License-Identifier: AGPL-3.0-only
"""The tray icon's right-click menu.

Split out of ``wintray`` to keep that file under its size ceiling. Everything
here is presentation of the controller's existing actions -- no state of its
own -- so the menu can grow without pushing the file that drives the tray over
the limit again.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import win_login_item
from i18n import _t
from panels.registry import available_panels
from state.menubar_prefs import (
    PANEL_FLAVORS,
    _hide_agy_enabled,
    _hide_claude_enabled,
    _hide_codex_enabled,
    _hide_grok_enabled,
    _panel_flavor,
    _quota_notifications_enabled,
    _window_keeper_enabled,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle at runtime, fine for typing
    from wintray import _WindowsTrayController


def _menu(controller: _WindowsTrayController) -> Any:
    # Imported lazily: wintray imports this module, so a module-level import
    # here would be a cycle.
    import pystray

    from wintray import _session_resume_enabled, _terse_mode_enabled

    panel_items = tuple(
        pystray.MenuItem(
            _t(controller.language, key),
            # pystray rejects actions whose co_argcount isn't 0/1/2, so the
            # panel_id binding must be keyword-only.
            lambda _icon, _item, *, panel_id=panel_id: controller.switch_panel(panel_id),
            checked=lambda _item, panel_id=panel_id: controller.active_panel_id == panel_id,
            radio=True,
        )
        for panel_id, key, _filename in available_panels()
    )
    flavor_items = tuple(
        pystray.MenuItem(
            _t(controller.language, f"flavor_{flavor}"),
            lambda _icon, _item, *, flavor=flavor: controller.set_panel_flavor(flavor),
            checked=lambda _item, flavor=flavor: _panel_flavor() == flavor,
            radio=True,
        )
        for flavor in PANEL_FLAVORS
    )
    return pystray.Menu(
        pystray.MenuItem("Open", controller.show_panel, default=True, visible=False),
        pystray.MenuItem(_t(controller.language, "panel_changelog"), controller.open_changelog),
        pystray.MenuItem(
            _t(controller.language, "discussion_window_title"), controller.open_discussion
        ),
        pystray.MenuItem(_t(controller.language, "about"), controller.show_about),
        pystray.MenuItem(
            _t(controller.language, "reset_panel_position"), controller.reset_panel_position
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_t(controller.language, "switch_panel"), pystray.Menu(*panel_items)),
        pystray.MenuItem(
            _t(controller.language, "panel_flavor_menu"),
            pystray.Menu(*flavor_items),
        ),
        pystray.MenuItem(
            _t(controller.language, "panel_talent_market"),
            controller.open_talent_market,
        ),
        pystray.MenuItem(
            _t(controller.language, "hide_sections_menu"),
            pystray.Menu(
                pystray.MenuItem(
                    _t(controller.language, "claude_name"),
                    lambda _icon, _item: controller.toggle_hide_section("hide_claude_section"),
                    checked=lambda _item: _hide_claude_enabled(),
                ),
                pystray.MenuItem(
                    _t(controller.language, "codex_name"),
                    lambda _icon, _item: controller.toggle_hide_section("hide_codex_section"),
                    checked=lambda _item: _hide_codex_enabled(),
                ),
                pystray.MenuItem(
                    _t(controller.language, "agy_name"),
                    lambda _icon, _item: controller.toggle_hide_section("hide_agy_section"),
                    checked=lambda _item: _hide_agy_enabled(),
                ),
                pystray.MenuItem(
                    _t(controller.language, "grok_name"),
                    lambda _icon, _item: controller.toggle_hide_section("hide_grok_section"),
                    checked=lambda _item: _hide_grok_enabled(),
                ),
            ),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_t(controller.language, "refresh_now"), lambda i, x: controller.refresh()),
        pystray.MenuItem(
            _t(controller.language, "launch_at_login"),
            controller.toggle_login,
            checked=lambda _item: win_login_item.is_enabled(),
        ),
        pystray.MenuItem(
            _t(controller.language, "quota_notifications_menu"),
            controller.toggle_quota_notifications,
            checked=lambda _item: _quota_notifications_enabled(),
        ),
        pystray.MenuItem(
            _t(controller.language, "window_keeper_menu"),
            controller.toggle_window_keeper,
            checked=lambda _item: _window_keeper_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            _t(controller.language, "project_butler"),
            controller.toggle_session_resume,
            checked=lambda _item: _session_resume_enabled(),
        ),
        pystray.MenuItem(
            _t(controller.language, "terse_mode_menu"),
            controller.toggle_terse_mode,
            checked=lambda _item: _terse_mode_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_t(controller.language, "check_update"), controller.check_update),
        pystray.MenuItem(_t(controller.language, "quit"), controller.quit),
    )


def _panel_menu_data(controller: _WindowsTrayController) -> list[dict[str, object]]:
    """Return fresh, localized data for the HTML panel menu."""
    from wintray import (
        _hide_agy_enabled,
        _hide_claude_enabled,
        _hide_codex_enabled,
        _hide_grok_enabled,
        _quota_notifications_enabled,
        _session_resume_enabled,
        _terse_mode_enabled,
        _window_keeper_enabled,
    )

    def item(key: str, action: str, **extra: object) -> dict[str, object]:
        return {
            "i18nKey": key,
            "label": _t(controller.language, key),
            "action": action,
            **extra,
        }

    panels = [
        item(
            key,
            "switch_panel",
            panelId=panel_id,
            checked=controller.active_panel_id == panel_id,
        )
        for panel_id, key, _filename in available_panels()
    ]
    hidden_sections = [
        item(
            "claude_name",
            "toggle_hide_section",
            preferenceKey="hide_claude_section",
            checked=_hide_claude_enabled(),
        ),
        item(
            "codex_name",
            "toggle_hide_section",
            preferenceKey="hide_codex_section",
            checked=_hide_codex_enabled(),
        ),
        item(
            "agy_name",
            "toggle_hide_section",
            preferenceKey="hide_agy_section",
            checked=_hide_agy_enabled(),
        ),
        item(
            "grok_name",
            "toggle_hide_section",
            preferenceKey="hide_grok_section",
            checked=_hide_grok_enabled(),
        ),
    ]
    return [
        item("panel_changelog", "open_changelog"),
        item("discussion_window_title", "open_discussion"),
        item("about", "show_about"),
        {"type": "separator"},
        item("switch_panel", "", children=panels),
        item("hide_sections_menu", "", children=hidden_sections),
        {"type": "separator"},
        item("launch_at_login", "toggle_login", checked=win_login_item.is_enabled()),
        item(
            "quota_notifications_menu",
            "toggle_quota_notifications",
            checked=_quota_notifications_enabled(),
        ),
        item(
            "window_keeper_menu",
            "toggle_window_keeper",
            checked=_window_keeper_enabled(),
        ),
        {"type": "separator"},
        item("project_butler", "toggle_session_resume", checked=_session_resume_enabled()),
        item("terse_mode_menu", "toggle_terse_mode", checked=_terse_mode_enabled()),
        {"type": "separator"},
        item("refresh_now", "refresh"),
    ]
