# SPDX-License-Identifier: AGPL-3.0-only
"""The settings lock, proved against real concurrent processes.

A single-process test cannot show this works: the failure mode is two OS
processes interleaving a load -> modify -> save cycle, and every individual save
is atomic, so nothing is ever corrupt. The lost entry simply never appears.

So the contention test spawns real interpreters. It also runs the same scenario
with the lock disabled and requires *that* to lose entries -- otherwise a test
that passes proves only that the machine happened not to interleave.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import settings_lock

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKERS = 4
APPENDS_EACH = 5  # 20 total: the log keeps the last 20, so none should be dropped


def test_exclusive_reports_whether_it_locked(tmp_path: Path) -> None:
    with settings_lock.exclusive(tmp_path / "a.lock") as locked:
        assert locked is True, "this platform should support locking"


def test_the_lock_is_released_when_the_block_ends(tmp_path: Path) -> None:
    """A lock that is never released turns the next edit into a ten-second
    stall followed by an unsynchronised write -- worse than no lock at all."""
    lock = tmp_path / "b.lock"

    with settings_lock.exclusive(lock) as first:
        assert first is True

    with settings_lock.exclusive(lock, timeout=1.0) as second:
        assert second is True


def test_an_unopenable_lock_path_still_runs_the_block(tmp_path: Path) -> None:
    """Losing an edit is bad; refusing to install a hook because a lock file
    could not be opened is worse."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("file", encoding="utf-8")

    with settings_lock.exclusive(blocked / "nested" / "c.lock") as locked:
        assert locked is False


def _worker_source(settings: Path, lock: Path, *, use_lock: bool) -> str:
    return textwrap.dedent(
        f"""
        import sys, time
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from pathlib import Path
        import setup_hook, session_hooks, settings_lock

        setup_hook.CLAUDE_SETTINGS = Path({str(settings)!r})
        session_hooks.SETTINGS_LOCK = Path({str(lock)!r})
        if not {use_lock!r}:
            # Reproduce the pre-lock behaviour to prove the race is real.
            import contextlib
            @contextlib.contextmanager
            def unlocked(path, timeout=0.0):
                yield False
            settings_lock.exclusive = unlocked
            session_hooks.settings_lock.exclusive = unlocked

        for i in range({APPENDS_EACH}):
            session_hooks._append_self_heal_log("probe", sys.argv[1] + "-" + str(i))
            time.sleep(0.005)
        """
    )


def _run_workers(tmp_path: Path, *, use_lock: bool) -> int:
    settings = tmp_path / f"settings-{use_lock}.json"
    settings.write_text("{}", encoding="utf-8")
    lock = tmp_path / f"settings-{use_lock}.lock"
    script = tmp_path / f"worker-{use_lock}.py"
    script.write_text(_worker_source(settings, lock, use_lock=use_lock), encoding="utf-8")

    processes = [
        subprocess.Popen([sys.executable, str(script), f"w{index}"])
        for index in range(WORKERS)
    ]
    for process in processes:
        process.wait(timeout=120)

    data = json.loads(settings.read_text(encoding="utf-8"))
    return len(data.get("agentdeck", {}).get("selfHealLog", []))


def test_concurrent_appends_keep_every_entry(tmp_path: Path) -> None:
    assert _run_workers(tmp_path, use_lock=True) == WORKERS * APPENDS_EACH


def test_without_the_lock_the_same_run_loses_entries(tmp_path: Path) -> None:
    """The control. If this passes too, the machine simply did not interleave
    and the test above proved nothing about the lock."""
    kept = _run_workers(tmp_path, use_lock=False)

    assert kept < WORKERS * APPENDS_EACH, (
        f"expected lost entries without the lock, kept all {kept}"
    )
