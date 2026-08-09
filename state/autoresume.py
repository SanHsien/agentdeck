# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Decide whether to schedule an unattended resume after the 5-hour quota resets.

When a session runs out of its 5-hour allowance the work simply stops until the
window rolls over. This module answers one question — *should a one-shot resume be
scheduled, and for when* — and answers it as a pure function so the policy is
testable without touching the Windows scheduler, the status file, or the clock.

Two constraints shape the policy and are easy to get wrong:

**The status file goes stale exactly when this feature matters.** It is only written
while Claude Code refreshes its status line, so once the machine is idle overnight the
percentages freeze. Nothing here may infer "the quota came back" from a *change* in
those numbers. ``five_hour_resets_at`` is an absolute epoch stamp, so a stale snapshot
still carries a usable future deadline — that is what the decision keys on.

**The weekly window is the real ceiling.** A resume fired on the 5-hour reset can spend
the rest of the week's allowance while nobody is watching. ``weekly_ceiling_pct`` gates
on the 7-day figure so the night's work cannot eat the days that follow.

The caller owns the side effects: registering and cancelling the scheduled task, and
the handoff text handed to the resumed run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adapters.types import RateLimits, ResumeTarget

__all__ = [
    "AutoResumeConfig",
    "ResumeTarget",
    "ScheduleDecision",
    "decide",
]

#: Fire this long after ``resets_at`` rather than on the boundary itself — the
#: server-side rollover is not instantaneous and a resume that races it just fails.
DEFAULT_LEAD_SECONDS = 180

#: Only schedule when the 5-hour window is effectively spent. Below this the session
#: is not blocked, so a resume would relaunch work nobody was waiting on.
DEFAULT_TRIGGER_PCT = 95.0

#: Refuse to resume once this much of the 7-day allowance is gone, leaving headroom
#: for the days after tonight. See the module docstring.
DEFAULT_WEEKLY_CEILING_PCT = 85.0

DecisionAction = Literal["schedule", "skip", "cancel"]

#: Stable identifiers, not prose — the caller maps these to i18n keys and log lines.
REASON_DISABLED = "disabled"
REASON_NO_TARGET = "no_target"
REASON_NO_RESET_TIME = "no_reset_time"
REASON_NOT_EXHAUSTED = "not_exhausted"
REASON_WEEKLY_CEILING = "weekly_ceiling"
REASON_ALREADY_RESET = "already_reset"
REASON_READY = "ready"


@dataclass(frozen=True, slots=True)
class AutoResumeConfig:
    """User-tunable policy. Off unless explicitly enabled."""

    enabled: bool = False
    trigger_pct: float = DEFAULT_TRIGGER_PCT
    weekly_ceiling_pct: float = DEFAULT_WEEKLY_CEILING_PCT
    lead_seconds: int = DEFAULT_LEAD_SECONDS


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    """``schedule`` registers a one-shot task, ``cancel`` clears any existing one.

    ``skip`` deliberately leaves an already-registered task alone: a snapshot that
    briefly loses its numbers should not cancel a resume that is already pending.
    """

    action: DecisionAction
    reason: str
    run_at: int | None = None


def decide(
    limits: RateLimits | None,
    target: ResumeTarget | None,
    config: AutoResumeConfig,
    now_ts: int,
) -> ScheduleDecision:
    """Return the scheduling decision for the current snapshot.

    ``now_ts`` is injected rather than read from the clock so the policy stays
    deterministic under test.
    """
    if not config.enabled:
        return ScheduleDecision("cancel", REASON_DISABLED)

    if target is None or not target.is_usable():
        return ScheduleDecision("skip", REASON_NO_TARGET)

    if limits is None or limits.five_hour_resets_at is None:
        return ScheduleDecision("skip", REASON_NO_RESET_TIME)

    # A reset stamp in the past means the window already rolled over: whatever was
    # blocked is runnable now, so there is nothing left to wait for. Cancelling here
    # also clears the task left behind by a resume that has already fired.
    if limits.five_hour_resets_at <= now_ts:
        return ScheduleDecision("cancel", REASON_ALREADY_RESET)

    five_pct = limits.five_hour_pct
    if five_pct is None or five_pct < config.trigger_pct:
        return ScheduleDecision("cancel", REASON_NOT_EXHAUSTED)

    # Checked after the 5-hour gate so the weekly ceiling is only reported when it is
    # the reason a resume was actually withheld.
    weekly_pct = limits.seven_day_pct
    if weekly_pct is not None and weekly_pct >= config.weekly_ceiling_pct:
        return ScheduleDecision("cancel", REASON_WEEKLY_CEILING)

    return ScheduleDecision(
        "schedule",
        REASON_READY,
        run_at=limits.five_hour_resets_at + config.lead_seconds,
    )
