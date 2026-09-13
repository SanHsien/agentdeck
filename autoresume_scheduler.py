# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Register and clear the one-shot Windows task that resumes work after a quota reset.

The tray already polls, so an in-process timer looks like the obvious way to wait for
the reset. It is not: a sleeping or hibernating machine freezes that timer, and
"the machine was asleep overnight" is the ordinary case this feature exists for. A
scheduled task with ``StartWhenAvailable`` survives sleep and runs on wake, so the
wait is handed to the Windows scheduler instead of kept in memory.

The task is registered from XML rather than ``schtasks`` switches because
``StartWhenAvailable`` has no command-line flag. Building that XML is a pure function
so the scheduling contract can be asserted in tests without touching the real
scheduler.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from adapters.rate_limits import load_rate_limits, load_resume_target
from i18n import _t
from state.autoresume import ScheduleDecision, decide
from state.menubar_prefs import _auto_resume_config

TASK_NAME = "agentdeck-auto-resume"

RESULT_PATH = Path(os.path.expanduser("~/.agentdeck/autoresume-result.json"))

#: Give up rather than run a resume that has been waiting so long its handoff is
#: stale — a machine off for days should wake to no surprise session.
EXECUTION_TIME_LIMIT = "PT3H"

logger = logging.getLogger(__name__)

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>{description}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>{execution_time_limit}</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def resume_command() -> tuple[str, str]:
    """Return the (command, arguments) pair that re-enters this app in resume mode.

    Frozen by PyInstaller the executable is self-contained; from a source checkout the
    task has to go back through the interpreter that is running now, because the
    scheduler starts with none of this environment.
    """
    if getattr(sys, "frozen", False):
        return sys.executable, "--resume-now"
    return sys.executable, f'"{os.path.abspath("main.py")}" --resume-now'


def build_task_xml(
    run_at: datetime,
    command: str,
    arguments: str,
    description: str = "agentdeck: resume work after the Claude Code quota resets",
) -> str:
    """Render the scheduled-task definition.

    ``run_at`` must be local time: Task Scheduler reads a ``StartBoundary`` without an
    offset as local, and the reset stamp has already been converted by the caller.
    """
    return _TASK_XML.format(
        description=escape(description),
        start_boundary=run_at.strftime("%Y-%m-%dT%H:%M:%S"),
        execution_time_limit=EXECUTION_TIME_LIMIT,
        command=escape(command),
        arguments=escape(arguments),
    )


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def schedule(run_at: datetime) -> bool:
    """Register (or replace) the one-shot resume task. Returns True on success."""
    command, arguments = resume_command()
    xml = build_task_xml(run_at, command, arguments)

    # schtasks reads the definition as UTF-16, matching the XML declaration above.
    handle, xml_path = tempfile.mkstemp(suffix=".xml")
    try:
        with os.fdopen(handle, "w", encoding="utf-16") as file:
            file.write(xml)
        result = _run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"])
    except OSError:
        logger.warning("auto-resume: could not write the task definition", exc_info=True)
        return False
    finally:
        with contextlib.suppress(OSError):
            os.unlink(xml_path)

    if result.returncode != 0:
        logger.warning("auto-resume: schtasks /Create failed: %s", result.stderr.strip())
        return False
    return True


def cancel() -> bool:
    """Remove the resume task. Absent is success — the goal is "no task pending"."""
    result = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    if result.returncode == 0:
        return True
    # schtasks cannot distinguish "no such task" by exit code alone.
    if "cannot find" in result.stderr.lower() or "找不到" in result.stderr:
        return True
    logger.warning("auto-resume: schtasks /Delete failed: %s", result.stderr.strip())
    return False


def is_scheduled() -> bool:
    return _run(["schtasks", "/Query", "/TN", TASK_NAME]).returncode == 0


def write_result(session_id: str, exit_code: int) -> None:
    """Leave the outcome for the tray to announce.

    The resumed run happens in its own process with no tray icon, so it cannot raise
    a notification itself. It drops the outcome here and the next tray poll reports it.
    """
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "exit_code": exit_code,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    handle, tmp_path = tempfile.mkstemp(dir=str(RESULT_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)
        os.replace(tmp_path, RESULT_PATH)
    except OSError:
        logger.warning("auto-resume: could not record the run outcome", exc_info=True)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)


def take_result() -> dict[str, object] | None:
    """Read and clear the pending outcome, so it is announced exactly once."""
    try:
        payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    with contextlib.suppress(OSError):
        RESULT_PATH.unlink()
    return payload if isinstance(payload, dict) else None


#: What the scheduler is believed to hold, so an unchanged decision on the next poll
#: costs nothing. ``None`` means "no task pending"; the value is the scheduled epoch.
_registered_run_at: int | None = None


def reset_registration_cache() -> None:
    """Forget what the scheduler is believed to hold. For tests and for re-sync."""
    global _registered_run_at
    _registered_run_at = None


def tick(icon: object, language: str) -> ScheduleDecision:
    """Keep the scheduled task in step with the quota, and announce finished runs.

    Called on every tray refresh, so it must be cheap when nothing has changed:
    ``schtasks`` is only invoked when the decision differs from what is already
    registered. Everything the decision needs is read here rather than passed in, so
    wiring this into the tray costs a single call.
    """
    global _registered_run_at

    result = take_result()
    if result is not None:
        # The run that just finished consumed the task it was triggered by.
        _registered_run_at = None
        _announce(icon, language, result)

    decision = decide(
        load_rate_limits(),
        load_resume_target(),
        _auto_resume_config(),
        int(datetime.now().timestamp()),
    )

    if decision.action == "schedule" and decision.run_at is not None:
        if decision.run_at != _registered_run_at and schedule(
            datetime.fromtimestamp(decision.run_at)
        ):
            _registered_run_at = decision.run_at
    elif decision.action == "cancel" and _registered_run_at is not None and cancel():
        _registered_run_at = None

    return decision


def _announce(icon: object, language: str, result: dict[str, object]) -> None:
    notify = getattr(icon, "notify", None)
    if not callable(notify):
        return
    ok = result.get("exit_code") == 0
    key = "autoresume_done" if ok else "autoresume_failed"
    with contextlib.suppress(Exception):
        notify(_t(language, f"{key}_body"), _t(language, f"{key}_title"))
