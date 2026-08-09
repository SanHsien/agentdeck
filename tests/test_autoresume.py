# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from adapters.types import RateLimits
from state.autoresume import (
    REASON_ALREADY_RESET,
    REASON_DISABLED,
    REASON_NO_RESET_TIME,
    REASON_NO_TARGET,
    REASON_NOT_EXHAUSTED,
    REASON_READY,
    REASON_WEEKLY_CEILING,
    AutoResumeConfig,
    ResumeTarget,
    decide,
)

NOW = 1_786_000_000
RESET_AT = NOW + 3600


def _target() -> ResumeTarget:
    return ResumeTarget(
        session_id="abc-123",
        cwd="C:/work/project",
        transcript_path="C:/logs/abc-123.jsonl",
    )


def _limits(
    five_pct: float | None = 99.0,
    seven_pct: float | None = 40.0,
    resets_at: int | None = RESET_AT,
) -> RateLimits:
    return RateLimits(
        five_hour_pct=five_pct,
        five_hour_resets_at=resets_at,
        seven_day_pct=seven_pct,
    )


def _enabled(**overrides: float | bool | int) -> AutoResumeConfig:
    return AutoResumeConfig(enabled=True, **overrides)  # type: ignore[arg-type]


def test_exhausted_session_schedules_after_the_reset_stamp() -> None:
    decision = decide(_limits(), _target(), _enabled(), NOW)

    assert decision.action == "schedule"
    assert decision.reason == REASON_READY
    assert decision.run_at == RESET_AT + 180


def test_lead_seconds_offsets_the_run_time() -> None:
    decision = decide(_limits(), _target(), _enabled(lead_seconds=600), NOW)

    assert decision.run_at == RESET_AT + 600


def test_disabled_config_cancels_rather_than_skipping() -> None:
    decision = decide(_limits(), _target(), AutoResumeConfig(), NOW)

    assert decision.action == "cancel"
    assert decision.reason == REASON_DISABLED


def test_session_below_the_trigger_is_not_worth_resuming() -> None:
    decision = decide(_limits(five_pct=40.0), _target(), _enabled(), NOW)

    assert decision.action == "cancel"
    assert decision.reason == REASON_NOT_EXHAUSTED


def test_trigger_boundary_counts_as_exhausted() -> None:
    decision = decide(_limits(five_pct=95.0), _target(), _enabled(trigger_pct=95.0), NOW)

    assert decision.action == "schedule"


def test_spent_weekly_allowance_blocks_the_overnight_run() -> None:
    decision = decide(_limits(seven_pct=89.0), _target(), _enabled(), NOW)

    assert decision.action == "cancel"
    assert decision.reason == REASON_WEEKLY_CEILING


def test_weekly_ceiling_boundary_blocks() -> None:
    decision = decide(_limits(seven_pct=85.0), _target(), _enabled(weekly_ceiling_pct=85.0), NOW)

    assert decision.reason == REASON_WEEKLY_CEILING


def test_raising_the_ceiling_permits_a_run_that_the_default_would_block() -> None:
    decision = decide(_limits(seven_pct=89.0), _target(), _enabled(weekly_ceiling_pct=95.0), NOW)

    assert decision.action == "schedule"


def test_missing_weekly_figure_does_not_block() -> None:
    decision = decide(_limits(seven_pct=None), _target(), _enabled(), NOW)

    assert decision.action == "schedule"


def test_five_hour_gate_is_reported_ahead_of_the_weekly_one() -> None:
    decision = decide(_limits(five_pct=10.0, seven_pct=99.0), _target(), _enabled(), NOW)

    assert decision.reason == REASON_NOT_EXHAUSTED


def test_reset_stamp_in_the_past_cancels() -> None:
    decision = decide(_limits(resets_at=NOW - 1), _target(), _enabled(), NOW)

    assert decision.action == "cancel"
    assert decision.reason == REASON_ALREADY_RESET


def test_reset_stamp_exactly_now_counts_as_already_reset() -> None:
    decision = decide(_limits(resets_at=NOW), _target(), _enabled(), NOW)

    assert decision.reason == REASON_ALREADY_RESET


def test_snapshot_without_a_reset_stamp_skips_instead_of_cancelling() -> None:
    decision = decide(_limits(resets_at=None), _target(), _enabled(), NOW)

    assert decision.action == "skip"
    assert decision.reason == REASON_NO_RESET_TIME


def test_absent_limits_skip_instead_of_cancelling() -> None:
    decision = decide(None, _target(), _enabled(), NOW)

    assert decision.action == "skip"
    assert decision.reason == REASON_NO_RESET_TIME


def test_missing_target_skips() -> None:
    decision = decide(_limits(), None, _enabled(), NOW)

    assert decision.action == "skip"
    assert decision.reason == REASON_NO_TARGET


def test_target_without_a_working_directory_is_unusable() -> None:
    target = ResumeTarget(session_id="abc-123", cwd="")

    decision = decide(_limits(), target, _enabled(), NOW)

    assert decision.reason == REASON_NO_TARGET


def test_target_without_a_session_id_is_unusable() -> None:
    target = ResumeTarget(session_id="", cwd="C:/work/project")

    assert decide(_limits(), target, _enabled(), NOW).reason == REASON_NO_TARGET


def test_frozen_percentages_still_schedule_while_the_stamp_is_future() -> None:
    """The status file stops updating once the machine goes idle overnight.

    The percentages then stay frozen at whatever they were when work stopped, so the
    decision has to keep working off the absolute reset stamp alone. Regression guard
    for the tempting-but-wrong "watch for the number to drop" approach.
    """
    stale = _limits(five_pct=100.0, resets_at=NOW + 5)

    first = decide(stale, _target(), _enabled(), NOW)
    later = decide(stale, _target(), _enabled(), NOW + 4)

    assert first.action == "schedule"
    assert later.action == "schedule"
    assert first.run_at == later.run_at
