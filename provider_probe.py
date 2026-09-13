# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Gather the facts ``provider_health`` projects, in one place.

``provider_health`` is deliberately IO-free so every branch is testable without
a provider installed. Something still has to read the disk, and that something
must be shared: the panels and ``--doctor`` reaching the same files by separate
code is how they drifted into disagreeing in the first place, which is the
problem the health model exists to solve.

So this module is the only place that turns files into facts, and both surfaces
call it.
"""

from __future__ import annotations

from pathlib import Path

import provider_health
import setup_hook


def collect_provider_health(*, now: float) -> list[provider_health.ProviderHealth]:
    """Gather the facts the projections need. All IO lives here, not in the model."""
    import usage_client
    from providers import codex_loader

    claude_error = ""
    status_path = Path(usage_client.STATUS_FILE)
    claude_updated: float | None = None
    try:
        if status_path.exists():
            claude_updated = status_path.stat().st_mtime
    except OSError as exc:
        claude_error = f"{type(exc).__name__}: {exc}"

    codex_error = ""
    sessions_dir = codex_loader.SESSIONS_DIR
    session_count = 0
    codex_updated: float | None = None
    try:
        if sessions_dir.is_dir():
            for path in sessions_dir.rglob("*.jsonl"):
                session_count += 1
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                codex_updated = mtime if codex_updated is None else max(codex_updated, mtime)
    except OSError as exc:
        codex_error = f"{type(exc).__name__}: {exc}"

    return [
        provider_health.claude_health(
            hook_installed=setup_hook._detect_current_state() != "missing",
            status_file_exists=status_path.exists(),
            last_updated=claude_updated,
            now=now,
            read_error=claude_error,
        ),
        provider_health.codex_health(
            sessions_dir_exists=sessions_dir.is_dir(),
            session_count=session_count,
            last_updated=codex_updated,
            now=now,
            read_error=codex_error,
        ),
        _antigravity_health(now),
    ]


def _antigravity_health(now: float) -> provider_health.ProviderHealth:
    """Antigravity's facts come from a preference and a credential, not a file.

    The probe is deliberately not run here: --doctor must stay a read-only
    report, and firing a network request would make the diagnostic itself a
    reason the state changes.
    """
    from providers import agy_quota_probe
    from state.menubar_prefs import _hide_agy_enabled

    probe_error = ""
    last_updated: float | None = None
    try:
        cache = agy_quota_probe.CACHE_PATH
        if cache.exists():
            last_updated = cache.stat().st_mtime
    except OSError as exc:
        probe_error = f"{type(exc).__name__}: {exc}"

    credentials_found = False
    try:
        credentials_found = agy_quota_probe._has_usable_token(
            agy_quota_probe._read_windows_credential()
        ) or agy_quota_probe._has_usable_token(agy_quota_probe._read_token_file())
    except Exception as exc:  # noqa: BLE001 - a broken credential store is a fact, not a crash
        probe_error = probe_error or f"{type(exc).__name__}: {exc}"

    return provider_health.antigravity_health(
        enabled=not _hide_agy_enabled(),
        credentials_found=credentials_found,
        last_updated=last_updated,
        now=now,
        probe_error=probe_error,
    )
