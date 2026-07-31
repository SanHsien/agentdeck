# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from typing import Any

import pytest

import doctor
import provider_health
import provider_probe
from panels.payload import _health_payload


def _fake(now: float) -> list[provider_health.ProviderHealth]:
    return [
        provider_health.claude_health(
            hook_installed=True, status_file_exists=True, last_updated=now - 60, now=now
        ),
        provider_health.codex_health(
            sessions_dir_exists=True, session_count=2, last_updated=now - 9999, now=now
        ),
        provider_health.antigravity_health(
            enabled=False, credentials_found=False, last_updated=None, now=now
        ),
    ]


def test_the_panel_and_the_doctor_read_the_same_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One collector is the whole point.

    Both surfaces used to reach the same files through separate code, which is
    how they drifted into describing one situation two different ways. Patching
    the collector must move both, or they can drift again.
    """
    calls: list[str] = []

    def collect(*, now: float) -> list[provider_health.ProviderHealth]:
        calls.append("collected")
        return _fake(now)

    monkeypatch.setattr(provider_probe, "collect_provider_health", collect)

    report = doctor.render()
    panel = _health_payload("en")

    assert len(calls) == 2, "one of the two surfaces bypassed the shared collector"
    # The same three verdicts, in both places.
    assert "claude       [ready]" in report
    assert "codex        [stale]" in report
    assert panel["claude"]["state"] == "ready"
    assert panel["codex"]["state"] == "stale"
    assert panel["antigravity"]["state"] == "misconfigured"


def test_the_panel_shows_a_next_step_exactly_when_there_is_something_to_do(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(provider_probe, "collect_provider_health",
                        lambda *, now: _fake(now))

    panel = _health_payload("en")

    # A healthy provider with a "next step" would be telling the user to fix
    # something that is not broken.
    assert panel["claude"]["nextStep"] == ""
    assert panel["codex"]["nextStep"]
    assert panel["antigravity"]["nextStep"]


def test_a_collector_failure_still_renders_both_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health is a diagnostic. It must never be the reason a panel goes blank."""
    def boom(*, now: float) -> Any:
        raise OSError("disk gone")

    monkeypatch.setattr(provider_probe, "collect_provider_health", boom)

    assert _health_payload("en") == {}
    assert "provider health:" in doctor.render()


def test_the_probe_reports_all_three_providers_against_the_real_machine() -> None:
    """The collector is the only place doing IO, so its shape is worth pinning."""
    healths = provider_probe.collect_provider_health(now=2_000_000_000.0)

    assert [health.provider for health in healths] == ["claude", "codex", "antigravity"]
    for health in healths:
        assert isinstance(health.state, provider_health.HealthState)
        assert health.reason_key.startswith("health_")
