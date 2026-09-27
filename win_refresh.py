# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

import threading
from collections.abc import Callable


class TrailingRefreshRunner:
    """Run one refresh now and coalesce busy-time requests into one trailing run."""

    def __init__(self, callback: Callable[[], None], stopping: threading.Event) -> None:
        self._callback = callback
        self._stopping = stopping
        self._lock = threading.Lock()
        self._in_flight = False
        self._queued = False
        self._thread: threading.Thread | None = None

    @property
    def in_flight(self) -> bool:
        with self._lock:
            return self._in_flight

    def request(self) -> None:
        if self._stopping.is_set():
            return
        with self._lock:
            if self._stopping.is_set():
                return
            if self._in_flight:
                self._queued = True
                return
            self._in_flight = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while True:
            rerun = False
            try:
                self._callback()
            finally:
                with self._lock:
                    rerun = self._queued and not self._stopping.is_set()
                    self._queued = False
                    if not rerun:
                        self._in_flight = False
                        self._thread = None
            if not rerun:
                return

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            self._queued = False
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
