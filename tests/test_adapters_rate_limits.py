# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adapters import rate_limits


def _write_status(path: Path, body: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")


def test_load_rate_limits_skips_bad_utf8_status_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    status_path.write_bytes(b"\xff\xfe not utf-8\n")
    monkeypatch.setattr(rate_limits, "STATUS_FILE", str(status_path))
    monkeypatch.setattr(rate_limits, "LEGACY_STATUS_FILE", str(tmp_path / "missing-legacy.json"))
    monkeypatch.setattr(rate_limits, "TT_STATUS_FILE", str(tmp_path / "missing-tt.json"))

    assert rate_limits.load_rate_limits() is None


def test_load_rate_limits_accepts_numeric_string_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    _write_status(
        status_path,
        {
            "rate_limits": {
                "five_hour": {"used_percentage": "25", "resets_at": "9999999999"},
                "seven_day": {"used_percentage": "70.0", "resets_at": "9999999998"},
            },
            "model": {"display_name": "Claude Test"},
            "_received_at": "2026-05-31T00:00:00Z",
        },
    )
    monkeypatch.setattr(rate_limits, "STATUS_FILE", str(status_path))
    monkeypatch.setattr(rate_limits, "LEGACY_STATUS_FILE", str(tmp_path / "missing-legacy.json"))
    monkeypatch.setattr(rate_limits, "TT_STATUS_FILE", str(tmp_path / "missing-tt.json"))

    result = rate_limits.load_rate_limits()

    assert result is not None
    assert result.five_hour_pct == 25.0
    assert result.five_hour_resets_at == 9999999999
    assert result.seven_day_pct == 70.0
    assert result.seven_day_resets_at == 9999999998
    assert result.model == "Claude Test"
    assert result.updated_at == "2026-05-31T00:00:00Z"


def test_load_rate_limits_clears_expired_percentage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    now_ts = datetime.now(UTC).timestamp()
    _write_status(
        status_path,
        {
            "rate_limits": {
                "five_hour": {"used_percentage": "25", "resets_at": str(now_ts - 60)},
                "seven_day": {"used_percentage": "70", "resets_at": str(now_ts + 60)},
            }
        },
    )
    monkeypatch.setattr(rate_limits, "STATUS_FILE", str(status_path))
    monkeypatch.setattr(rate_limits, "LEGACY_STATUS_FILE", str(tmp_path / "missing-legacy.json"))
    monkeypatch.setattr(rate_limits, "TT_STATUS_FILE", str(tmp_path / "missing-tt.json"))

    result = rate_limits.load_rate_limits()

    assert result is not None
    assert result.five_hour_pct == 0.0
    assert result.five_hour_resets_at == int(now_ts - 60)
    assert result.seven_day_pct == 70.0


def _point_at(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status_path: Path) -> None:
    monkeypatch.setattr(rate_limits, "STATUS_FILE", str(status_path))
    monkeypatch.setattr(rate_limits, "LEGACY_STATUS_FILE", str(tmp_path / "missing-legacy.json"))
    monkeypatch.setattr(rate_limits, "TT_STATUS_FILE", str(tmp_path / "missing-tt.json"))


def test_load_resume_target_reads_the_session_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    _write_status(
        status_path,
        {
            "session_id": "abc-123",
            "cwd": "C:/work/project",
            "transcript_path": "C:/logs/abc-123.jsonl",
        },
    )
    _point_at(monkeypatch, tmp_path, status_path)

    target = rate_limits.load_resume_target()

    assert target is not None
    assert target.session_id == "abc-123"
    assert target.cwd == "C:/work/project"
    assert target.transcript_path == "C:/logs/abc-123.jsonl"


def test_load_resume_target_tolerates_a_missing_transcript_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    _write_status(status_path, {"session_id": "abc-123", "cwd": "C:/work/project"})
    _point_at(monkeypatch, tmp_path, status_path)

    target = rate_limits.load_resume_target()

    assert target is not None
    assert target.transcript_path == ""


def test_load_resume_target_rejects_a_status_without_a_working_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    _write_status(status_path, {"session_id": "abc-123"})
    _point_at(monkeypatch, tmp_path, status_path)

    assert rate_limits.load_resume_target() is None


def test_load_resume_target_rejects_non_string_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "agentdeck-status.json"
    _write_status(status_path, {"session_id": 123, "cwd": ["C:/work"]})
    _point_at(monkeypatch, tmp_path, status_path)

    assert rate_limits.load_resume_target() is None


def test_load_resume_target_returns_none_without_a_status_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _point_at(monkeypatch, tmp_path, tmp_path / "absent.json")

    assert rate_limits.load_resume_target() is None
