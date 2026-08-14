# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

import pytest

import update_checker


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, amt: int | None = None) -> bytes:
        # Real HTTPResponse.read takes an optional size. A double that refuses
        # it hides every capped read the production code performs.
        return self.body if amt is None else self.body[:amt]


def test_compare_versions_orders_numeric_versions() -> None:
    assert update_checker.compare_versions("0.10.1", "0.10.2") == -1
    assert update_checker.compare_versions("0.10.1", "0.10.1") == 0
    assert update_checker.compare_versions("0.9.10", "0.10.0") == -1
    assert update_checker.compare_versions("0.11.0-beta.1", "0.11.0") == -1
    assert update_checker.compare_versions("0.11.0", "0.11.0-rc.1") == 1


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.2.3", (1, 2, 3, None)),
        ("0.11.0-beta.1", (0, 11, 0, ("beta", "1"))),
        ("0.11.0-rc1", (0, 11, 0, ("rc1",))),
        ("0.11.0+build.5", (0, 11, 0, None)),
        ("vX.Y", None),
        ("", None),
    ],
)
def test_parse_version_accepts_prerelease_and_build_suffixes(
    version: str,
    expected: tuple[int, int, int, tuple[str, ...] | None] | None,
) -> None:
    assert update_checker._parse_version(version) == expected


def test_check_latest_release_offers_final_to_beta_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, *, timeout: FakeResponse(
            b'{"tag_name":"v0.11.0","html_url":"https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0","body":"notes"}'
        ),
    )

    assert update_checker.check_latest_release("0.11.0-beta.1") == update_checker.ReleaseInfo(
        version="0.11.0",
        html_url="https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0",
    )


def test_check_latest_release_parses_newer_release(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, *, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(
            b'{"tag_name":"v0.10.2","html_url":"https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0","body":"notes"}'
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    release = update_checker.check_latest_release("0.10.1", timeout=1.5)

    assert release == update_checker.ReleaseInfo(
        version="0.10.2",
        html_url="https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0",
    )
    assert captured["timeout"] == 1.5
    assert captured["request"].full_url == (
        "https://api.github.com/repos/SanHsien/agentdeck/releases/latest"
    )
    assert captured["request"].headers["User-agent"] == "agentdeck/0.10.1"


def test_check_latest_release_returns_none_when_remote_is_not_newer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, *, timeout: FakeResponse(
            b'{"tag_name":"v0.10.1","html_url":"https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0","body":"notes"}'
        ),
    )

    assert update_checker.check_latest_release("0.10.1") is None
    assert update_checker.check_latest_release("0.10.2") is None


@pytest.mark.parametrize(
    "response_body",
    [
        b"not json",
        b'{"tag_name":"vX.Y","html_url":"https://github.com/SanHsien/agentdeck/releases/tag/v0.11.0"}',
    ],
)
def test_check_latest_release_returns_none_for_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch,
    response_body: bytes,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, *, timeout: FakeResponse(response_body),
    )

    assert update_checker.check_latest_release("0.10.1") is None


def test_check_latest_release_returns_none_for_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Any, *, timeout: float) -> FakeResponse:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert update_checker.check_latest_release("0.10.1") is None
    assert update_checker.check_latest_release_result("0.10.1").failed is True


def test_a_non_https_release_url_is_refused() -> None:
    """The URL is handed to webbrowser.open(). A javascript: value would
    execute rather than navigate, and the update prompt now puts this address
    in front of the user as the thing to trust."""
    hostile = {
        "tag_name": "v99.0.0",
        "html_url": "javascript:alert(document.cookie)//github.com/x/releases",
    }
    plain_http = {
        "tag_name": "v99.0.0",
        "html_url": "http://github.com/SanHsien/agentdeck/releases/tag/v99",
    }
    good = {
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/SanHsien/agentdeck/releases/tag/v99",
    }

    assert update_checker._release_from_payload(hostile) is None
    assert update_checker._release_from_payload(plain_http) is None
    assert update_checker._release_from_payload(good) is not None


def test_an_oversized_release_response_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """urlopen().read() with no argument buffers whatever the endpoint sends."""

    class Endless:
        def __enter__(self) -> Endless:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self, amt: int | None = None) -> bytes:
            size = amt if amt is not None else update_checker.MAX_RESPONSE_BYTES * 4
            return b"{" + b"x" * (size - 1)

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Endless())

    result = update_checker.check_latest_release_result("0.1.0")

    assert result.release is None
    assert result.failed is True


@pytest.mark.parametrize(
    "html_url",
    [
        "https://evil.example.com/phish",
        "https://github.com.evil.example/SanHsien/agentdeck",
        "https://github.com/SanHsien/agentdeck-evil/releases/tag/v1",
        "https://github.com/SomeoneElse/agentdeck/releases/tag/v1",
        "javascript:alert(1)",
        "http://github.com/SanHsien/agentdeck/releases/tag/v1",
    ],
)
def test_a_release_url_outside_this_repository_is_refused(html_url: str) -> None:
    """This URL is printed in the update prompt and then handed to
    webbrowser.open() if the user says yes. Checking only the scheme let an
    arbitrary address appear under this app's name and open on one click.
    The endpoint it comes from is hard-coded to this repository, so the prefix
    is known exactly and there is no reason to accept anything else.
    """
    assert (
        update_checker._release_from_payload({"tag_name": "v9.9.9", "html_url": html_url}) is None
    )


def test_this_repositorys_own_release_url_is_accepted() -> None:
    release = update_checker._release_from_payload(
        {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/SanHsien/agentdeck/releases/tag/v9.9.9",
        }
    )

    assert release is not None
    assert release.version == "9.9.9"


def test_the_release_prefix_matches_the_api_endpoint() -> None:
    """The two constants name the same repository. If a fork edits one and not
    the other, every update check silently returns nothing -- the app simply
    stops offering updates, with no error to notice.
    """
    owner_repo = update_checker.GITHUB_RELEASES_API.split("/repos/")[1].rsplit("/releases", 1)[0]

    assert f"https://github.com/{owner_repo}/releases/" == update_checker.RELEASE_URL_PREFIX
