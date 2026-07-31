# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import os
import shlex
import sqlite3
import sys
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

import provider_health
import setup_hook
from i18n import _t, packaged_resource_path

SEPARATOR = "-" * 29


def render() -> str:
    lines = [
        f"agentdeck v{_field(_current_version)}",
        SEPARATOR,
        f"hook state:        {_field(_hook_state)}",
        f"hook version:      {_field(_hook_version)}",
        f"hook script:       {_script_status(setup_hook.HOOK_TARGET)}",
        f"forwarder script:  {_script_status(setup_hook.FORWARDER_TARGET)}",
        f"status file:       {_field(_status_file)}",
        f"status command:    {_field(_status_command)}",
        f"external hooks:    {_field(_external_hooks)}",
        f"forwarder prompt:  {_field(_forwarder_prompt)}",
        "self-heal log (last 5):",
        *_self_heal_log_lines(),
        SEPARATOR,
        f"codex jsonl:       {_field(_codex_sessions)}",
        f"codex logs:        {_field(_codex_logs)}",
        f"codex state:       {_field(_codex_state)}",
        f"codex rate limits: {_field(_codex_rate_limits)}",
        SEPARATOR,
        "provider health:",
        *_provider_health_lines(),
    ]
    return "\n".join(lines) + "\n"


def _provider_health_lines() -> list[str]:
    """Render the shared health model so --doctor and the panels agree.

    Each surface used to reach its own verdict from the same files and phrase it
    its own way, so a user comparing them could not tell whether they disagreed
    about the facts or only about the wording.
    """
    import time

    from usage_lang import detect_lang

    now = time.time()
    try:
        healths = collect_provider_health(now=now)
    except Exception as exc:  # noqa: BLE001 - diagnostics must not be what breaks
        return [f"  error: {type(exc).__name__}: {exc}"]

    language = detect_lang()
    lines: list[str] = []
    for health in healths:
        when = f", updated {_ago(health.last_updated)} ago" if health.last_updated else ""
        lines.append(f"  {health.provider:<12} [{health.state}]{when}")
        lines.append(f"    {_t(language, health.reason_key)}")
        if health.next_step_key and health.state is not provider_health.HealthState.READY:
            lines.append(f"    -> {_t(language, health.next_step_key)}")
        if health.detail:
            lines.append(f"    {health.detail}")
    return lines or ["  none"]


def collect_provider_health(*, now: float) -> list[provider_health.ProviderHealth]:
    """Gather the facts the projections need. All IO lives here, not in the model."""
    import codex_loader
    import usage_client

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
    import agy_quota_probe
    from menubar_prefs import _hide_agy_enabled

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


def _field(func: Callable[[], str]) -> str:
    try:
        return func()
    except Exception as exc:
        return f"error: {exc}"


def _current_version() -> str:
    try:
        return metadata.version("agentdeck")
    except metadata.PackageNotFoundError:
        pyproject = packaged_resource_path(
            "pyproject.toml", Path(__file__).with_name("pyproject.toml")
        )
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version")
        if isinstance(version, str):
            return version
        raise RuntimeError("project.version missing from pyproject.toml") from None


def _hook_state() -> str:
    return setup_hook._detect_current_state()


def _hook_version() -> str:
    installed = setup_hook._installed_hook_version()
    if installed is None:
        return f"not installed (current {setup_hook.HOOK_VERSION})"
    suffix = (
        "current"
        if installed == setup_hook.HOOK_VERSION
        else f"current {setup_hook.HOOK_VERSION}"
    )
    return f"{installed} ({suffix})"


def _script_status(path: Path) -> str:
    try:
        display = _display_path(path)
        status = "ok" if path.exists() else "missing"
        return f"{display}  [{status}]"
    except Exception as exc:
        return f"error: {exc}"


def _status_file() -> str:
    path = setup_hook.STATUS_FILE
    display = _display_path(path)
    if not path.exists():
        return f"{display}  [missing]"
    return f"{display}  (wrote {_ago(path.stat().st_mtime)} ago)"


def _status_command() -> str:
    settings = setup_hook._load_settings()
    sl = settings.get("statusLine")
    command = sl.get("command") if isinstance(sl, dict) else None
    if not isinstance(command, str):
        return "not configured"
    if (
        sys.platform == "win32"
        and "agentdeck-statusline" in command
        and "\\" in command
    ):
        return "Windows Git Bash-incompatible paths; run usage --setup, then restart Claude Code"
    return "ok"


def _external_hooks() -> str:
    state = setup_hook._detect_current_state()
    if state != "external":
        return "none detected"
    settings = setup_hook._load_settings()
    sl = settings.get("statusLine")
    command = sl.get("command") if isinstance(sl, dict) else None
    if not isinstance(command, str):
        return "external (unrecognized)"
    keyword = _external_keyword(command)
    return keyword if keyword else "external (unrecognized)"


def _forwarder_prompt() -> str:
    settings = setup_hook._load_settings()
    usage = settings.get(setup_hook.BACKUP_KEY)
    if isinstance(usage, dict) and usage.get("forwarderModePromptDismissed") is True:
        return "acked"
    return "not acked"


def _self_heal_log_lines() -> list[str]:
    try:
        settings = setup_hook._load_settings()
        usage = settings.get(setup_hook.BACKUP_KEY)
        log = usage.get("selfHealLog") if isinstance(usage, dict) else None
        if not isinstance(log, list) or not log:
            return ["  none"]
        lines: list[str] = []
        for item in log[-5:]:
            if not isinstance(item, dict):
                continue
            timestamp = str(item.get("timestamp", "unknown"))
            action = str(item.get("action", "unknown"))
            detail = str(item.get("detail", ""))
            lines.append(f"  {timestamp}  {action:<22} {detail}".rstrip())
        return lines or ["  none"]
    except Exception as exc:
        return [f"  error: {exc}"]


def _codex_sessions() -> str:
    import codex_loader

    sessions_dir = codex_loader.SESSIONS_DIR
    if not sessions_dir.is_dir():
        return "0 files, missing sessions dir"
    count = 0
    newest_mtime = 0.0
    for path in sessions_dir.rglob("*.jsonl"):
        count += 1
        try:
            newest_mtime = max(newest_mtime, path.stat().st_mtime)
        except OSError:
            continue
    if newest_mtime <= 0:
        return f"{count} files, no readable mtimes"
    return f"{count} files, latest wrote {_ago(newest_mtime)} ago"


def _codex_logs() -> str:
    import codex_loader

    logs_db = codex_loader.LOGS_DB
    if not logs_db.exists():
        return f"{_display_path(logs_db)}  [missing], rate_limit rows: 0"
    rows = _codex_rate_limit_log_count(logs_db)
    return f"{_display_path(logs_db)}  [ok], rate_limit rows: {rows}"


def _codex_rate_limit_log_count(logs_db: Path) -> int:
    query = (
        "SELECT count(*) FROM logs "
        "WHERE feedback_log_body LIKE '%codex.rate_limits%' "
        "OR feedback_log_body LIKE '%usage_limit_reached%'"
    )
    with sqlite3.connect(f"{logs_db.resolve().as_uri()}?mode=ro", uri=True) as conn:
        value = conn.execute(query).fetchone()[0]
    return int(value)


def _codex_state() -> str:
    import codex_loader

    state_db = codex_loader.STATE_DB
    status = "ok" if state_db.exists() else "missing"
    return f"{_display_path(state_db)}  [{status}]"


def _codex_rate_limits() -> str:
    import codex_loader

    rate_limits = codex_loader.load_rate_limits()
    if rate_limits is None:
        return "none"
    five = "yes" if rate_limits.five_hour_pct is not None else "no"
    weekly = "yes" if rate_limits.seven_day_pct is not None else "no"
    updated = _rate_limits_updated_age(rate_limits.updated_at)
    return f"5h: {five}, weekly: {weekly}, updated: {updated}"


def _rate_limits_updated_age(updated_at: str) -> str:
    if not updated_at:
        return "unknown"
    timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)
    return f"{_ago(timestamp.timestamp())} ago"


def _external_keyword(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for part in parts:
        token = part.lower()
        basename = Path(part).name.lower()
        for keyword in ("ccusage", "lord-kali"):
            if keyword in token or keyword in basename:
                return keyword
    return None


def _display_path(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    if text == home:
        return "~"
    if text.startswith(home + os.sep):
        return "~" + text[len(home) :]
    return text


def _ago(mtime: float) -> str:
    seconds = max(0, int(datetime.now(UTC).timestamp() - mtime))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"
