# SPDX-License-Identifier: AGPL-3.0-only
"""Upstream #273/#274/#278/#279: partial quota must stay live and safe."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import status_projection
import usage_client
import usage_statusline
from adapters import rate_limits
from state.menubar_state import _quota_row
from usage_notifications import QuotaNotifier

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


@pytest.fixture
def status_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "agentdeck-status.json"
    monkeypatch.setattr(usage_statusline, "STATUS_FILE", str(path))
    for module in (usage_client, rate_limits):
        monkeypatch.setattr(module, "STATUS_FILE", str(path))
        monkeypatch.setattr(module, "LEGACY_STATUS_FILE", str(tmp_path / "legacy.json"))
        monkeypatch.setattr(module, "TT_STATUS_FILE", str(tmp_path / "tt.json"))
    monkeypatch.setattr(usage_client, "CLAUDE_JSON_FILE", str(tmp_path / "claude.json"))
    monkeypatch.setattr(usage_client, "CLAUDE_DESKTOP_USAGE_FILE", str(tmp_path / "desktop.json"))
    monkeypatch.setattr("usage_client.time.time", lambda: NOW.timestamp())
    return path


@pytest.mark.parametrize("window,seconds", [("five_hour", 18000), ("seven_day", 604800)])
@pytest.mark.parametrize("offset,retained", [(3600, True), (-3600, True), (0, False)])
def test_partial_save_updates_fresh_window_and_bounds_cached_retention(
    status_path: Path, window: str, seconds: int, offset: int, retained: bool
) -> None:
    other = "seven_day" if window == "five_hour" else "five_hour"
    reset = NOW.timestamp() + (offset if offset else -seconds)
    cached = {"used_percentage": 100, "resets_at": reset}
    fresh = {"used_percentage": 46, "resets_at": NOW.timestamp() + 7200}
    status_path.write_text(json.dumps({"rate_limits": {
        window: cached, other: {"used_percentage": 34, "resets_at": 9_999_999_999},
    }}), encoding="utf-8")

    usage_statusline.save({"rate_limits": {other: fresh}}, NOW)

    data = json.loads(status_path.read_text(encoding="utf-8"))
    assert data["rate_limits"][other] == fresh
    assert data["rate_limits"].get(window) == (cached if retained else None)
    snapshot = usage_client._build_snapshot(data)
    assert snapshot is not None
    percent = snapshot.current_percent if window == "five_hour" else snapshot.weekly_percent
    expected = (100 if offset > 0 else 0) if retained else None
    assert percent == expected


@pytest.mark.parametrize("window", ["five_hour", "seven_day"])
def test_client_uses_a_single_window_instead_of_stale_cache(status_path: Path, window: str) -> None:
    status_path.write_text(json.dumps({"rate_limits": {
        window: {"used_percentage": 46, "resets_at": NOW.timestamp() + 3600},
    }}), encoding="utf-8")
    # Even a newer .claude.json is only a fallback; Desktop precedence stays separate.
    Path(usage_client.CLAUDE_JSON_FILE).write_text(json.dumps({"cachedUsageUtilization": {
        "fetchedAtMs": (NOW.timestamp() + 10) * 1000,
        "utilization": {"five_hour": {"utilization": 3}, "seven_day": {"utilization": 34}},
    }}), encoding="utf-8")

    outcome = asyncio.run(usage_client.ClaudeUsageClient(mock=False).fetch_once())

    assert outcome.snapshot is not None
    assert outcome.snapshot.data_source == "hook"
    assert outcome.snapshot.current_percent == (46 if window == "five_hour" else None)
    assert outcome.snapshot.weekly_percent == (46 if window == "seven_day" else None)
    if window == "seven_day":
        assert outcome.snapshot.current_reset_at is None


@pytest.mark.parametrize("bad", ["broken", [], True, {"used_percentage": "bad"}])
def test_malformed_present_window_does_not_bypass_fallback(status_path: Path, bad: Any) -> None:
    status_path.write_text(json.dumps({"rate_limits": {
        "five_hour": bad, "seven_day": {"used_percentage": 46},
    }}), encoding="utf-8")
    outcome = asyncio.run(usage_client.ClaudeUsageClient(mock=False).fetch_once())
    assert outcome.state is usage_client.PollState.LOADING
    # The report adapter also must not call .get() on a malformed window.
    limits = rate_limits.load_rate_limits()
    assert limits is not None
    assert limits.seven_day_pct == 46


def test_no_quota_payload_keeps_expired_cache(status_path: Path) -> None:
    cached = {"seven_day": {"used_percentage": 34, "resets_at": 1000}}
    status_path.write_text(json.dumps({"rate_limits": cached}), encoding="utf-8")
    usage_statusline.save({"model": {"display_name": "new"}}, NOW)
    assert json.loads(status_path.read_text(encoding="utf-8"))["rate_limits"] == cached


def test_unknown_reset_is_not_invented_for_keeper(status_path: Path) -> None:
    snapshot = usage_client._build_snapshot({"rate_limits": {
        "five_hour": {"used_percentage": 46}, "seven_day": {"used_percentage": 34},
    }})
    assert snapshot is not None
    assert snapshot.current_percent == 46
    assert snapshot.current_reset_at is None


def test_expired_hook_window_renders_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usage_statusline, "get_width", lambda: 116)
    output = usage_statusline._render_core({"rate_limits": {
        "five_hour": {"used_percentage": 100, "resets_at": NOW.timestamp() - 1},
    }}, NOW)
    assert "100%" not in re.sub(r"\x1b\[[0-9;]*m", "", output)
    assert "0%" in output


@pytest.mark.parametrize("window", ["five_hour", "seven_day"])
def test_retained_expired_window_reaches_panel_and_recovery_notification(
    status_path: Path, window: str
) -> None:
    other = "seven_day" if window == "five_hour" else "five_hour"
    reset = NOW.timestamp() - 3600
    status_path.write_text(json.dumps({"rate_limits": {
        window: {"used_percentage": 100, "resets_at": reset},
    }}), encoding="utf-8")
    channel = "claude_session" if window == "five_hour" else "claude_weekly"
    notifier = QuotaNotifier()
    notifier.update({channel: (100, True)})
    usage_statusline.save({"rate_limits": {
        other: {"used_percentage": 46, "resets_at": NOW.timestamp() + 7200},
    }}, NOW)

    outcome = asyncio.run(usage_client.ClaudeUsageClient(mock=False).fetch_once())
    snapshot = outcome.snapshot
    assert snapshot is not None
    percent = snapshot.current_percent if window == "five_hour" else snapshot.weekly_percent
    boundary = snapshot.current_reset_at if window == "five_hour" else snapshot.weekly_reset_at
    assert percent == 0
    assert boundary == reset
    row = _quota_row(window, percent, boundary, NOW.timestamp(), (0, 0, 0), "zh-TW")
    assert row.available and row.percent == 0
    events = notifier.update({channel: (row.percent, row.available)})
    assert [(event.kind, event.channel) for event in events] == [("restored", channel)]
    limits = rate_limits.load_rate_limits()
    assert limits is not None
    assert (limits.five_hour_pct if window == "five_hour" else limits.seven_day_pct) == 0


def test_status_json_collects_single_window(status_path: Path) -> None:
    status_path.write_text(json.dumps({"rate_limits": {
        "seven_day": {"used_percentage": 46, "resets_at": NOW.timestamp() + 7200},
    }}), encoding="utf-8")
    quota = status_projection._collect_claude_quota()
    assert quota is not None
    assert quota["weekly"]["percent"] == 46
    assert quota["session"]["percent"] is None
