# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Keep spawned processes from flashing a console window.

This is a tray app: it has no console of its own, so on Windows every
`subprocess` call that runs a console program (`git`, `claude`, `clip`, the
Antigravity CLI) pops a black window for as long as the child lives. One call
per project lookup or quota poll becomes a stream of flashes over a session, and
the panel can appear behind them. Ported from upstream `2a1996e`, which hit the
same thing.

Upstream returns a kwargs dict and unpacks it at the call site. This returns the
flag itself instead: `subprocess.run(..., creationflags=creation_flags())` type
checks against the overloads in `subprocess.pyi`, while `**{...}` does not, and
`creationflags=0` is valid on every platform -- only a *non-zero* value is
Windows-only.

The stdlib-only hooks installed into the user's environment
(`usage_session_resume.py`, `usage_statusline_forwarder.py`) cannot import this
-- they run under the system Python with no path to the project -- so they carry
their own copy. `tests/test_subprocess_hidden_console.py` pins both halves.
"""

from __future__ import annotations

import subprocess

__all__ = ["creation_flags"]


def creation_flags() -> int:
    """`CREATE_NO_WINDOW` on Windows, `0` (the default) everywhere else."""
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
