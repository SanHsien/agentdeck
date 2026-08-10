# SPDX-License-Identifier: AGPL-3.0-only
"""A cross-process lock for read-modify-write cycles on the settings file.

``settings.json`` is edited by more than one process: the tray app self-heals
its hooks while a ``--setup`` run or a second launch may be rewriting the same
file. Each edit is load -> modify -> save, and the save is atomic on its own,
which is exactly what makes the race invisible: no file is ever corrupt, the
later writer simply serialises a copy it read before the earlier one landed, and
the earlier edit disappears with nothing to show it was lost.

The lock lives in its own file rather than sharing the status line's. That one
is taken on every status-line refresh -- several times a minute -- and a settings
edit queueing behind it would be waiting on traffic it has nothing to do with.

Windows has no ``flock``. ``msvcrt.locking`` is the native equivalent, but it
offers only "retry on a one-second granularity" or "fail instantly", so the
contended case is polled here. The same approach is already proven in
``usage_statusline.py``; that copy is deliberately not shared, because the hook
scripts are copied to ``~/.claude`` and executed by whatever ``python3`` the
user's Claude Code finds, with no package around them to import from.
"""

from __future__ import annotations

import errno
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_fcntl: Any = None
_msvcrt: Any = None
if sys.platform == "win32":
    try:
        import msvcrt as _msvcrt_module
    except ImportError:
        pass
    else:
        _msvcrt = _msvcrt_module
else:
    try:
        import fcntl as _fcntl_module
    except ImportError:
        pass
    else:
        _fcntl = _fcntl_module

LOCK_TIMEOUT_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.001
# msvcrt.locking reports a contended byte as EACCES; EDEADLOCK is what it raises
# once its own internal retries are exhausted.
_CONTENDED = frozenset(
    (errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK), errno.EDEADLK)
)


def _acquire_windows(lock_fd: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        try:
            if os.fstat(lock_fd).st_size == 0:
                os.write(lock_fd, b"\0")
            os.lseek(lock_fd, 0, os.SEEK_SET)
            _msvcrt.locking(lock_fd, _msvcrt.LK_NBLCK, 1)
            return True
        except OSError as exc:
            if exc.errno not in _CONTENDED:
                # Locking is unsupported on this descriptor or filesystem;
                # spinning would not help.
                return False
            if time.monotonic() >= deadline:
                return False
            time.sleep(_POLL_INTERVAL_SECONDS)


@contextmanager
def exclusive(lock_path: Path, *, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[bool]:
    """Hold an exclusive lock for the block, yielding whether it was obtained.

    Yields ``False`` rather than raising when the platform cannot lock: losing
    an edit is bad, refusing to install a hook because a lock file could not be
    opened is worse. Callers that care can act on the flag; the default is to
    proceed exactly as the code did before there was a lock.
    """
    lock_fd: int | None = None
    locked = False
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        yield False
        return

    try:
        if _fcntl is not None:
            try:
                _fcntl.flock(lock_fd, _fcntl.LOCK_EX)
                locked = True
            except OSError:
                locked = False
        elif _msvcrt is not None:
            locked = _acquire_windows(lock_fd, timeout)
        yield locked
    finally:
        if locked:
            try:
                if _fcntl is not None:
                    _fcntl.flock(lock_fd, _fcntl.LOCK_UN)
                elif _msvcrt is not None:
                    os.lseek(lock_fd, 0, os.SEEK_SET)
                    _msvcrt.locking(lock_fd, _msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        os.close(lock_fd)
