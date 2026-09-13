# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

import threading

from win_refresh import TrailingRefreshRunner


def test_request_does_not_start_after_stop_begins() -> None:
    stopping = threading.Event()
    called = threading.Event()
    runner = TrailingRefreshRunner(called.set, stopping)

    runner._lock.acquire()
    request_thread = threading.Thread(target=runner.request)
    request_thread.start()
    stopping.set()
    runner._lock.release()
    request_thread.join(timeout=2)

    assert request_thread.is_alive() is False
    assert called.wait(timeout=0.05) is False
    assert runner.in_flight is False
