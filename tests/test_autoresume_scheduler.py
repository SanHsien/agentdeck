# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from xml.etree import ElementTree

import pytest

import autoresume_scheduler as scheduler

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
RUN_AT = datetime(2026, 8, 9, 13, 53, 0)


def _xml() -> str:
    return scheduler.build_task_xml(RUN_AT, "C:/apps/agentdeck.exe", "--resume-now")


def _parse(xml: str) -> ElementTree.Element:
    return ElementTree.fromstring(xml)


def _text(root: ElementTree.Element, path: str) -> str:
    node = root.find(path, NS)
    assert node is not None, f"missing {path}"
    return (node.text or "").strip()


def test_task_definition_is_well_formed_xml() -> None:
    assert _parse(_xml()).tag.endswith("Task")


def test_trigger_uses_local_time_without_an_offset() -> None:
    # Task Scheduler reads an offset-free StartBoundary as local time; appending a
    # zone here would silently shift every resume.
    assert _text(_parse(_xml()), "t:Triggers/t:TimeTrigger/t:StartBoundary") == (
        "2026-08-09T13:53:00"
    )


def test_start_when_available_survives_a_sleeping_machine() -> None:
    """The whole point of using the scheduler instead of an in-process timer."""
    assert _text(_parse(_xml()), "t:Settings/t:StartWhenAvailable") == "true"


def test_battery_settings_do_not_suppress_an_overnight_run() -> None:
    root = _parse(_xml())

    assert _text(root, "t:Settings/t:DisallowStartIfOnBatteries") == "false"
    assert _text(root, "t:Settings/t:StopIfGoingOnBatteries") == "false"


def test_action_carries_the_command_and_arguments() -> None:
    root = _parse(_xml())

    assert _text(root, "t:Actions/t:Exec/t:Command") == "C:/apps/agentdeck.exe"
    assert _text(root, "t:Actions/t:Exec/t:Arguments") == "--resume-now"


def test_execution_time_limit_bounds_a_stale_resume() -> None:
    assert _text(_parse(_xml()), "t:Settings/t:ExecutionTimeLimit") == "PT3H"


def test_paths_with_xml_metacharacters_stay_parseable() -> None:
    xml = scheduler.build_task_xml(RUN_AT, 'C:/a&b/"quoted"/app.exe', "--resume-now --note <x>")

    root = _parse(xml)

    assert _text(root, "t:Actions/t:Exec/t:Command") == 'C:/a&b/"quoted"/app.exe'
    assert _text(root, "t:Actions/t:Exec/t:Arguments") == "--resume-now --note <x>"


def test_declared_encoding_matches_what_schtasks_is_given() -> None:
    # schedule() writes the file as UTF-16; a mismatch here makes schtasks reject it.
    assert 'encoding="UTF-16"' in _xml()


def _fake_run(
    monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: str = ""
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, returncode, "", stderr)

    monkeypatch.setattr(scheduler, "_run", fake)
    return calls


def test_cancel_reports_success_when_the_task_is_already_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "nothing pending" is the goal, so a missing task is the desired state, not a
    # failure worth logging or retrying.
    _fake_run(monkeypatch, 1, "ERROR: The system cannot find the file specified.")

    assert scheduler.cancel() is True


def test_cancel_recognises_the_localized_not_found_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_run(monkeypatch, 1, "錯誤: 系統找不到指定的檔案。")

    assert scheduler.cancel() is True


def test_cancel_reports_failure_on_a_real_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_run(monkeypatch, 1, "ERROR: Access is denied.")

    assert scheduler.cancel() is False


def test_cancel_targets_the_named_task(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_run(monkeypatch, 0)

    scheduler.cancel()

    assert calls == [["schtasks", "/Delete", "/TN", scheduler.TASK_NAME, "/F"]]


def test_is_scheduled_follows_the_query_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_run(monkeypatch, 0)
    assert scheduler.is_scheduled() is True

    _fake_run(monkeypatch, 1)
    assert scheduler.is_scheduled() is False


def test_frozen_build_invokes_the_executable_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "C:/apps/agentdeck.exe")

    assert scheduler.resume_command() == ("C:/apps/agentdeck.exe", "--resume-now")


def test_source_checkout_routes_back_through_the_interpreter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The scheduler starts the task with none of the developer's environment, so the
    # entry point has to be spelled out rather than relying on a resolved `python`.
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", "C:/py/python.exe")

    command, arguments = scheduler.resume_command()

    assert command == "C:/py/python.exe"
    assert arguments.endswith("--resume-now")
    assert "main.py" in arguments
