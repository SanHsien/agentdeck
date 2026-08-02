# SPDX-License-Identifier: AGPL-3.0-only
"""Native show, hide, minimize, and restore behavior for Windows panels."""

from __future__ import annotations

from typing import Any


def toggle_panel(controller: Any) -> None:
    if controller._minimized:
        controller.window.restore()
        controller._minimized = False
        controller.inject_state(force=True)
        controller.refresh()
        return
    if controller.visible:
        controller._save_window_position()
        controller.visible = False
        controller._minimized = False
        controller._positioned_this_show = False
        controller.window.hide()
        return
    controller.visible = True
    controller._minimized = False
    controller._place_window()
    controller.window.show()
    controller.inject_state(force=True)
    controller.refresh()


def minimize_panel(controller: Any) -> None:
    if controller.window is not None:
        controller._save_window_position()
        controller.window.minimize()
        controller._minimized = True
