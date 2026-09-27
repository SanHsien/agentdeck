# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import update_checker

AUTO_CHECK_TTL_SECONDS = 24 * 60 * 60
# How long a "later" answer suppresses the automatic prompt. Lived in menubar.py
# until macOS support was removed; it belongs here with the rest of the gating so
# both hosts share one definition.
UPDATE_DISMISS_SECONDS = 24 * 3600


def dismissed_recently(prefs: Mapping[str, Any]) -> bool:
    """True while a recent "later" answer should keep the prompt quiet."""
    dismissed_at = prefs.get("update_dismissed_at")
    try:
        return (time.time() - float(dismissed_at)) < UPDATE_DISMISS_SECONDS  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def should_prompt(prefs: Mapping[str, Any], release_version: str) -> bool:
    """Whether an automatic check may show the prompt for this release."""
    if dismissed_recently(prefs):
        return False
    return prefs.get("update_skipped_version") != release_version


def auto_check_is_due(prefs: dict[str, Any]) -> bool:
    cached = prefs.get("last_update_check")
    checked_at = cached.get("checked_at") if isinstance(cached, dict) else None
    if not isinstance(checked_at, int | float):
        return True
    return (time.time() - float(checked_at)) >= AUTO_CHECK_TTL_SECONDS


def stale_cache_reset(prefs: dict[str, Any], current_version: str) -> dict[str, Any] | None:
    cached = prefs.get("last_update_check")
    if (
        isinstance(cached, dict)
        and isinstance(cached.get("latest_version"), str)
        and cached.get("current_version") != current_version
        and update_checker.compare_versions(current_version, cached["latest_version"]) >= 0
    ):
        return {
            **cached,
            "current_version": current_version,
            "latest_version": current_version,
        }
    return None


def build_check_cache_entry(
    current_version: str,
    release: update_checker.ReleaseInfo | None,
) -> dict[str, Any]:
    return {
        "checked_at": time.time(),
        "current_version": current_version,
        "latest_version": release.version if release else current_version,
        "release_url": release.html_url if release else None,
    }


def resolve_alert_choice(result_code: int, release_version: str) -> tuple[str, dict[str, str]]:
    if result_code == 1000:
        return ("open", {})
    if result_code == 1002:
        return ("skip", {"update_skipped_version": release_version})
    return ("dismiss", {})


# MessageBoxW return codes for the three-button update prompt, the Windows
# counterpart of upstream's NSAlert. The mapping lives here rather than in
# wintray so it stays unit-testable.
#
# Button assignment matters: MB_YESNOCANCEL returns IDCANCEL when the user
# presses Escape or clicks the title-bar close button, so IDCANCEL must land on
# the harmless choice. "Skip this version" suppresses the release permanently, so
# it gets the explicit No button and Escape means "ask me again later".
IDCANCEL = 2
IDYES = 6
IDNO = 7


def resolve_message_box_choice(
    result_code: int, release_version: str
) -> tuple[str, dict[str, str]]:
    """Map a MessageBoxW result onto the same actions as ``resolve_alert_choice``.

    Yes downloads, No skips the version for good, and everything else — Cancel,
    Escape, the close button, or a code Windows does not document — defers.
    Deferring on the unknown path is deliberate: silently suppressing a version
    because a dialog was dismissed would hide the update forever.
    """
    if result_code == IDYES:
        return ("open", {})
    if result_code == IDNO:
        return ("skip", {"update_skipped_version": release_version})
    return ("dismiss", {})
