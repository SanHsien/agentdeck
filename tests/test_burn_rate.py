# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import pytest

from burn_rate import BurnRateTracker


def test_forecast_none_for_empty_buffer() -> None:
    tracker = BurnRateTracker()

    assert tracker.forecast_seconds() is None


def test_forecast_none_for_single_sample() -> None:
    tracker = BurnRateTracker()
    tracker.record(100.0, 20.0)

    assert tracker.forecast_seconds() is None


def test_forecast_uses_recent_samples() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 10.0)
    tracker.record(75.0, 17.5)
    tracker.record(150.0, 25.0)
    tracker.record(225.0, 32.5)
    tracker.record(300.0, 40.0)

    assert tracker.forecast_seconds() == pytest.approx(600.0)


def test_forecast_still_shortens_when_burn_accelerates() -> None:
    """The window slope must not become a way to never warn.

    It is more conservative than the old EMA on a rising curve -- deliberately,
    because the EMA's responsiveness was indistinguishable from its false
    alarms -- but a burn that is genuinely speeding up still has to forecast
    sooner than the same quota burning steadily.
    """
    accelerating = BurnRateTracker()
    for timestamp, percent in [
        (0.0, 10.0), (75.0, 11.0), (150.0, 12.0),
        (225.0, 17.0), (300.0, 32.0),
    ]:
        accelerating.record(timestamp, percent)
    steady = BurnRateTracker()
    for timestamp, percent in [
        (0.0, 10.0), (75.0, 11.0), (150.0, 12.0),
        (225.0, 13.0), (300.0, 14.0),
    ]:
        steady.record(timestamp, percent)

    fast = accelerating.forecast_seconds(min_span_seconds=300.0)
    slow = steady.forecast_seconds(min_span_seconds=300.0)

    assert fast is not None and slow is not None
    assert fast < slow / 4


def test_one_spike_in_a_short_gap_does_not_dominate_the_forecast() -> None:
    """Claude's percentage moves in steps. One large message landing in a short
    polling gap used to produce an enormous instantaneous rate that the EMA then
    weighted at half: ten minutes of steady 0.5%/min followed by 7% inside five
    seconds forecast 0.9 minutes to empty, where the window says about 28."""
    tracker = BurnRateTracker()
    for timestamp, percent in [
        (0.0, 50.0), (120.0, 51.0), (240.0, 52.0),
        (360.0, 53.0), (480.0, 54.0), (600.0, 55.0), (605.0, 62.0),
    ]:
        tracker.record(timestamp, percent)

    forecast = tracker.forecast_seconds()

    assert forecast is not None
    assert forecast > 20 * 60, "a single spike blew the forecast down to under a minute"


def test_forecast_default_allows_six_minute_span() -> None:
    tracker = BurnRateTracker()
    for index in range(10):
        tracker.record(index * 40.0, index * (10.0 / 9.0))

    assert tracker.forecast_seconds() is not None


def test_forecast_default_none_for_three_samples_under_minimums() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 0.0)
    tracker.record(90.0, 5.0)
    tracker.record(180.0, 10.0)

    assert tracker.forecast_seconds() is None


def test_forecast_weekly_span_threshold_rejects_six_minute_span() -> None:
    tracker = BurnRateTracker()
    for index in range(10):
        tracker.record(index * 40.0, index * (10.0 / 9.0))

    assert tracker.forecast_seconds(window_seconds=30 * 60, min_span_seconds=30 * 60) is None


def test_forecast_weekly_span_threshold_allows_thirty_minute_span() -> None:
    tracker = BurnRateTracker()
    for index in range(31):
        tracker.record(index * 60.0, index * (30.0 / 30.0))

    assert tracker.forecast_seconds(
        window_seconds=30 * 60,
        min_span_seconds=30 * 60,
    ) == pytest.approx(4200.0)


def test_forecast_window_seconds_filters_old_samples_from_slope() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 0.0)
    for index in range(31):
        tracker.record(300.0 + (index * 60.0), 20.0 + index)

    assert tracker.forecast_seconds(
        window_seconds=30 * 60,
        min_span_seconds=30 * 60,
    ) == pytest.approx(3000.0)


def test_forecast_explicit_none_parameters_match_default() -> None:
    tracker = BurnRateTracker()
    for index in range(10):
        tracker.record(index * 40.0, index * (10.0 / 9.0))

    assert tracker.forecast_seconds(
        window_seconds=None,
        min_span_seconds=None,
    ) == tracker.forecast_seconds()


def test_forecast_none_for_too_short_span() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 10.0)
    tracker.record(45.0, 20.0)
    tracker.record(90.0, 30.0)
    tracker.record(135.0, 40.0)
    tracker.record(180.0, 50.0)

    assert tracker.forecast_seconds() is None


def test_record_detects_reset_and_clears_old_samples() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 60.0)
    tracker.record(60.0, 68.0)
    tracker.record(120.0, 10.0)
    tracker.record(210.0, 15.0)
    tracker.record(300.0, 20.0)
    tracker.record(390.0, 25.0)
    tracker.record(480.0, 30.0)

    assert tracker.forecast_seconds() == pytest.approx(1260.0)


def test_forecast_none_for_negative_slope() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 60.0)
    tracker.record(300.0, 40.0)

    assert tracker.forecast_seconds() is None


def test_forecast_none_for_duplicate_timestamp_zero_span() -> None:
    tracker = BurnRateTracker()
    for percent in (10.0, 20.0, 30.0, 40.0, 50.0):
        tracker.record(100.0, percent)

    assert tracker.forecast_seconds(min_span_seconds=0) is None


def test_record_prunes_samples_older_than_rolling_window() -> None:
    tracker = BurnRateTracker()
    tracker.record(0.0, 10.0)
    tracker.record(601.0, 20.0)
    tracker.record(751.0, 35.0)
    tracker.record(901.0, 50.0)
    tracker.record(1051.0, 65.0)
    tracker.record(1201.0, 80.0)

    assert tracker.forecast_seconds() == pytest.approx(200.0)
