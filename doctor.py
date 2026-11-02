# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import os
import platform
import re
import shlex
import sqlite3
import sys
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from importlib import metadata
from pathlib import Path
from typing import Any

import provider_health
import provider_probe
import setup_hook
import status_projection
from i18n import _t, packaged_resource_path

SEPARATOR = "-" * 29
DOCTOR_SCHEMA_VERSION = 1


def _json_check(func: Callable[[], Any]) -> Any:
    try:
        return func()
    except Exception as exc:
        # Exception messages may contain credentials or arbitrary project paths.
        return {"error": type(exc).__name__}


def _json_hook_version() -> dict[str, str | None]:
    installed = setup_hook._installed_hook_version()
    if installed is not None and not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,8}){1,3}", installed):
        installed = "[REDACTED]"
    return {"installed": installed, "current": setup_hook.HOOK_VERSION}


def _file_info(path: Path) -> dict[str, Any]:
    # Paths add no diagnostic value beyond the logical file name in this report.
    exists = path.exists()
    return {"exists": exists, "modified_ago": _ago(path.stat().st_mtime) if exists else None}


def _json_self_heal_log() -> list[dict[str, Any]]:
    settings = setup_hook._load_settings()
    usage = settings.get(setup_hook.BACKUP_KEY)
    log = usage.get("selfHealLog") if isinstance(usage, dict) else None
    if not isinstance(log, list):
        return []
    known_actions = {
        "install_hook", "update_hook", "restore_hook_scripts", "migrate_windows_statusline",
        "migrate_bundled_python", "restore_terse_hook_codex", "update_terse_hook_codex",
        "restore_resume_hook", "update_resume_hook", "restore_terse_hook", "update_terse_hook",
        "restore_terse_reminder_hook", "update_terse_reminder_hook", "upgrade_codex_status_line",
    }
    entries = []
    for item in log[-5:]:
        if not isinstance(item, dict):
            continue
        try:
            timestamp = datetime.fromisoformat(str(item.get("timestamp"))).isoformat()
        except ValueError:
            timestamp = "unknown"
        action = item.get("action")
        entries.append({
            "timestamp": timestamp,
            "action": (
                action if isinstance(action, str) and action in known_actions else "[REDACTED]"
            ),
            "detail": "[REDACTED]" if item.get("detail") else "",
        })
    return entries


def render_json() -> str:
    """Issue-safe, headless diagnostic report sharing the status v1 projection.

    No repair, UI initialization, network probe or raw credential is requested.
    Free-form logs and exception messages are withheld, even for unknown secrets.
    """
    from providers import codex_loader

    payload = status_projection.build_status_payload()
    payload["schema_version"] = DOCTOR_SCHEMA_VERSION
    for entry in payload["providers"].values():
        health = entry.get("health", {})
        if health.get("detail"):
            health["detail"] = "[REDACTED]"
    payload["diagnostics"] = {
        "environment": {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "packaged": bool(getattr(sys, "frozen", False)),
        },
        "checks": {
            "hook_state": _json_check(_hook_state),
            "hook_version": _json_check(_json_hook_version),
            "status_command": _json_check(_status_command),
            "external_hooks": _json_check(_external_hooks),
            "forwarder_prompt": _json_check(_forwarder_prompt),
            "codex_sessions": _json_check(_codex_sessions),
            "codex_log_rate_limit_rows": _json_check(
                lambda: _codex_rate_limit_log_count(codex_loader.LOGS_DB)
                if codex_loader.LOGS_DB.exists() else 0
            ),
            "codex_rate_limits": _json_check(_codex_rate_limits),
        },
        "files": {
            name: _json_check(partial(_file_info, path))
            for name, path in (
                ("hook_script", setup_hook.HOOK_TARGET),
                ("forwarder_script", setup_hook.FORWARDER_TARGET),
                ("status_file", setup_hook.STATUS_FILE),
                ("codex_logs", codex_loader.LOGS_DB),
                ("codex_state", codex_loader.STATE_DB),
            )
        },
        "self_heal_log": _json_check(_json_self_heal_log),
    }
    return json.dumps(status_projection.redact_data(payload), ensure_ascii=False, indent=2)


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
        healths = provider_probe.collect_provider_health(now=now)
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
    from providers import codex_loader

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
    from providers import codex_loader

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
    from providers import codex_loader

    state_db = codex_loader.STATE_DB
    status = "ok" if state_db.exists() else "missing"
    return f"{_display_path(state_db)}  [{status}]"


def _codex_rate_limits() -> str:
    from providers import codex_loader

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
