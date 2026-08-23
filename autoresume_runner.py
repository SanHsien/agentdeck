# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Carry out the resume once the scheduled task fires.

Invoked as ``--resume-now`` by the task :mod:`autoresume_scheduler` registered, in a
process the Windows scheduler started — no terminal, no console, nobody watching. Two
consequences shape everything here:

**The run must be non-interactive.** ``claude --resume`` reattaches an interactive
session and would block forever without a TTY. ``claude -p`` prints and exits, so that
is what a scheduled run uses; the conversation is carried across as a handoff prompt
rather than by reattaching.

**Nothing may raise.** A crash in a headless task is invisible. Every failure is
written to the log and reported through the exit code instead.

The handoff is assembled from the previous session's transcript by reusing the
extraction :mod:`usage_session_resume` already performs for its SessionStart hook —
the same "what was actually being worked on" logic, so the two features cannot drift
into disagreeing about where work stopped.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import autoresume_scheduler
from adapters.rate_limits import load_resume_target
from adapters.types import ResumeTarget
from i18n import t as _t
from usage_session_resume import _parse_session

LOG_PATH = Path(os.path.expanduser("~/.agentdeck/autoresume-log.txt"))

#: Slightly under the task's own ExecutionTimeLimit so the run is cut off here, where
#: the reason can be logged, rather than killed silently by the scheduler.
RUN_TIMEOUT_SECONDS = 165 * 60

_MAX_COMMITS = 3
_MAX_TODOS = 5
_MAX_FILES = 5

logger = logging.getLogger(__name__)


def _log(message: str) -> None:
    """Append one timestamped line. Logging must never be the thing that fails."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(f"{stamp}  {message}\n")
    except OSError:
        logger.warning("auto-resume: could not write %s", LOG_PATH, exc_info=True)


def build_handoff(target: ResumeTarget) -> str:
    """Describe where the interrupted work stopped, as a prompt for the resumed run.

    Returns "" when the transcript yields nothing usable — better to skip the run
    than to wake Claude up with an empty instruction and let it invent a task.
    """
    if not target.transcript_path:
        return ""
    parsed = _parse_session(Path(target.transcript_path))
    if parsed is None:
        return ""

    _last_active, last_request, commits, todos, edited_files = parsed
    none_label = _t("autoresume_none")
    done = commits[:_MAX_COMMITS] or edited_files[:_MAX_FILES]

    return _t(
        "autoresume_prompt",
        last_request=last_request or none_label,
        commits=" · ".join(done) or none_label,
        todos=" · ".join(todos[:_MAX_TODOS]) or none_label,
    )


def _claude_executable() -> str | None:
    return shutil.which("claude")


def run_resume() -> int:
    """Entry point for ``--resume-now``. Returns a process exit code.

    The one-shot task is removed on the way out whatever the outcome, so a failure
    cannot leave a trigger behind that fires again on the next reset.
    """
    try:
        return _run_resume()
    finally:
        autoresume_scheduler.cancel()


def _run_resume() -> int:
    _log("=== resume fired ===")

    target = load_resume_target()
    if target is None:
        _log("ABORT: no resumable session recorded in the status file")
        return 1

    executable = _claude_executable()
    if executable is None:
        _log("ABORT: 'claude' is not on PATH for the scheduled task's user")
        return 1

    if not Path(target.cwd).is_dir():
        _log(f"ABORT: working directory is gone: {target.cwd}")
        return 1

    prompt = build_handoff(target)
    if not prompt:
        _log(f"ABORT: nothing to hand off from {target.transcript_path or '<no transcript>'}")
        return 1

    _log(f"resuming session {target.session_id} in {target.cwd}")
    try:
        result = subprocess.run(
            [executable, "-p", prompt],
            cwd=target.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _log(f"TIMEOUT after {RUN_TIMEOUT_SECONDS}s")
        return 1
    except OSError as error:
        _log(f"ABORT: could not start claude: {error}")
        return 1

    if result.stdout.strip():
        _log(f"output:\n{result.stdout.strip()}")
    if result.returncode != 0 and result.stderr.strip():
        _log(f"stderr:\n{result.stderr.strip()}")
    _log(f"=== exit code: {result.returncode} ===")
    autoresume_scheduler.write_result(target.session_id, result.returncode)
    return result.returncode
