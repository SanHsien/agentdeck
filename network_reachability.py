# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Bounded reachability check before a CLI can fall back to browser sign-in."""

from __future__ import annotations

import socket
import threading
import urllib.request
from concurrent.futures import Future


def google_auth_reachable(timeout: float = 3.0) -> bool:
    """Allow HTTPS proxies, otherwise bound both DNS lookup and TCP connection."""
    proxies = urllib.request.getproxies()
    if proxies.get("https") or proxies.get("all"):
        return True
    result: Future[bool] = Future()

    def probe() -> None:
        try:
            with socket.create_connection(("oauth2.googleapis.com", 443), timeout=timeout):
                result.set_result(True)
        except OSError:
            result.set_result(False)
        except BaseException as exc:
            result.set_exception(exc)

    threading.Thread(target=probe, daemon=True).start()
    try:
        return result.result(timeout=timeout)
    except TimeoutError:
        return False
