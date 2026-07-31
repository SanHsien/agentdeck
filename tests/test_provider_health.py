# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from provider_health import (
    STALE_AFTER_SECONDS,
    HealthState,
    ProviderHealth,
    antigravity_health,
    claude_health,
    codex_health,
    worst_of,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = 2_000_000_000.0


def test_a_missing_hook_outranks_a_stale_file() -> None:
    """Without the hook the file cannot update, so its age is a symptom.

    Reporting "data is old" here would send the user to look at Claude Code
    when the thing to fix is the install.
    """
    health = claude_health(
        hook_installed=False,
        status_file_exists=True,
        last_updated=NOW - 10 * 3600,
        now=NOW,
    )

    assert health.state is HealthState.MISCONFIGURED
    assert health.reason_key == "health_claude_no_hook"
    assert health.next_step_key == "health_claude_no_hook_fix"


def test_claude_is_ready_inside_its_window_and_stale_outside_it() -> None:
    window = STALE_AFTER_SECONDS["claude"]

    fresh = claude_health(
        hook_installed=True, status_file_exists=True, last_updated=NOW - window + 1, now=NOW
    )
    old = claude_health(
        hook_installed=True, status_file_exists=True, last_updated=NOW - window - 1, now=NOW
    )

    assert fresh.state is HealthState.READY
    assert old.state is HealthState.STALE
    assert old.next_step_key == "health_claude_stale_fix"


def test_claude_with_a_hook_but_no_file_has_not_run_yet() -> None:
    health = claude_health(
        hook_installed=True, status_file_exists=False, last_updated=None, now=NOW
    )

    assert health.state is HealthState.MISSING


def test_a_read_error_wins_over_every_other_claude_branch() -> None:
    health = claude_health(
        hook_installed=False,
        status_file_exists=False,
        last_updated=None,
        now=NOW,
        read_error="PermissionError: denied",
    )

    assert health.state is HealthState.ERROR
    assert health.detail == "PermissionError: denied"


@pytest.mark.parametrize(
    ("sessions_dir_exists", "session_count"),
    [(False, 0), (True, 0)],
)
def test_codex_treats_no_directory_and_no_logs_the_same(
    sessions_dir_exists: bool, session_count: int
) -> None:
    """Both mean "Codex has not run here", which is one situation to a user."""
    health = codex_health(
        sessions_dir_exists=sessions_dir_exists,
        session_count=session_count,
        last_updated=None,
        now=NOW,
    )

    assert health.state is HealthState.MISSING
    assert health.next_step_key == "health_codex_missing_fix"


def test_codex_keeps_its_own_staleness_window() -> None:
    window = STALE_AFTER_SECONDS["codex"]

    fresh = codex_health(
        sessions_dir_exists=True, session_count=3, last_updated=NOW - window + 1, now=NOW
    )
    old = codex_health(
        sessions_dir_exists=True, session_count=3, last_updated=NOW - window - 1, now=NOW
    )

    assert fresh.state is HealthState.READY
    assert old.state is HealthState.STALE


def test_antigravity_separates_being_off_from_not_being_signed_in() -> None:
    """Two different user actions, so they must not collapse into one message."""
    off = antigravity_health(
        enabled=False, credentials_found=True, last_updated=NOW, now=NOW
    )
    signed_out = antigravity_health(
        enabled=True, credentials_found=False, last_updated=None, now=NOW
    )

    assert off.state is HealthState.MISCONFIGURED
    assert signed_out.state is HealthState.MISCONFIGURED
    assert off.next_step_key != signed_out.next_step_key


def test_a_dead_endpoint_is_unavailable_not_an_error_and_keeps_its_timestamp() -> None:
    """Cached numbers stay on screen, so the user needs to know how old they are."""
    health = antigravity_health(
        enabled=True,
        credentials_found=True,
        last_updated=NOW - 60,
        now=NOW,
        remote_unavailable=True,
    )

    assert health.state is HealthState.UNAVAILABLE
    assert health.last_updated == NOW - 60
    assert health.is_usable is False


def test_usable_covers_stale_because_old_numbers_still_beat_no_numbers() -> None:
    ready = claude_health(
        hook_installed=True, status_file_exists=True, last_updated=NOW, now=NOW
    )
    stale = claude_health(
        hook_installed=True,
        status_file_exists=True,
        last_updated=NOW - 10 * 3600,
        now=NOW,
    )
    missing = codex_health(
        sessions_dir_exists=False, session_count=0, last_updated=None, now=NOW
    )

    assert ready.is_usable and stale.is_usable
    assert not missing.is_usable


def test_worst_of_surfaces_the_state_that_needs_action() -> None:
    healths = [
        claude_health(hook_installed=True, status_file_exists=True, last_updated=NOW, now=NOW),
        codex_health(sessions_dir_exists=True, session_count=1, last_updated=NOW, now=NOW),
        antigravity_health(
            enabled=True, credentials_found=False, last_updated=None, now=NOW
        ),
    ]

    worst = worst_of(healths)

    assert worst is not None
    assert worst.state is HealthState.MISCONFIGURED
    assert worst_of([]) is None


def test_age_is_reported_forward_only() -> None:
    """A clock that jumped must not produce a negative age in the UI."""
    health = ProviderHealth("claude", HealthState.READY, "health_claude_ready",
                            last_updated=NOW + 30)

    assert health.age_seconds(NOW) == 0.0
    assert ProviderHealth("claude", HealthState.MISSING, "x").age_seconds(NOW) is None


def test_every_key_this_module_hands_out_exists_in_both_languages() -> None:
    """The keys are only useful if `_t()` can resolve them.

    They are produced by branches most users never reach, so a missing
    translation would surface as a raw key in front of whoever is already
    having a bad day.
    """
    source = (ROOT / "provider_health.py").read_text(encoding="utf-8")
    # Only string literals, so the docstring warning about a wrong key shape
    # does not get mistaken for a key that must exist.
    keys = set(re.findall(r'"(health_[a-z_]+)"', source))
    translations = json.loads((ROOT / "i18n.json").read_text(encoding="utf-8"))

    assert keys, "no health keys found; the extraction pattern went stale"
    for language in ("zh-TW", "en"):
        missing = sorted(key for key in keys if key not in translations[language])
        assert not missing, f"{language} is missing: {missing}"
