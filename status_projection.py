# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Neutral status projection emitting a versioned schema for scripts and tools.

Scripts and schedulers need machine-readable status without parsing TUI or doctor
text. This module provides a versioned JSON projection of provider quotas, data
health, and update timestamps, redacting sensitive user details, paths, tokens,
and prompts by default.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import time
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, cast

import provider_health
import provider_probe
from i18n import packaged_resource_path

SCHEMA_VERSION = 1

# Patterns for sensitive tokens and credentials
_TOKEN_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"ya29\.[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
]

# Patterns for file paths (Windows and POSIX)
_PATH_PATTERNS = [
    re.compile(r"[a-zA-Z]:\\[^\"'\s\n\r<>,;]+"),
    re.compile(r"/(?:Users|home|var|tmp)/[^\"'\s\n\r<>,;]+"),
    re.compile(r"~[/\\][^\"'\s\n\r<>,;]+"),
]


def _user_names() -> set[str]:
    names: set[str] = set()
    try:
        current_user = getpass.getuser()
        if len(current_user) >= 2:
            names.add(current_user)
    except Exception:
        pass
    for var in ("USERNAME", "USER", "LOGNAME"):
        val = os.environ.get(var)
        if val and len(val) >= 2:
            names.add(val)
    try:
        home_name = Path.home().name
        if len(home_name) >= 2:
            names.add(home_name)
    except Exception:
        pass
    return names


def redact_text(text: str) -> str:
    """Mask user names, file paths, and secret tokens in human-readable details."""
    if not text:
        return text

    redacted = text
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub("[REDACTED_TOKEN]", redacted)

    for pattern in _PATH_PATTERNS:
        redacted = pattern.sub("[REDACTED_PATH]", redacted)

    for user in _user_names():
        if user in redacted:
            redacted = redacted.replace(user, "[REDACTED_USER]")

    return redacted


def redact_data(data: Any) -> Any:
    """Recursively scrub strings and dictionary values against leaks."""
    if isinstance(data, str):
        return redact_text(data)
    if isinstance(data, Mapping):
        return {str(k): redact_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_data(v) for v in data]
    if isinstance(data, tuple):
        return tuple(redact_data(v) for v in data)
    return data


def _current_version() -> str:
    try:
        return metadata.version("agentdeck")
    except metadata.PackageNotFoundError:
        pyproject = packaged_resource_path(
            "pyproject.toml", Path(__file__).with_name("pyproject.toml")
        )
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            version = data.get("project", {}).get("version")
            if isinstance(version, str):
                return version
        except OSError:
            pass
    return "unknown"


def _collect_claude_quota(*, mock: bool = False) -> dict[str, Any] | None:
    import usage_client

    if mock:
        client = usage_client.ClaudeUsageClient(mock=True)
        outcome = client._mock_outcome()
        snapshot = outcome.snapshot
        if snapshot:
            return {
                "session": {
                    "percent": snapshot.current_percent,
                    "reset_at": snapshot.current_reset_at,
                    "status": snapshot.current_status,
                },
                "weekly": {
                    "percent": snapshot.weekly_percent,
                    "reset_at": snapshot.weekly_reset_at,
                    "status": snapshot.current_status,
                },
                "data_source": snapshot.data_source,
                "is_stale": snapshot.is_stale,
            }
        return None

    try:
        result = usage_client._read_status_file()
        snapshot = None
        if result is not None:
            data, source_path, _ = result
            if usage_client._has_complete_rate_limits(data):
                snapshot = usage_client._build_snapshot(
                    data, data_source=usage_client._source_from_path(source_path)
                )

        if snapshot is None:
            c_json = usage_client._read_claude_json_snapshot()
            c_desk = usage_client._read_desktop_usage_snapshot()
            snapshot = usage_client._newest_snapshot(c_json, c_desk)

        if snapshot is not None:
            return {
                "session": {
                    "percent": snapshot.current_percent,
                    "reset_at": snapshot.current_reset_at,
                    "status": snapshot.current_status,
                },
                "weekly": {
                    "percent": snapshot.weekly_percent,
                    "reset_at": snapshot.weekly_reset_at,
                    "status": snapshot.current_status,
                },
                "data_source": snapshot.data_source,
                "is_stale": snapshot.is_stale,
            }
    except Exception:
        pass
    return None


def _collect_codex_quota(*, mock: bool = False) -> dict[str, Any] | None:
    if mock:
        now = time.time()
        return {
            "session": {
                "percent": 12.0,
                "reset_at": now + 4 * 3600,
                "window_minutes": 300.0,
            },
            "weekly": {
                "percent": 28.0,
                "reset_at": now + 4 * 86400,
                "window_minutes": 10080.0,
            },
            "model": "gpt-5",
            "credits": {
                "balance": None,
                "unlimited": False,
            },
        }

    try:
        from providers import codex_loader

        rate_limits = codex_loader.load_rate_limits()
        if rate_limits is not None:
            return {
                "session": {
                    "percent": rate_limits.five_hour_pct,
                    "reset_at": rate_limits.five_hour_resets_at,
                    "window_minutes": rate_limits.five_hour_window_minutes,
                },
                "weekly": {
                    "percent": rate_limits.seven_day_pct,
                    "reset_at": rate_limits.seven_day_resets_at,
                    "window_minutes": rate_limits.seven_day_window_minutes,
                },
                "model": rate_limits.model or "unknown",
                "credits": {
                    "balance": rate_limits.credit_balance,
                    "unlimited": rate_limits.credits_unlimited,
                },
            }
    except Exception:
        pass
    return None


def _collect_antigravity_quota(*, mock: bool = False) -> dict[str, Any] | None:
    if mock:
        return {
            "group_name": "gemini",
            "session": {
                "percent": 30.0,
                "remaining_percent": 70.0,
                "resets_in": "3h 45m",
                "resets_in_minutes": 225,
            },
            "weekly": {
                "percent": 50.0,
                "remaining_percent": 50.0,
                "resets_in": "5d 2h",
                "resets_in_minutes": 7320,
            },
        }

    try:
        from providers import agy_quota_probe

        cached = agy_quota_probe._read_cache()
        if cached is not None and cached.groups:
            selected = next(
                (group for group in cached.groups if "gemini" in group.name.lower()),
                cached.groups[0],
            )
            five_hour_pct = (
                round(100.0 - selected.five_hour.remaining_percent, 1)
                if selected.five_hour.remaining_percent is not None
                else None
            )
            weekly_pct = (
                round(100.0 - selected.weekly.remaining_percent, 1)
                if selected.weekly.remaining_percent is not None
                else None
            )
            return {
                "group_name": selected.name,
                "session": {
                    "percent": five_hour_pct,
                    "remaining_percent": selected.five_hour.remaining_percent,
                    "resets_in": selected.five_hour.resets_in,
                    "resets_in_minutes": selected.five_hour.resets_in_minutes,
                },
                "weekly": {
                    "percent": weekly_pct,
                    "remaining_percent": selected.weekly.remaining_percent,
                    "resets_in": selected.weekly.resets_in,
                    "resets_in_minutes": selected.weekly.resets_in_minutes,
                },
            }
    except Exception:
        pass
    return None


def build_status_payload(
    *,
    now: float | None = None,
    mock: bool = False,
    healths: list[provider_health.ProviderHealth] | None = None,
) -> dict[str, Any]:
    """Assemble the neutral, versioned status dictionary."""
    current_time = time.time() if now is None else now

    if healths is None:
        if mock:
            healths = [
                provider_health.ProviderHealth(
                    provider="claude",
                    state=provider_health.HealthState.READY,
                    reason_key="health_claude_ready",
                    last_updated=current_time - 120,
                ),
                provider_health.ProviderHealth(
                    provider="codex",
                    state=provider_health.HealthState.READY,
                    reason_key="health_codex_ready",
                    last_updated=current_time - 180,
                ),
                provider_health.ProviderHealth(
                    provider="antigravity",
                    state=provider_health.HealthState.READY,
                    reason_key="health_agy_ready",
                    last_updated=current_time - 300,
                ),
            ]
        else:
            try:
                healths = provider_probe.collect_provider_health(now=current_time)
            except Exception as exc:
                healths = [
                    provider_health.ProviderHealth(
                        provider="claude",
                        state=provider_health.HealthState.ERROR,
                        reason_key="health_claude_error",
                        detail=str(exc),
                    )
                ]

    health_by_provider = {h.provider: h for h in healths}

    claude_quota = _collect_claude_quota(mock=mock)
    codex_quota = _collect_codex_quota(mock=mock)
    agy_quota = _collect_antigravity_quota(mock=mock)

    providers_payload: dict[str, dict[str, Any]] = {}

    for name, quota in (
        ("claude", claude_quota),
        ("codex", codex_quota),
        ("antigravity", agy_quota),
    ):
        h = health_by_provider.get(name)
        health_payload: dict[str, Any]
        if h is not None:
            health_payload = {
                "state": str(h.state),
                "usable": h.is_usable,
                "reason_key": h.reason_key,
                "next_step_key": h.next_step_key,
                "last_updated": h.last_updated,
                "detail": h.detail,
            }
            updated_at = h.last_updated
        else:
            health_payload = {
                "state": str(provider_health.HealthState.MISSING),
                "usable": False,
                "reason_key": "health_unknown",
                "next_step_key": None,
                "last_updated": None,
                "detail": "",
            }
            updated_at = None

        providers_payload[name] = {
            "health": health_payload,
            "quota": quota,
            "updated_at": updated_at,
        }

    raw_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "app_version": _current_version(),
        "generated_at": datetime.fromtimestamp(current_time, tz=UTC).isoformat(),
        "timestamp": current_time,
        "providers": providers_payload,
    }

    return cast(dict[str, Any], redact_data(raw_payload))


def render_json(*, indent: int = 2, mock: bool = False) -> str:
    """Format the neutral status projection as a JSON string."""
    payload = build_status_payload(mock=mock)
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def render_text(*, mock: bool = False) -> str:
    """Render a concise, human-readable summary for console inspection."""
    payload = build_status_payload(mock=mock)
    lines: list[str] = [
        f"agentdeck status (schema v{payload['schema_version']}, app v{payload['app_version']})",
        "-" * 40,
    ]
    for provider, data in payload.get("providers", {}).items():
        health = data.get("health", {})
        quota = data.get("quota")
        state_str = f"[{health.get('state', 'unknown')}]"
        quota_summary: list[str] = []
        if quota:
            session = quota.get("session")
            if session and session.get("percent") is not None:
                quota_summary.append(f"session: {session['percent']}%")
            weekly = quota.get("weekly")
            if weekly and weekly.get("percent") is not None:
                quota_summary.append(f"weekly: {weekly['percent']}%")
        quota_str = ", ".join(quota_summary) if quota_summary else "no quota"
        lines.append(f"{provider:<14} {state_str:<12} {quota_str}")
    return "\n".join(lines) + "\n"
