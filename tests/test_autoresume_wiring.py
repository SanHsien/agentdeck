# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Preferences, the tray tick, and the handoff the resumed run is given."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

import autoresume_runner as runner
import autoresume_scheduler as scheduler
from adapters.types import RateLimits, ResumeTarget
from state.autoresume import (
    DEFAULT_LEAD_SECONDS,
    DEFAULT_TRIGGER_PCT,
    DEFAULT_WEEKLY_CEILING_PCT,
)
from state.menubar_prefs import _auto_resume_config, _auto_resume_enabled

# Relative to the real clock on purpose. tick() reads datetime.now() itself, so
# a fixed date here is a time bomb: these tests passed on the day they were
# written and went red a day later with no code change, because NOW + 3600 had
# become the past and the scheduler correctly refused to schedule into it.
# Every use below is an offset from "now", which is what the cases actually mean.
NOW = int(datetime.now(UTC).timestamp())


# --------------------------------------------------------------------------- prefs


def test_auto_resume_is_off_unless_asked_for() -> None:
    # It starts an unattended Claude run, so no one may inherit it by upgrading.
    assert _auto_resume_enabled({}) is False
    assert _auto_resume_enabled({"auto_resume": "yes"}) is False
    assert _auto_resume_enabled({"auto_resume": True}) is True


def test_config_falls_back_to_defaults_for_junk_values() -> None:
    config = _auto_resume_config(
        {
            "auto_resume": True,
            "auto_resume_trigger_pct": "high",
            "auto_resume_weekly_ceiling_pct": 0,
            "auto_resume_lead_seconds": -30,
        }
    )

    assert config.trigger_pct == DEFAULT_TRIGGER_PCT
    assert config.weekly_ceiling_pct == DEFAULT_WEEKLY_CEILING_PCT
    assert config.lead_seconds == DEFAULT_LEAD_SECONDS


def test_config_accepts_valid_overrides() -> None:
    config = _auto_resume_config(
        {
            "auto_resume": True,
            "auto_resume_trigger_pct": 80,
            "auto_resume_weekly_ceiling_pct": 95.5,
            "auto_resume_lead_seconds": 600,
        }
    )

    assert (config.trigger_pct, config.weekly_ceiling_pct, config.lead_seconds) == (
        80.0,
        95.5,
        600,
    )


def test_booleans_are_not_accepted_as_numbers() -> None:
    # bool is an int subclass; without an explicit guard `True` becomes 1%.
    config = _auto_resume_config(
        {"auto_resume": True, "auto_resume_trigger_pct": True, "auto_resume_lead_seconds": True}
    )

    assert config.trigger_pct == DEFAULT_TRIGGER_PCT
    assert config.lead_seconds == DEFAULT_LEAD_SECONDS


# ---------------------------------------------------------------------------- tick


class _FakeIcon:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, str]] = []

    def notify(self, body: str, title: str) -> None:
        self.notifications.append((title, body))


@pytest.fixture(autouse=True)
def _clean_registration() -> None:
    scheduler.reset_registration_cache()


def _arrange(
    monkeypatch: pytest.MonkeyPatch,
    *,
    five_pct: float = 99.0,
    resets_at: int | None = NOW + 3600,
    enabled: bool = True,
) -> tuple[list[datetime], list[int]]:
    scheduled: list[datetime] = []
    cancelled: list[int] = []

    monkeypatch.setattr(
        scheduler,
        "load_rate_limits",
        lambda: RateLimits(
            five_hour_pct=five_pct, five_hour_resets_at=resets_at, seven_day_pct=10.0
        ),
    )
    monkeypatch.setattr(
        scheduler,
        "load_resume_target",
        lambda: ResumeTarget("abc-123", "C:/work", "C:/logs/abc.jsonl"),
    )
    monkeypatch.setattr(
        scheduler, "_auto_resume_config", lambda: _auto_resume_config({"auto_resume": enabled})
    )

    def record_schedule(run_at: datetime) -> bool:
        scheduled.append(run_at)
        return True

    def record_cancel() -> bool:
        cancelled.append(1)
        return True

    monkeypatch.setattr(scheduler, "take_result", lambda: None)
    monkeypatch.setattr(scheduler, "schedule", record_schedule)
    monkeypatch.setattr(scheduler, "cancel", record_cancel)
    return scheduled, cancelled


def test_repeated_ticks_do_not_re_register_an_unchanged_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tray ticks every refresh; schtasks must not be invoked every minute."""
    scheduled, _ = _arrange(monkeypatch)
    icon = _FakeIcon()

    for _ in range(5):
        scheduler.tick(icon, "en")

    assert len(scheduled) == 1


def test_a_moved_reset_time_re_registers(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduled, _ = _arrange(monkeypatch, resets_at=NOW + 3600)
    scheduler.tick(_FakeIcon(), "en")

    _arrange(monkeypatch, resets_at=NOW + 7200)
    scheduler.tick(_FakeIcon(), "en")

    assert len(scheduled) == 1  # the second arrange installed a fresh recorder


def test_cancel_is_not_called_when_nothing_is_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, cancelled = _arrange(monkeypatch, enabled=False)

    scheduler.tick(_FakeIcon(), "en")

    assert cancelled == []


def test_cancel_runs_once_after_a_schedule_is_withdrawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _arrange(monkeypatch)
    scheduler.tick(_FakeIcon(), "en")

    _, cancelled = _arrange(monkeypatch, five_pct=10.0)
    scheduler.tick(_FakeIcon(), "en")
    scheduler.tick(_FakeIcon(), "en")

    assert len(cancelled) == 1


def test_a_finished_run_is_announced_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, five_pct=10.0)
    results = [{"session_id": "abc-123", "exit_code": 0}, None]
    monkeypatch.setattr(scheduler, "take_result", lambda: results.pop(0))
    icon = _FakeIcon()

    scheduler.tick(icon, "en")
    scheduler.tick(icon, "en")

    assert len(icon.notifications) == 1
    assert "resume" in icon.notifications[0][0].lower()


def test_a_failed_run_is_announced_differently(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, five_pct=10.0)
    monkeypatch.setattr(scheduler, "take_result", lambda: {"exit_code": 1})
    icon = _FakeIcon()

    scheduler.tick(icon, "en")

    ok_icon = _FakeIcon()
    monkeypatch.setattr(scheduler, "take_result", lambda: {"exit_code": 0})
    scheduler.reset_registration_cache()
    scheduler.tick(ok_icon, "en")

    assert icon.notifications[0] != ok_icon.notifications[0]


def test_tick_survives_an_icon_that_cannot_notify(monkeypatch: pytest.MonkeyPatch) -> None:
    _arrange(monkeypatch, five_pct=10.0)
    monkeypatch.setattr(scheduler, "take_result", lambda: {"exit_code": 0})

    scheduler.tick(object(), "en")  # must not raise


# ------------------------------------------------------------------- result file


def test_result_is_read_once_and_cleared(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "autoresume-result.json"
    monkeypatch.setattr(scheduler, "RESULT_PATH", path)

    scheduler.write_result("abc-123", 0)
    first = scheduler.take_result()
    second = scheduler.take_result()

    assert first is not None
    assert first["session_id"] == "abc-123"
    assert first["exit_code"] == 0
    assert second is None


def test_a_corrupt_result_file_is_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "autoresume-result.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(scheduler, "RESULT_PATH", path)

    assert scheduler.take_result() is None


# --------------------------------------------------------------------- handoff


def _transcript(tmp_path: Path) -> Path:
    path = tmp_path / "session.jsonl"
    lines = [
        {
            "type": "user",
            "message": {"content": "fix the login redirect"},
            "timestamp": "2026-08-09T09:00:00Z",
        },
        {
            "type": "assistant",
            "timestamp": "2026-08-09T09:05:00Z",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": 'git commit -m "fix redirect loop"'},
                    },
                    {
                        "type": "tool_use",
                        "name": "TodoWrite",
                        "input": {
                            "todos": [{"status": "pending", "content": "add a regression test"}]
                        },
                    },
                ]
            },
        },
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return path


def test_handoff_carries_the_request_commit_and_todo(tmp_path: Path) -> None:
    target = ResumeTarget("abc", str(tmp_path), str(_transcript(tmp_path)))

    handoff = runner.build_handoff(target)

    assert "fix the login redirect" in handoff
    assert "fix redirect loop" in handoff
    assert "add a regression test" in handoff


def test_handoff_is_empty_without_a_transcript_path(tmp_path: Path) -> None:
    assert runner.build_handoff(ResumeTarget("abc", str(tmp_path))) == ""


def test_handoff_is_empty_when_the_transcript_is_missing(tmp_path: Path) -> None:
    target = ResumeTarget("abc", str(tmp_path), str(tmp_path / "absent.jsonl"))

    assert runner.build_handoff(target) == ""


def test_run_resume_stops_before_launching_when_nothing_is_resumable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A resume with no target must not fall through to spawning claude.
    monkeypatch.setattr(runner, "LOG_PATH", tmp_path / "log.txt")
    monkeypatch.setattr(runner, "load_resume_target", lambda: None)
    monkeypatch.setattr(scheduler, "cancel", lambda: True)

    def explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("claude must not be started")

    monkeypatch.setattr(subprocess, "run", explode)

    assert runner.run_resume() == 1


def test_run_resume_clears_the_task_even_when_it_aborts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed resume must not leave a trigger armed for the next reset."""
    cancelled: list[int] = []

    def record_cancel() -> bool:
        cancelled.append(1)
        return True

    monkeypatch.setattr(runner, "LOG_PATH", tmp_path / "log.txt")
    monkeypatch.setattr(runner, "load_resume_target", lambda: None)
    monkeypatch.setattr(scheduler, "cancel", record_cancel)

    runner.run_resume()

    assert cancelled == [1]
