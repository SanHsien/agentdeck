# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from providers.grok_quota_probe import GrokQuotaResult
from state import menubar_grok

_FETCHED_AT = "2026-08-26T09:13:58.737Z"
_PERIOD_END = "2026-09-01T15:50:08+00:00"
# Six minutes after the snapshot — inside GROK_STALE_SECONDS, so the fresh
# projection test can assert stale is None.
_NOW = datetime(2026, 8, 26, 9, 20, tzinfo=UTC).timestamp()


def _quota(*, used: float = 33.5, period_end: str = _PERIOD_END) -> GrokQuotaResult:
    return GrokQuotaResult(
        used_percent=used,
        period_end=period_end,
        fetched_at=_FETCHED_AT,
        subscription_tier="SuperGrok Lite",
    )


def test_project_quota_converts_weekly_percent_and_reset() -> None:
    projection = menubar_grok.project_quota(_quota(), "en", now=_NOW)

    assert projection is not None
    assert projection.weekly.title == "Weekly"
    assert projection.weekly.percent == 33.5
    assert projection.weekly.percent_text == "33.5% used"
    assert projection.weekly.available is True
    assert projection.stale is None


def test_project_quota_hides_expired_period() -> None:
    projection = menubar_grok.project_quota(
        _quota(period_end="2026-08-25T15:50:08+00:00"),
        "en",
        now=_NOW,
    )

    assert projection is None


def test_project_quota_marks_stale_snapshot() -> None:
    stale_now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC).timestamp()

    projection = menubar_grok.project_quota(_quota(), "en", now=stale_now)

    assert projection is not None
    assert projection.stale is not None
    assert "minutes" in projection.stale["ageText"]


def test_load_refresh_result_hides_when_grok_home_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(menubar_grok, "find_grok", lambda: None)

    result = menubar_grok.load_refresh_result("en")

    assert result.projection is None
    assert result.hide_grok is True


def test_fallback_projection_is_inert() -> None:
    fallback = menubar_grok.fallback_projection("en")

    assert fallback.weekly.percent is None
    assert fallback.weekly.available is False
    assert fallback.stale is None
