# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Auto-open the next Antigravity 5-hour window."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path

from network_reachability import google_auth_reachable
from providers import agy_quota_probe
from state.menubar_agy import AgyRefreshResult
from state.menubar_prefs import _agy_window_keeper_enabled
from subprocess_utils import creation_flags

logger = logging.getLogger(__name__)

AGY_WINDOW_KEEPER_STATE_PATH = Path(
    os.path.expanduser("~/.agentdeck/agy_window_keeper.json")
)
PING_COOLDOWN_SECONDS = 5 * 3600
AGY_CLI_SIGNED_OUT_PATH = AGY_WINDOW_KEEPER_STATE_PATH.parent / "agy_cli_signed_out"
PING_TIMEOUT_SECONDS = 180
AGY_MODEL = "Gemini 3.5 Flash (Low)"
_AGY_BIN_FALLBACKS = (
    "~/.local/bin/agy",
    "~/AppData/Local/agy/bin/agy.exe",
)

_lock = threading.Lock()
_ping_in_flight = False


def should_ping(
    now: float,
    enabled: bool,
    last_ping_at: float | None,
    remaining_percent: float | None,
    stale: object | None,
    fallback_projection: bool,
    mock: bool,
) -> bool:
    """Return whether fresh quota data shows no active five-hour window.

    At 100% remaining, the API reset time is a sliding placeholder, so it
    cannot indicate an active window.
    """
    if not enabled or mock or fallback_projection or stale is not None:
        return False
    if remaining_percent is None or remaining_percent < 100.0:
        return False
    return last_ping_at is None or now - last_ping_at >= PING_COOLDOWN_SECONDS


def _load_last_ping(path: Path | None = None) -> float | None:
    state_path = AGY_WINDOW_KEEPER_STATE_PATH if path is None else path
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("last_ping_at")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _save_last_ping(ts: float, path: Path | None = None) -> None:
    state_path = AGY_WINDOW_KEEPER_STATE_PATH if path is None else path
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"last_ping_at": ts}) + "\n"
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=state_path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_path, state_path)
        tmp_path = None
    except OSError:
        _debug_log("agy-window-keeper state write failed", exc_info=True)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            with suppress(OSError):
                os.unlink(tmp_path)


def _resolve_agy_bin() -> str | None:
    found = shutil.which("agy")
    if found:
        return found
    for candidate in _AGY_BIN_FALLBACKS:
        resolved = os.path.expanduser(candidate)
        if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
    return None


def _try_acquire() -> bool:
    global _ping_in_flight
    with _lock:
        if _ping_in_flight:
            return False
        _ping_in_flight = True
        return True


def _release() -> None:
    global _ping_in_flight
    with _lock:
        _ping_in_flight = False


def _credential_fingerprint() -> str | None:
    """Read the stored credential without resolving or refreshing it."""
    token_data: object = agy_quota_probe._read_token_file()
    if not agy_quota_probe._has_usable_token(token_data):
        token_data = agy_quota_probe._read_windows_credential()
    token = token_data.get("token") if isinstance(token_data, dict) else None
    if not isinstance(token, dict):
        return None
    return hashlib.sha256(json.dumps(token, sort_keys=True).encode()).hexdigest()


def _mark_cli_signed_out(before: str | None) -> None:
    if _credential_fingerprint() != before:
        return
    with suppress(OSError):
        AGY_CLI_SIGNED_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        AGY_CLI_SIGNED_OUT_PATH.write_text(
            json.dumps({"fingerprint": before}), encoding="utf-8",
        )


def _cli_may_run() -> bool:
    if not AGY_CLI_SIGNED_OUT_PATH.exists():
        return True
    try:
        marker = json.loads(AGY_CLI_SIGNED_OUT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        marker = {}
    stored = marker.get("fingerprint") if isinstance(marker, dict) else None
    current = _credential_fingerprint()
    if current is None or current == stored:
        return False
    with suppress(OSError):
        AGY_CLI_SIGNED_OUT_PATH.unlink(missing_ok=True)
    return True


def _auth_failure(stdout: object, stderr: object) -> bool:
    output = f"{stdout or ''}\n{stderr or ''}".lower()
    return "authentication required" in output or "authentication failed" in output


def _run_agy_ping(agy_bin: str) -> None:
    if not _cli_may_run():
        return
    before = _credential_fingerprint()
    try:
        _run_agy_command(agy_bin, before)
    except subprocess.TimeoutExpired as exc:
        if _auth_failure(exc.stdout, exc.stderr):
            _mark_cli_signed_out(before)
        raise


def _run_agy_command(agy_bin: str, before: str | None) -> None:
    result = subprocess.run(  # noqa: S603 - resolved local Antigravity CLI
        [agy_bin, "-p", "ok", "--model", AGY_MODEL],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=PING_TIMEOUT_SECONDS,
        cwd=os.path.expanduser("~"),
        check=False,
        creationflags=creation_flags(),
    )
    if result.returncode != 0 and _auth_failure(result.stdout, result.stderr):
        _mark_cli_signed_out(before)


def _ping_worker(started_at: float) -> None:
    try:
        agy_bin = _resolve_agy_bin()
        if agy_bin is None:
            _debug_log("agy-window-keeper: agy binary not found, skipping ping")
            return
        _run_agy_ping(agy_bin)
        _debug_log(f"agy-window-keeper: ping completed (started_at={started_at})")
    except subprocess.TimeoutExpired:
        _debug_log(f"agy-window-keeper: ping timed out after {PING_TIMEOUT_SECONDS}s")
    except Exception:
        _debug_log("agy-window-keeper: ping failed", exc_info=True)
    finally:
        _release()


def maybe_ping(result: AgyRefreshResult, mock: bool) -> None:
    """Read preferences and state, then dispatch a background ping if eligible."""
    if mock:
        return
    enabled = _agy_window_keeper_enabled()
    if not enabled:
        return
    projection = result.projection
    # The panel prefers Gemini, but can fall back to another group when it is absent.
    # Only Gemini's window can authorize a Gemini ping.
    five_hour = (
        projection.five_hour
        if projection is not None and "gemini" in projection.group_name.lower()
        else None
    )
    now = time.time()
    last_ping_at = _load_last_ping()
    if not should_ping(
        now=now,
        enabled=enabled,
        last_ping_at=last_ping_at,
        remaining_percent=(
            five_hour.remaining_percent if five_hour is not None else None
        ),
        stale=projection.stale if projection is not None else None,
        fallback_projection=projection is None,
        mock=mock,
    ):
        return
    if not google_auth_reachable():
        return
    if not _cli_may_run():
        return
    if not _try_acquire():
        return
    # Stamp dispatch even on failure to avoid retrying every refresh.
    _save_last_ping(now)
    threading.Thread(target=_ping_worker, args=(now,), daemon=True).start()


def _debug_log(message: str, *, exc_info: bool = False) -> None:
    if os.environ.get("AGENTDECK_DEBUG") == "1":
        logger.warning(message, exc_info=exc_info)
