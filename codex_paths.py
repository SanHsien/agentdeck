# SPDX-License-Identifier: AGPL-3.0-only
"""One source of truth for where Codex keeps its local data.

Codex CLI honours ``CODEX_HOME``, and people who set it -- separate work and
personal accounts, a containerised Codex -- had every path in this app pointing
somewhere Codex never writes. The result was not an error but a blank: no
sessions, no rate limits, no Codex card, with nothing to say why.

Read at call time rather than captured at import, so a test can set the variable
and a caller gets the answer that is true now.
"""

from __future__ import annotations

import os
from pathlib import Path


def codex_home() -> Path:
    """Codex's data directory: ``CODEX_HOME`` when set, otherwise ``~/.codex``."""
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path(os.path.expanduser("~/.codex"))
