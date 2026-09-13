# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import burn_rate
import usage_rate
from providers.history_loader import UsageEntry


def _entry(total_tokens: int) -> UsageEntry:
    return UsageEntry(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        session_id="session",
        message_id="message",
        request_id="request",
        model="claude-sonnet",
        input_tokens=total_tokens,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        cost_usd=None,
        project="project",
    )


def _entries_at_rate(tokens_per_minute: int) -> list[UsageEntry]:
    """Two entries spanning the classifier's minimum window.

    The rate is expressed rather than implied: with a zero span the denominator
    is the floor, so a single-entry fixture was silently asserting "N tokens in
    one minute" and quietly changed meaning the moment that floor moved.
    """
    minutes = burn_rate.MIN_FORECAST_SPAN_SECONDS / 60.0
    total = int(tokens_per_minute * minutes)
    first = _entry(total)
    second = _entry(0)
    return [
        first,
        replace(second, timestamp=first.timestamp + timedelta(minutes=minutes)),
    ]


def _pin_now_to_last_entry(
    monkeypatch: pytest.MonkeyPatch, entries: list[UsageEntry]
) -> None:
    """Pin "now" to the newest entry.

    The classifier measures elapsed time from now rather than from the last
    entry, so that idle time after you stop working counts against the rate.
    That makes these fixtures' January timestamps months stale against the real
    clock, and every rate would divide down to Idle. Pinning reproduces the
    first-to-last span these threshold tests were written against; the decay
    itself has its own test.
    """
    monkeypatch.setattr(usage_rate, "_utc_now", lambda: max(e.timestamp for e in entries))


def test_group_returns_forced_group() -> None:
    assert usage_rate.UsageRateTracker(forced_group=2).group() == 2


def test_group_returns_idle_for_mock() -> None:
    assert usage_rate.UsageRateTracker(mock=True).group() == 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", 0),
        ("3", 3),
        ("bad", 0),
        ("4", 0),
        ("-1", 0),
    ],
)
def test_group_reads_force_group_env(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected: int,
) -> None:
    monkeypatch.setenv("USAGE_FORCE_GROUP", value)
    monkeypatch.setattr(usage_rate, "load_entries", lambda hours_back: [_entry(10)])

    assert usage_rate.UsageRateTracker().group() == expected


@pytest.mark.parametrize(
    ("tokens", "expected_group"),
    [
        (499, 0),
        (500, 1),
        (2500, 2),
        (6000, 3),
    ],
)
def test_group_burn_rate_buckets(
    monkeypatch: pytest.MonkeyPatch,
    tokens: int,
    expected_group: int,
) -> None:
    entries = _entries_at_rate(tokens)
    monkeypatch.setattr(usage_rate, "load_entries", lambda hours_back: entries)
    _pin_now_to_last_entry(monkeypatch, entries)

    assert usage_rate.UsageRateTracker().group() == expected_group


def test_group_excludes_cache_read_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = UsageEntry(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        session_id="session",
        message_id="message",
        request_id="request",
        model="claude-sonnet",
        input_tokens=100,
        output_tokens=100,
        cache_creation_tokens=0,
        cache_read_tokens=5_000_000,
        cost_usd=None,
        project="project",
    )
    monkeypatch.setattr(usage_rate, "load_entries", lambda hours_back: [entry])
    _pin_now_to_last_entry(monkeypatch, [entry])

    assert usage_rate.UsageRateTracker().group() == 0


def test_group_caches_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_load_entries(hours_back: int) -> list[UsageEntry]:
        nonlocal calls
        calls += 1
        return _entries_at_rate(1000)

    monkeypatch.setattr(usage_rate, "load_entries", fake_load_entries)
    _pin_now_to_last_entry(monkeypatch, _entries_at_rate(1000))
    tracker = usage_rate.UsageRateTracker()

    assert tracker.group() == 1
    assert tracker.group() == 1
    assert calls == 1


def test_group_uses_custom_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = _entries_at_rate(3000)
    _pin_now_to_last_entry(monkeypatch, entries)
    tracker = usage_rate.UsageRateTracker(load=lambda hours_back: entries)

    assert tracker.group() == 2


def _timed_entry(offset_seconds: int, cache_creation: int = 0) -> UsageEntry:
    return UsageEntry(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds),
        session_id="session",
        message_id=f"message-{offset_seconds}",
        request_id=f"request-{offset_seconds}",
        model="claude-opus-5",
        input_tokens=200,
        output_tokens=100,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=0,
        cost_usd=None,
        project="project",
    )


def test_a_fat_system_prompt_is_not_sustained_heavy_burn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One message's cache_creation over a very short span used to divide into a
    rate that read as sustained Heavy: two messages thirty seconds apart, one
    ordinary system prompt, and the sprite ran as if quota were pouring away."""
    entries = [_timed_entry(0, cache_creation=20_000), _timed_entry(30)]
    _pin_now_to_last_entry(monkeypatch, entries)

    tracker = usage_rate.UsageRateTracker(load=lambda hours_back: entries)

    assert usage_rate.GROUP_NAMES[tracker.group()] == "Active"


def test_genuinely_heavy_burn_is_still_heavy(monkeypatch: pytest.MonkeyPatch) -> None:
    """The floor must not become a way to never report Heavy — a fix that only
    suppresses is indistinguishable from deleting the feature."""
    entries = [_timed_entry(minute * 60, cache_creation=12_000) for minute in range(21)]
    _pin_now_to_last_entry(monkeypatch, entries)

    tracker = usage_rate.UsageRateTracker(load=lambda hours_back: entries)

    assert usage_rate.GROUP_NAMES[tracker.group()] == "Heavy"


def test_the_floor_matches_the_forecast_threshold() -> None:
    """Two different answers to "how short is too short" would drift apart, and
    the burn-rate readout and the forecast would disagree about the same data."""
    source = Path(usage_rate.__file__).read_text(encoding="utf-8")

    assert "MIN_FORECAST_SPAN_SECONDS" in source, (
        "the floor was written as its own number again"
    )


def test_the_rate_decays_after_you_stop_working(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ten busy minutes then forty idle ones must not still read as Active.

    The denominator used to span first-to-last entry, which leaves out every
    minute after you stopped. The sprite stayed pinned at a high burn rate until
    the entries aged out of the one-hour window -- forty minutes of telling the
    user quota was pouring away while nothing was running.

    Measured on the real numbers below: 56,100 active tokens over a ten-minute
    burst read 5,610 tokens/min (Active) when the true rate was 1,122 (Normal).
    """
    start = datetime(2026, 1, 1, tzinfo=UTC)
    busy = [
        replace(
            _entry(0),
            timestamp=start + timedelta(minutes=minute),
            output_tokens=5_000,
            input_tokens=100,
        )
        for minute in range(11)
    ]
    monkeypatch.setattr(usage_rate, "_utc_now", lambda: start + timedelta(minutes=50))

    tracker = usage_rate.UsageRateTracker(load=lambda hours_back: busy)

    assert usage_rate.GROUP_NAMES[tracker.group()] == "Normal"


def test_the_same_burst_still_reads_high_while_it_is_happening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The decay must not become a way to never report a busy machine.

    Exactly the data from the test above, read while the burst is still running
    instead of forty minutes later: 5,610 tokens/min, one bucket below the Heavy
    threshold of 6,000. Same entries, two different answers -- which is the
    whole point of measuring from now.
    """
    start = datetime(2026, 1, 1, tzinfo=UTC)
    busy = [
        replace(
            _entry(0),
            timestamp=start + timedelta(minutes=minute),
            output_tokens=5_000,
            input_tokens=100,
        )
        for minute in range(11)
    ]
    monkeypatch.setattr(usage_rate, "_utc_now", lambda: busy[-1].timestamp)

    tracker = usage_rate.UsageRateTracker(load=lambda hours_back: busy)

    assert usage_rate.GROUP_NAMES[tracker.group()] == "Active"
