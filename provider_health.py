# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""One vocabulary for "is this provider's data any good right now?".

Claude, Codex and Antigravity each learned to describe themselves separately,
and they disagreed about everything: Codex called data old after 15 minutes and
Antigravity after 20, one returned ``None`` for healthy while another returned a
dict, and ``--doctor`` printed a third set of phrases that the panels never
showed. A user seeing ``--`` had no way to tell "you have never run this tool"
from "the file is there but ancient" from "the query failed".

Everything here is a pure projection: callers pass in facts they have already
gathered, and get back a state plus the two things a user actually needs — why,
and what to do next. No IO, so every branch is testable without a provider
installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthState(StrEnum):
    """Why a provider's numbers are, or are not, on screen.

    The order matters: these are listed worst-last, and `worst_of` relies on it
    to summarise several providers into one badge.
    """

    READY = "ready"
    """Data is present and recent enough to trust."""

    STALE = "stale"
    """Data is real but older than this provider's refresh window."""

    MISSING = "missing"
    """Nothing to read yet — the tool has not been used on this machine."""

    MISCONFIGURED = "misconfigured"
    """The tool is in use but agentdeck is not wired to it: hook not installed,
    CLI not logged in, feature switched off."""

    UNAVAILABLE = "unavailable"
    """A remote the provider depends on is temporarily refusing to answer."""

    ERROR = "error"
    """Reading local state failed in a way that is not one of the above."""


_SEVERITY = {
    HealthState.READY: 0,
    HealthState.STALE: 1,
    HealthState.MISSING: 2,
    HealthState.MISCONFIGURED: 3,
    HealthState.UNAVAILABLE: 4,
    HealthState.ERROR: 5,
}

# Kept per provider rather than unified into one number: these are refresh
# cadences, not a policy choice. Codex writes on every turn, Antigravity is
# polled on a timer, and flattening them would either cry stale on a healthy
# Antigravity or stay quiet on a Codex session that died ten minutes ago.
STALE_AFTER_SECONDS = {
    "claude": 15 * 60,
    "codex": 15 * 60,
    "antigravity": 20 * 60,
}


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """A provider's state plus what to tell the user about it.

    ``reason_key`` and ``next_step_key`` are i18n keys, never prose: the panels
    and ``--doctor`` render them through the same lookup, which is what stops
    the UI and the CLI drifting apart again. ``detail`` carries specifics that
    must not be translated, such as a path or a count.
    """

    provider: str
    state: HealthState
    reason_key: str
    next_step_key: str | None = None
    last_updated: float | None = None
    detail: str = ""

    @property
    def is_usable(self) -> bool:
        """Whether numbers can be shown at all, even if they are old."""
        return self.state in (HealthState.READY, HealthState.STALE)

    def age_seconds(self, now: float) -> float | None:
        if self.last_updated is None:
            return None
        return max(0.0, now - self.last_updated)


def _freshness(
    provider: str,
    last_updated: float | None,
    now: float,
    *,
    ready_key: str,
    stale_key: str,
    stale_fix_key: str,
    missing_key: str,
    missing_fix_key: str,
) -> ProviderHealth:
    """Every i18n key is passed in, never built from the provider name.

    Interpolating them (``f"health_{provider}_missing"``) reads fine and then
    quietly asks for a key nobody wrote — "antigravity" would look for
    ``health_antigravity_missing`` while the rest of the file says
    ``health_agy_*``. Spelling them out keeps the parity test able to find
    every key by grepping.
    """
    if last_updated is None:
        return ProviderHealth(provider, HealthState.MISSING, missing_key,
                              next_step_key=missing_fix_key)
    if now - last_updated > STALE_AFTER_SECONDS[provider]:
        return ProviderHealth(provider, HealthState.STALE, stale_key,
                              next_step_key=stale_fix_key,
                              last_updated=last_updated)
    return ProviderHealth(provider, HealthState.READY, ready_key, last_updated=last_updated)


def claude_health(
    *,
    hook_installed: bool,
    status_file_exists: bool,
    last_updated: float | None,
    now: float,
    read_error: str = "",
) -> ProviderHealth:
    """Claude Code's numbers arrive through the statusLine hook.

    The hook check comes first on purpose. Without it the status file simply
    stops being written, so its age is a symptom; reporting "data is old" would
    send the user looking in the wrong place.
    """
    if read_error:
        return ProviderHealth("claude", HealthState.ERROR, "health_claude_error",
                              next_step_key="health_generic_error_fix", detail=read_error)
    if not hook_installed:
        return ProviderHealth("claude", HealthState.MISCONFIGURED, "health_claude_no_hook",
                              next_step_key="health_claude_no_hook_fix")
    if not status_file_exists:
        return ProviderHealth("claude", HealthState.MISSING, "health_claude_missing",
                              next_step_key="health_claude_missing_fix")
    return _freshness(
        "claude", last_updated, now,
        ready_key="health_claude_ready",
        stale_key="health_claude_stale",
        stale_fix_key="health_claude_stale_fix",
        missing_key="health_claude_missing",
        missing_fix_key="health_claude_missing_fix",
    )


def codex_health(
    *,
    sessions_dir_exists: bool,
    session_count: int,
    last_updated: float | None,
    now: float,
    read_error: str = "",
) -> ProviderHealth:
    """Codex has no hook to install, so absence of logs is the only signal.

    A missing sessions directory and an empty one mean the same thing to a user
    — Codex has not run here — so both report MISSING rather than one of them
    looking like a broken install.
    """
    if read_error:
        return ProviderHealth("codex", HealthState.ERROR, "health_codex_error",
                              next_step_key="health_generic_error_fix", detail=read_error)
    if not sessions_dir_exists or session_count <= 0:
        return ProviderHealth("codex", HealthState.MISSING, "health_codex_missing",
                              next_step_key="health_codex_missing_fix")
    return _freshness(
        "codex", last_updated, now,
        ready_key="health_codex_ready",
        stale_key="health_codex_stale",
        stale_fix_key="health_codex_stale_fix",
        missing_key="health_codex_missing",
        missing_fix_key="health_codex_missing_fix",
    )


def antigravity_health(
    *,
    enabled: bool,
    credentials_found: bool,
    last_updated: float | None,
    now: float,
    probe_error: str = "",
    remote_unavailable: bool = False,
) -> ProviderHealth:
    """Antigravity is the one provider that must reach the network.

    That gives it a state the other two cannot have: credentials are fine and
    nothing is misconfigured, but Google did not answer. Cached numbers may
    still be shown, which is why UNAVAILABLE is distinct from ERROR.
    """
    if not enabled:
        return ProviderHealth("antigravity", HealthState.MISCONFIGURED, "health_agy_disabled",
                              next_step_key="health_agy_disabled_fix")
    if not credentials_found:
        return ProviderHealth("antigravity", HealthState.MISCONFIGURED, "health_agy_no_login",
                              next_step_key="health_agy_no_login_fix")
    if remote_unavailable:
        return ProviderHealth("antigravity", HealthState.UNAVAILABLE, "health_agy_unavailable",
                              next_step_key="health_agy_unavailable_fix",
                              last_updated=last_updated)
    if probe_error:
        return ProviderHealth("antigravity", HealthState.ERROR, "health_agy_error",
                              next_step_key="health_generic_error_fix", detail=probe_error,
                              last_updated=last_updated)
    return _freshness(
        "antigravity", last_updated, now,
        ready_key="health_agy_ready",
        stale_key="health_agy_stale",
        stale_fix_key="health_agy_stale_fix",
        missing_key="health_agy_missing",
        missing_fix_key="health_agy_missing_fix",
    )


def worst_of(healths: list[ProviderHealth]) -> ProviderHealth | None:
    """The one to surface when there is room for a single line."""
    if not healths:
        return None
    return max(healths, key=lambda health: _SEVERITY[health.state])
