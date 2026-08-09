# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from collections.abc import Mapping

from prefs import _load_preferences, _save_preferences
from state.autoresume import (
    DEFAULT_LEAD_SECONDS,
    DEFAULT_TRIGGER_PCT,
    DEFAULT_WEEKLY_CEILING_PCT,
    AutoResumeConfig,
)

DEFAULT_QUOTA_CARD_ORDER = ("claude", "codex", "agy")


def _resolved_preferences(prefs: Mapping[str, object] | None = None) -> Mapping[str, object]:
    return _load_preferences() if prefs is None else prefs


def _auto_update_check_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    data = _resolved_preferences(prefs)
    return data.get("auto_update_check") is not False


def _hide_claude_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    data = _resolved_preferences(prefs)
    return data.get("hide_claude_section") is True


def _hide_codex_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    data = _resolved_preferences(prefs)
    return data.get("hide_codex_section") is True


def _hide_agy_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    data = _resolved_preferences(prefs)
    return data.get("hide_agy_section") is True


def _quota_card_order(prefs: Mapping[str, object] | None = None) -> tuple[str, ...]:
    data = _resolved_preferences(prefs)
    order = _valid_quota_card_order(data.get("quota_card_order"))
    return DEFAULT_QUOTA_CARD_ORDER if order is None else order


def _save_quota_card_order(order: object) -> bool:
    valid_order = _valid_quota_card_order(order)
    if valid_order is None:
        return False
    prefs = _load_preferences()
    prefs["quota_card_order"] = list(valid_order)
    _save_preferences(prefs)
    return True


def _valid_quota_card_order(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or len(value) != len(DEFAULT_QUOTA_CARD_ORDER):
        return None
    if any(not isinstance(card, str) for card in value):
        return None
    order = tuple(value)
    if set(order) != set(DEFAULT_QUOTA_CARD_ORDER):
        return None
    return order


def _quota_notifications_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    data = _resolved_preferences(prefs)
    return data.get("quota_notifications") is not False


def _window_keeper_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    # Defaults OFF (opt-in) — opposite polarity from quota_notifications, which
    # is why this is `is True` rather than `is not False`.
    data = _resolved_preferences(prefs)
    return data.get("window_keeper") is True or data.get("agy_window_keeper") is True


def _agy_window_keeper_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    return _window_keeper_enabled(prefs)


def _auto_resume_enabled(prefs: Mapping[str, object] | None = None) -> bool:
    # Defaults OFF: this one starts an unattended Claude run on its own, so it has to
    # be asked for rather than inherited by anyone who updates.
    data = _resolved_preferences(prefs)
    return data.get("auto_resume") is True


def _auto_resume_config(prefs: Mapping[str, object] | None = None) -> AutoResumeConfig:
    data = _resolved_preferences(prefs)
    return AutoResumeConfig(
        enabled=_auto_resume_enabled(data),
        trigger_pct=_percentage(data.get("auto_resume_trigger_pct"), DEFAULT_TRIGGER_PCT),
        weekly_ceiling_pct=_percentage(
            data.get("auto_resume_weekly_ceiling_pct"), DEFAULT_WEEKLY_CEILING_PCT
        ),
        lead_seconds=_lead_seconds(data.get("auto_resume_lead_seconds")),
    )


def _percentage(value: object, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return fallback
    return float(value) if 0 < float(value) <= 100 else fallback


def _lead_seconds(value: object) -> int:
    # A negative lead would fire before the quota actually rolls over, which is the
    # one thing the buffer exists to prevent.
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_LEAD_SECONDS
    return value if 0 <= value <= 3600 else DEFAULT_LEAD_SECONDS


def _quota_notification_thresholds(prefs: Mapping[str, object] | None = None) -> list[float]:
    data = _resolved_preferences(prefs)
    raw = data.get("quota_notification_thresholds")
    if not isinstance(raw, list):
        return [90.0]
    thresholds: list[float] = []
    for value in raw:
        if isinstance(value, int | float) and 0 < float(value) <= 100:
            thresholds.append(float(value))
    return thresholds or [90.0]
