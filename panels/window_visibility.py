# SPDX-License-Identifier: AGPL-3.0-only
"""Native show, hide, minimize, and restore behavior for Windows panels.

Minimizing means "to the tray", not "to the taskbar". A tray app that also
leaves a taskbar button behind is reachable from two places at once, takes
taskbar room it does not need, and offers two ways back that behave
differently. ``window.hide()`` removes it from the taskbar and Alt-Tab, and the
tray icon becomes the single way back.
"""

from __future__ import annotations

from typing import Any


def toggle_panel(controller: Any) -> None:
    if controller._minimized:
        # Minimizing hides rather than minimizing natively, so returning is a
        # show. restore() would do nothing to a hidden window, which would
        # leave the tray icon looking unresponsive.
        controller.visible = True
        controller._minimized = False
        controller._place_window()
        controller.window.show()
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
    """Send the panel to the tray.

    The position is saved first so the next show returns it to where the user
    left it. ``_positioned_this_show`` is deliberately left alone: dismissing a
    panel resets it, minimizing should not.
    """
    if controller.window is None:
        return
    controller._save_window_position()
    controller.visible = False
    controller._minimized = True
    controller.window.hide()


def on_native_minimize(controller: Any) -> None:
    """Follow an OS-driven minimize into the tray as well.

    The panel is frameless, so its own button is the usual route -- but Show
    Desktop, Win+D and a taskbar right-click can still minimize it natively.
    Letting those land on the taskbar while the button lands in the tray would
    make one action behave two ways depending on how it was invoked.
    """
    controller._minimized = True
    if controller.window is None:
        return
    controller.visible = False
    controller._save_window_position()
    controller.window.hide()
