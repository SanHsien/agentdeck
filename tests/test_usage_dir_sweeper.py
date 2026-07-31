from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

import pytest

import main
import session_hooks
import usage_dir_sweeper
from usage_dir_sweeper import STALE_TEMP_AGE_SECONDS, sweep_stale_temp_files


def _make_old(path: Path, now: float) -> None:
    path.touch()
    old_time = now - STALE_TEMP_AGE_SECONDS
    os.utime(path, (old_time, old_time))


def test_sweeps_only_stale_matching_files(tmp_path: Path) -> None:
    now = 2_000_000_000.0
    stale = tmp_path / "tmpABC123.tmp"
    fresh = tmp_path / "tmpNEW456.tmp"
    _make_old(stale, now)
    fresh.touch()
    os.utime(fresh, (now, now))

    deleted = sweep_stale_temp_files(tmp_path, now=now)

    assert deleted == 1
    assert not stale.exists()
    assert fresh.exists()


def test_sweeps_direct_dot_d_child_but_keeps_cache_shards(tmp_path: Path) -> None:
    now = 2_000_000_000.0
    cache_dir = tmp_path / "history.d"
    cache_dir.mkdir()
    stale = cache_dir / "tmpCACHE.tmp"
    shard = cache_dir / "files-00.json"
    _make_old(stale, now)
    _make_old(shard, now)

    deleted = sweep_stale_temp_files(tmp_path, now=now)

    assert deleted == 1
    assert not stale.exists()
    assert shard.exists()


def test_keeps_nonmatching_names(tmp_path: Path) -> None:
    now = 2_000_000_000.0
    paths = [
        tmp_path / "important.tmp",
        tmp_path / "tmpfoo.json",
        tmp_path / "tmp_notes.txt",
    ]
    for path in paths:
        _make_old(path, now)

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert all(path.exists() for path in paths)


def test_keeps_matching_directory(tmp_path: Path) -> None:
    now = 2_000_000_000.0
    matching_directory = tmp_path / "tmpDIR.tmp"
    matching_directory.mkdir()

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert matching_directory.is_dir()


def test_keeps_matching_junction(tmp_path: Path) -> None:
    """A junction is the reparse point Windows lets an ordinary user create.

    Symlinks need Developer Mode or elevation, so this is the non-regular entry
    that can be exercised on a stock machine — same ``S_ISREG`` branch.
    """
    import _winapi

    now = 2_000_000_000.0
    target = tmp_path / "target_dir"
    target.mkdir()
    junction = tmp_path / "tmpJUNC.tmp"
    _winapi.CreateJunction(str(target), str(junction))

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert junction.is_junction()
    assert target.is_dir()


def test_keeps_matching_symlink(tmp_path: Path) -> None:
    """Needs symlink privilege; `tools/dev_check.ps1` deselects it when absent."""
    now = 2_000_000_000.0
    target = tmp_path / "target.txt"
    _make_old(target, now)
    link = tmp_path / "tmpLINK.tmp"
    link.symlink_to(target)

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert link.is_symlink()
    assert target.exists()


def test_does_not_recurse_below_direct_dot_d_child(tmp_path: Path) -> None:
    now = 2_000_000_000.0
    deep_dir = tmp_path / "history.d" / "sub"
    deep_dir.mkdir(parents=True)
    stale = deep_dir / "tmpDEEP.tmp"
    _make_old(stale, now)

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert stale.exists()


def test_missing_root_returns_zero_without_creating_it(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    assert sweep_stale_temp_files(missing, now=2_000_000_000.0) == 0
    assert not missing.exists()


def test_unlink_oserror_does_not_stop_other_deletions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = 2_000_000_000.0
    blocked = tmp_path / "tmpBLOCKED.tmp"
    removable = tmp_path / "tmpREMOVABLE.tmp"
    _make_old(blocked, now)
    _make_old(removable, now)
    original_unlink = Path.unlink

    def selective_unlink(path: Path, missing_ok: bool = False) -> None:
        if path == blocked:
            raise OSError("simulated unlink failure")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", selective_unlink)
    caplog.set_level(logging.WARNING)

    assert sweep_stale_temp_files(tmp_path, now=now) == 1
    assert blocked.exists()
    assert not removable.exists()
    assert caplog.records == []


def test_debug_mode_logs_file_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = 2_000_000_000.0
    blocked = tmp_path / "tmpBLOCKED.tmp"
    _make_old(blocked, now)
    monkeypatch.setenv("AGENTDECK_DEBUG", "1")

    def fail_unlink(_path: Path, missing_ok: bool = False) -> None:
        raise OSError

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    caplog.set_level(logging.WARNING)

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert "failed to inspect or remove stale temp file" in caplog.text


def test_main_self_heal_runs_sweeper_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(session_hooks, "self_heal", lambda: calls.append("hooks"))

    def fake_sweep() -> int:
        calls.append("sweeper")
        return 0

    monkeypatch.setattr(usage_dir_sweeper, "sweep_stale_temp_files", fake_sweep)

    main._self_heal()

    assert calls == ["hooks", "sweeper"]


def test_main_self_heal_swallows_sweeper_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_hooks, "self_heal", lambda: None)

    def fail() -> int:
        raise OSError("simulated sweep failure")

    monkeypatch.setattr(usage_dir_sweeper, "sweep_stale_temp_files", fail)

    main._self_heal()


def test_a_symlink_mode_is_skipped_without_needing_the_privilege(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover the symlink flavour on a machine that cannot create symlinks.

    Creating one needs SeCreateSymbolicLinkPrivilege, which an unelevated
    Windows session does not hold, so `test_keeps_matching_symlink` is
    deselected there and that input shape went untested locally.

    The branch under test reads `lstat().st_mode` and skips anything that is not
    a regular file, so reporting `S_IFLNK` for a real file exercises exactly
    that check. The file is genuinely stale and genuinely name-matching, so it
    *would* be deleted -- only the mode saves it, which is the behaviour being
    proven. What this cannot prove is that Windows reports `S_IFLNK` for a real
    symlink; that is CPython's contract, and `test_keeps_matching_symlink`
    covers it wherever the privilege exists.
    """
    now = 2_000_000_000.0
    disguised = tmp_path / "tmpLINK.tmp"
    _make_old(disguised, now)
    real_lstat = Path.lstat

    def lstat_as_symlink(self: Path, **kwargs: object) -> os.stat_result:
        result = real_lstat(self)
        if self.name != disguised.name:
            return result
        fields = list(result)
        fields[0] = (result.st_mode & ~stat.S_IFMT(result.st_mode)) | stat.S_IFLNK
        return os.stat_result(fields)

    monkeypatch.setattr(Path, "lstat", lstat_as_symlink)

    # sweep_stale_temp_files swallows every exception and returns 0, so a broken
    # helper would make the assertions below pass without exercising anything.
    # Check the disguise took effect first -- this test was green for that exact
    # wrong reason before `stat` was imported.
    assert stat.S_ISLNK(disguised.lstat().st_mode)

    assert sweep_stale_temp_files(tmp_path, now=now) == 0
    assert disguised.exists()


def test_the_same_file_without_the_disguise_is_swept(tmp_path: Path) -> None:
    """The control for the test above: without the mode change it is deleted.

    Without this, the symlink test would pass just as happily if the sweeper
    had stopped deleting anything at all.
    """
    now = 2_000_000_000.0
    ordinary = tmp_path / "tmpLINK.tmp"
    _make_old(ordinary, now)

    assert sweep_stale_temp_files(tmp_path, now=now) == 1
    assert not ordinary.exists()
