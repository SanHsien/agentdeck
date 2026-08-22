# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Shared JSONL line-size limit and bounded binary reader.

Session logs are written by other programs and are not a trusted input: a single
line has no upper bound, so `readline()` will happily materialise a multi-GB
string and take the process down. Every JSONL read path goes through
`read_bounded_jsonl_line`, which drains an oversized line instead of holding it.

Taken from upstream 2588cc0, with one addition the fork needs: `on_skipped_bytes`
(see the parameter docstring).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import BinaryIO

# 64 MiB. Upstream picked it from measured real-world data, where the largest
# single line was 23 MB; the limit is a blast radius, not a target.
MAX_JSONL_LINE_BYTES = 64 * 1024 * 1024

_DRAIN_CHUNK_BYTES = 65536


def read_bounded_jsonl_line(
    file: BinaryIO,
    *,
    on_skipped_bytes: Callable[[bytes], None] | None = None,
) -> tuple[bytes, bool]:
    """Read one line, draining and flagging it when it exceeds the shared limit.

    Returns ``(line, too_long)``. An oversized line is consumed to its newline
    and reported as ``(b"", True)`` so callers can log and continue; end of file
    is ``(b"", False)``.

    ``on_skipped_bytes`` receives the bytes of a drained line as they are read.
    The incremental caches in `providers/history_loader` and
    `providers/codex_loader` keep a rolling digest of the *confirmed prefix* and
    re-verify it by hashing the file from offset 0 on the next run. Advancing the
    confirmed offset past a drained line without hashing what was skipped makes
    the stored digest permanently disagree with the file, so the cache would miss
    on every run — the parse stays correct, but the whole incremental path
    silently stops working.
    """
    line = file.readline(MAX_JSONL_LINE_BYTES + 1)
    if len(line) <= MAX_JSONL_LINE_BYTES:
        return line, False

    while True:
        if on_skipped_bytes is not None and line:
            on_skipped_bytes(line)
        if not line or line.endswith(b"\n"):
            return b"", True
        line = file.readline(_DRAIN_CHUNK_BYTES)
