# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

GITHUB_RELEASES_API = "https://api.github.com/repos/SanHsien/agentdeck/releases/latest"
# The only prefix a release page from the endpoint above can legitimately
# have. The URL is both shown in the update prompt and handed to
# webbrowser.open(), so a payload that named any other host would put an
# arbitrary address in front of the user under this app's name and open it
# on request. Checking the scheme alone let through both
# https://evil.example.com/phish and the look-alike
# https://github.com.evil.example/SanHsien/agentdeck.
RELEASE_URL_PREFIX = "https://github.com/SanHsien/agentdeck/releases/"
# A release payload is tens of KB; cap the read so a broken or hostile endpoint
# cannot make us buffer an unbounded response.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    html_url: str


@dataclass(frozen=True, slots=True)
class ReleaseCheckResult:
    release: ReleaseInfo | None
    failed: bool = False


def _parse_version(version: str) -> tuple[int, int, int, tuple[str, ...] | None] | None:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)?$", version)
    if match is None:
        return None
    suffix = match.group(4) or ""
    prerelease: tuple[str, ...] | None = None
    if suffix.startswith("-") or suffix.startswith("."):
        prerelease = tuple(part for part in suffix[1:].split("+", 1)[0].split(".") if part)
        if not prerelease:
            return None
    elif suffix and not suffix.startswith("+"):
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease)


def compare_versions(a: str, b: str) -> int:
    parsed_a = _parse_version(a)
    parsed_b = _parse_version(b)
    if parsed_a is None or parsed_b is None:
        raise ValueError("versions must use MAJOR.MINOR.PATCH numeric format")
    base_a = parsed_a[:3]
    base_b = parsed_b[:3]
    if base_a < base_b:
        return -1
    if base_a > base_b:
        return 1
    prerelease_a = parsed_a[3]
    prerelease_b = parsed_b[3]
    if prerelease_a is None and prerelease_b is None:
        return 0
    if prerelease_a is None:
        return 1
    if prerelease_b is None:
        return -1
    for part_a, part_b in zip(prerelease_a, prerelease_b, strict=False):
        is_digit_a = part_a.isdigit()
        is_digit_b = part_b.isdigit()
        if is_digit_a and is_digit_b:
            value_a = int(part_a)
            value_b = int(part_b)
            if value_a < value_b:
                return -1
            if value_a > value_b:
                return 1
            continue
        if is_digit_a != is_digit_b:
            return -1 if is_digit_a else 1
        if part_a < part_b:
            return -1
        if part_a > part_b:
            return 1
    if len(prerelease_a) < len(prerelease_b):
        return -1
    if len(prerelease_a) > len(prerelease_b):
        return 1
    return 0


def check_latest_release(current_version: str, *, timeout: float = 5.0) -> ReleaseInfo | None:
    return check_latest_release_result(current_version, timeout=timeout).release


def check_latest_release_result(
    current_version: str,
    *,
    timeout: float = 5.0,
) -> ReleaseCheckResult:
    if _parse_version(current_version) is None:
        return ReleaseCheckResult(None)

    request = urllib.request.Request(
        GITHUB_RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"agentdeck/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("release response exceeds the size limit")
        payload = json.loads(raw.decode("utf-8"))
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        urllib.error.URLError,
        urllib.error.HTTPError,
    ):
        return ReleaseCheckResult(None, failed=True)

    release = _release_from_payload(payload)
    if release is None:
        return ReleaseCheckResult(None)
    try:
        if compare_versions(current_version, release.version) >= 0:
            return ReleaseCheckResult(None)
    except ValueError:
        return ReleaseCheckResult(None)
    return ReleaseCheckResult(release)


def _release_from_payload(payload: Any) -> ReleaseInfo | None:
    if not isinstance(payload, dict):
        return None

    tag_name = payload.get("tag_name")
    html_url = payload.get("html_url")
    if not isinstance(tag_name, str) or not isinstance(html_url, str):
        return None
    # This URL is shown to the user and handed to webbrowser.open(). It comes
    # from a hard-coded endpoint on this repository, so its prefix is known
    # exactly; anything else is not our release page.
    if not html_url.startswith(RELEASE_URL_PREFIX):
        return None

    version = tag_name.removeprefix("v")
    if _parse_version(version) is None:
        return None
    return ReleaseInfo(version=version, html_url=html_url)
