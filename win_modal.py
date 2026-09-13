# SPDX-License-Identifier: AGPL-3.0-only
"""One native dialog at a time, in front, owned by the panel.

Two things made the About box impossible to dismiss. It was raised with no
owner from a background thread, so Windows never gave it focus and it opened
*behind* whatever the user was looking at -- the click that asked for it looked
like it did nothing. So they clicked again, and every click added another
dialog: three clicks, three dialogs, each needing its own dismissal. That is
what "it will not close" actually was.

The lock is process-wide rather than per-controller on purpose: there is one
tray, one panel, and one user, so a second modal is never the right answer no
matter which object asked for it.
"""

from __future__ import annotations

import threading
from typing import Any

MB_ICON_WARNING = 0x30
MB_ICON_INFO = 0x40
MB_YESNOCANCEL = 0x03
# Without these a MessageBoxW raised from a background thread opens behind the
# window the user is looking at and never takes focus.
MB_SETFOREGROUND = 0x00010000
MB_TOPMOST = 0x00040000

NO_ANSWER = 0

_MODAL_LOCK = threading.Lock()


def owner_handle(window: Any, *, visible: bool) -> int:
    """The panel's window handle while it is on screen, else no owner.

    An owner the user cannot see gives the dialog nothing to sit above and
    nothing to disable, so a hidden panel deliberately owns nothing.
    """
    if not visible or window is None:
        return 0
    native = getattr(window, "native", None)
    handle = getattr(native, "Handle", None)
    if handle is None:
        return 0
    # WinForms hands back a .NET IntPtr. int() refuses it outright, so the
    # obvious conversion raises and -- caught -- turns ownership into a silent
    # no-op: an unowned dialog again, with nothing to show for it.
    to_int64 = getattr(handle, "ToInt64", None)
    if callable(to_int64):
        return int(to_int64())
    try:
        return int(str(handle))
    except (TypeError, ValueError):
        return 0


def show(text: str, *, title: str = "agentdeck", style: int = MB_ICON_INFO, owner: int = 0) -> int:
    """Show one modal and return its result, or ``NO_ANSWER`` if one is already up.

    Owning it to the panel puts it above an always-on-top window and greys the
    panel while it waits, so the dialog is both visible and obviously the thing
    to deal with.
    """
    import ctypes

    if not _MODAL_LOCK.acquire(blocking=False):
        return NO_ANSWER
    try:
        library_name = "windll"
        windll: Any = getattr(ctypes, library_name)
        return int(
            windll.user32.MessageBoxW(
                owner, text, title, style | MB_SETFOREGROUND | MB_TOPMOST
            )
        )
    finally:
        _MODAL_LOCK.release()
