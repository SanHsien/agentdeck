from __future__ import annotations

import time
from typing import Any

import pytest

import update_checker
import update_gate


def test_auto_check_is_due_for_missing_or_invalid_timestamp() -> None:
    assert update_gate.auto_check_is_due({}) is True
    assert update_gate.auto_check_is_due({"last_update_check": {"checked_at": "bad"}}) is True


def test_auto_check_is_due_only_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 1_700_000_000.0
    monkeypatch.setattr("update_gate.time.time", lambda: now)

    assert update_gate.auto_check_is_due(
        {"last_update_check": {"checked_at": now - update_gate.AUTO_CHECK_TTL_SECONDS + 1}},
    ) is False
    assert update_gate.auto_check_is_due(
        {"last_update_check": {"checked_at": now - update_gate.AUTO_CHECK_TTL_SECONDS}},
    ) is True


def test_stale_cache_reset_updates_after_upgrade() -> None:
    prefs: dict[str, Any] = {
        "last_update_check": {
            "checked_at": 1700000000.0,
            "current_version": "0.14.3",
            "latest_version": "0.15.0",
            "release_url": "https://x/v0.15.0",
        }
    }

    result = update_gate.stale_cache_reset(prefs, "0.15.0")

    assert result == {
        "checked_at": 1700000000.0,
        "current_version": "0.15.0",
        "latest_version": "0.15.0",
        "release_url": "https://x/v0.15.0",
    }


def test_stale_cache_reset_returns_none_for_pending_update() -> None:
    prefs: dict[str, Any] = {
        "last_update_check": {
            "checked_at": 1700000000.0,
            "current_version": "0.15.0",
            "latest_version": "0.16.0",
            "release_url": "https://x/v0.16.0",
        }
    }

    assert update_gate.stale_cache_reset(prefs, "0.15.0") is None


def test_build_check_cache_entry_with_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("update_gate.time.time", lambda: 1700000000.0)

    result = update_gate.build_check_cache_entry(
        "0.11.3",
        update_checker.ReleaseInfo(version="0.12.0", html_url="https://x/v0.12.0"),
    )

    assert result == {
        "checked_at": 1700000000.0,
        "current_version": "0.11.3",
        "latest_version": "0.12.0",
        "release_url": "https://x/v0.12.0",
    }


def test_build_check_cache_entry_without_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("update_gate.time.time", lambda: 1700000000.0)

    result = update_gate.build_check_cache_entry("0.11.3", None)

    assert result == {
        "checked_at": 1700000000.0,
        "current_version": "0.11.3",
        "latest_version": "0.11.3",
        "release_url": None,
    }


@pytest.mark.parametrize(
    ("result_code", "expected"),
    [
        (1000, ("open", {})),
        (1002, ("skip", {"update_skipped_version": "0.12.0"})),
        (999, ("dismiss", {})),
    ],
)
def test_resolve_alert_choice(
    result_code: int,
    expected: tuple[str, dict[str, str]],
) -> None:
    assert update_gate.resolve_alert_choice(result_code, "0.12.0") == expected


@pytest.mark.parametrize(
    ("code", "expected_action", "expected_prefs"),
    [
        (update_gate.IDYES, "open", {}),
        (update_gate.IDNO, "skip", {"update_skipped_version": "1.2.3"}),
        (update_gate.IDCANCEL, "dismiss", {}),
        (0, "dismiss", {}),  # Windows returns 0 when the box cannot be shown
        (99, "dismiss", {}),  # undocumented code
    ],
)
def test_resolve_message_box_choice(
    code: int, expected_action: str, expected_prefs: dict[str, str]
) -> None:
    # Escape and the close button both return IDCANCEL, so anything that is not an
    # explicit No must defer. Skipping on an accidental dismissal would hide the
    # release for good.
    assert update_gate.resolve_message_box_choice(code, "1.2.3") == (
        expected_action,
        expected_prefs,
    )


def test_dismissed_recently_window() -> None:
    now = time.time()

    assert update_gate.dismissed_recently({"update_dismissed_at": now}) is True
    assert (
        update_gate.dismissed_recently(
            {"update_dismissed_at": now - update_gate.UPDATE_DISMISS_SECONDS - 1}
        )
        is False
    )


@pytest.mark.parametrize("value", [None, "", "not-a-number", {}, []])
def test_dismissed_recently_ignores_unusable_values(value: object) -> None:
    # A corrupt preferences file must not suppress update prompts forever.
    assert update_gate.dismissed_recently({"update_dismissed_at": value}) is False


def test_should_prompt_respects_skip_and_dismissal() -> None:
    assert update_gate.should_prompt({}, "1.2.3") is True
    assert update_gate.should_prompt({"update_skipped_version": "1.2.3"}, "1.2.3") is False
    # A skip applies to that version only; a newer one must still prompt.
    assert update_gate.should_prompt({"update_skipped_version": "1.2.2"}, "1.2.3") is True
    assert (
        update_gate.should_prompt({"update_dismissed_at": time.time()}, "1.2.3") is False
    )
