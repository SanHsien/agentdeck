# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Serialise window geometry changes onto the WinForms UI thread.

Every JS bridge message arrives on a fresh worker thread — pywebview's
``js_bridge_call`` does ``Thread(target=_call).start()`` — and pywebview's
``resize()``/``move()`` read WinForms ``Location``/``Width``/``Handle`` and call
``SetWindowPos`` with nothing marshalling them. pystray runs its menu callbacks
on its own thread as well. The panel reports its content height on the first
path continuously, so without this the window's geometry was read and written
from arbitrary threads all day.

WinForms raises on a cross-thread access only when a debugger is attached, so
in the wild it is simply undefined behaviour: no exception, no log line, just
the occasional wrong size or missed move that nobody can reproduce.
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
from collections import deque
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class WindowMutationQueue:
    """A queue of geometry changes drained on the native UI thread."""

    def __init__(
        self,
        *,
        window: Callable[[], Any | None],
        stopping: threading.Event,
    ) -> None:
        self._window = window
        self._stopping = stopping
        self._queue: deque[Callable[[], None]] = deque()
        self._lock = threading.Lock()
        self._scheduled = False

    def dispatch(self, mutation: Callable[[], None]) -> None:
        """Queue ``mutation`` and make sure something will run it."""
        if self._stopping.is_set():
            return
        with self._lock:
            self._queue.append(mutation)
            if self._scheduled:
                return
            self._scheduled = True

        if self.schedule_drain():
            return
        # Nothing could run it — the Form does not exist yet. Clear the flag so
        # the next caller tries again rather than queueing behind a drain that
        # will never happen. The mutation itself stays queued.
        with self._lock:
            self._scheduled = False

    def schedule_drain(self) -> bool:
        """Post a drain to the UI thread. False means nobody could run it."""
        window = self._window()
        if window is None:
            return False
        if not hasattr(window, "native"):
            # Test doubles have no native control; run inline.
            self.drain()
            return True
        native = window.native
        if native is None:
            # The tray can be clicked before pywebview has created its Form.
            # Leave the work queued; on_loaded() schedules another drain.
            return False
        try:
            if native.InvokeRequired:
                # "System" only resolves after pythonnet's clr module has been
                # imported. pywebview does that on the way to building the Form
                # we just read, but relying on that ordering makes the failure
                # mode a silently swallowed ImportError and a mutation that
                # never runs. Ask for clr explicitly instead.
                importlib.import_module("clr")
                system = importlib.import_module("System")
                native.BeginInvoke(system.Action(self.drain))
            else:
                self.drain()
        except Exception:
            if os.environ.get("AGENTDECK_DEBUG") == "1":
                logger.warning("failed to dispatch window mutation", exc_info=True)
            return False
        return True

    def drain(self) -> None:
        """Run every queued mutation. Only ever called on the UI thread."""
        while True:
            with self._lock:
                if self._stopping.is_set():
                    # Quit tore the window down; a geometry change landing now
                    # would touch a destroyed handle or resurrect the window.
                    self._queue.clear()
                    self._scheduled = False
                    return
                if not self._queue:
                    self._scheduled = False
                    return
                mutation = self._queue.popleft()
            try:
                mutation()
            except Exception:
                if os.environ.get("AGENTDECK_DEBUG") == "1":
                    logger.warning("window mutation failed", exc_info=True)
