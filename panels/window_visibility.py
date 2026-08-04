# SPDX-License-Identifier: AGPL-3.0-only
"""Native show, hide, minimize, and restore behavior for Windows panels.

Minimizing means "to the tray", not "to the taskbar". A tray app that also
leaves a taskbar button behind is reachable from two places at once, takes
taskbar room it does not need, and offers two ways back that behave
differently. ``window.hide()`` removes it from the taskbar and Alt-Tab, and the
tray icon becomes the single way back.

The window wears a normal title bar, so its own minimize button, its close
button and Alt+F4 all arrive here and all end the same way: hidden, still
running, one tray icon to bring it back. Closing never quits the app -- the
tray menu's Quit is the only exit, which is what makes a single X press safe.
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


def on_native_minimize(controller: Any) -> None:
    """Send the panel to the tray instead of to the taskbar.

    Every route into this function is an OS-driven one -- the title bar's
    minimize and close buttons, Alt+F4, Show Desktop, Win+D, a taskbar
    right-click. They are handled identically on purpose: one action should not
    behave two ways depending on how it was invoked.

    The position is saved first so the next show returns the panel to where the
    user left it. ``_positioned_this_show`` is deliberately left alone:
    dismissing a panel resets it, minimizing should not.
    """
    controller._minimized = True
    if controller.window is None:
        return
    controller.visible = False
    controller._save_window_position()
    controller.window.hide()
