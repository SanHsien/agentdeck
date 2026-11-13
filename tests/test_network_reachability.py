# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import socket
import threading
import urllib.request
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

import network_reachability as network


@pytest.mark.parametrize("proxy", ["https", "all"])
def test_https_proxy_does_not_require_a_direct_connection(
    monkeypatch: pytest.MonkeyPatch, proxy: str,
) -> None:
    connect = Mock(side_effect=AssertionError("must not connect directly"))
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {proxy: "http://proxy:80"})
    monkeypatch.setattr(socket, "create_connection", connect)
    assert network.google_auth_reachable()
    connect.assert_not_called()


@pytest.mark.parametrize("reachable", [True, False])
def test_no_proxy_alone_still_probes_google(
    monkeypatch: pytest.MonkeyPatch, reachable: bool,
) -> None:
    connect = Mock(return_value=nullcontext()) if reachable else Mock(side_effect=OSError)
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {"no": "localhost"})
    monkeypatch.setattr(socket, "create_connection", connect)
    assert network.google_auth_reachable(timeout=1) is reachable
    connect.assert_called_once_with(("oauth2.googleapis.com", 443), timeout=1)


def test_dns_lookup_is_bounded_and_worker_can_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = threading.Event()
    finished = threading.Event()
    workers: list[threading.Thread] = []

    def blocked_connection(address: tuple[str, int], timeout: float) -> None:
        workers.append(threading.current_thread())
        try:
            release.wait(2)
            raise OSError("DNS unavailable")
        finally:
            finished.set()

    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    monkeypatch.setattr(socket, "create_connection", blocked_connection)
    try:
        assert not network.google_auth_reachable(timeout=0.05)
        assert not finished.is_set()
    finally:
        release.set()
        assert finished.wait(2)
        for worker in workers:
            worker.join(2)
            assert not worker.is_alive()
