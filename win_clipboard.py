# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Put text on the Windows clipboard.

Split out of `wintray.py` when the console-window fix pushed that file past the
ceiling `scripts/check_file_size.py` guards: its policy is to move logic into a
leaf module rather than raise the limit, and this is exactly that shape -- one
side effect, no window state, testable without a tray.

`clip.exe` reads its input as UTF-16LE, so the encoding is not incidental: hand
it UTF-8 and non-ASCII text lands on the clipboard as mojibake.
"""

from __future__ import annotations

import subprocess

from subprocess_utils import creation_flags

__all__ = ["copy_text"]


def copy_text(text: str) -> None:
    """Copy `text`, letting the caller decide what a failure means."""
    subprocess.run(  # noqa: S603 - fixed executable, text passed on stdin
        ["clip"],
        input=text.encode("utf-16-le"),
        check=False,
        shell=False,
        creationflags=creation_flags(),
    )
