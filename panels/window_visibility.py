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

import contextlib
from typing import Any


def _reveal(window: Any) -> None:
    """Put the window back on screen, whatever state it was left in.

    Both calls are needed, in this order. The title bar's minimize button sets
    the window iconic *before* our handler hides it, so it ends up hidden and
    minimized at once: ``show()`` alone brings back only a taskbar button the
    user has to click a second time, and ``restore()`` alone does nothing to a
    window that is still hidden, which makes the tray icon look dead.
    """
    window.show()
    with contextlib.suppress(Exception):
        # Cosmetic on a window that was never iconic; never worth failing a
        # show over.
        window.restore()


def toggle_panel(controller: Any) -> None:
    if controller._minimized:
        controller.visible = True
        controller._minimized = False
        controller._place_window()
        _reveal(controller.window)
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
    _reveal(controller.window)
    controller.inject_state(force=True)
    controller.refresh()


def on_closing(controller: Any) -> bool:
    """Send the window to the tray instead of quitting.

    Returning False cancels the close: pywebview's ``closing`` event is
    cancellable, and the winforms backend sets ``args.Cancel`` when any handler
    says so. Quitting from the title bar would be a trap -- the tray icon is how
    this app is meant to be dismissed and recalled, and a stray click on X
    should not end the session that is tracking quota.

    ``quit()`` reaches this same handler, because it shuts the window down with
    ``destroy()`` and that fires ``closing`` too. Cancelling *that* close
    stranded the app: the tray icon was already stopped, so the process kept
    running with no window and no icon -- nothing to click, nothing to quit --
    while the single-instance lock told the next launch it was already running.
    ``stopping`` is set only by ``quit()``, so it is the one signal that
    separates "the user pressed X" from "the app is going away".
    """
    if controller.stopping.is_set():
        return True
    on_native_minimize(controller)
    return False


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
