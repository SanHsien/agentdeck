#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Fail the build when a module guarded by a growth policy creeps past its ceiling.

Ported from upstream `8d26748`. The code does not transfer — that guard watches
`menubar.py`, which this fork deleted — but the reasoning does: upstream split
that file twice and it grew back both times, because "keep this module small"
lived in a document and was enforced by nothing.

`wintray.py` is this fork's equivalent. It hosts the tray icon, the panel
windows, the JS shim, the update flow and the talent-market actions, and every
new feature is one more tempting method on the same class.

**Lower a ceiling whenever a cut lands; never raise one to make the build green.**
Raising it is how the policy dies: each raise is individually defensible and the
file is 3,000 lines a year later.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CEILINGS = {
    "wintray.py": 1900,
}


def main() -> int:
    failures: list[str] = []
    for name, ceiling in CEILINGS.items():
        path = REPO_ROOT / name
        if not path.is_file():
            # A guarded file that vanished means the guard is now a lie, which
            # is worse than no guard at all.
            failures.append(f"{name}: guarded file is missing")
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        headroom = ceiling - lines
        print(f"{name}: {lines}/{ceiling} lines ({headroom:+d})")
        if lines > ceiling:
            failures.append(
                f"{name}: {lines} lines exceeds the {ceiling}-line ceiling. "
                "Move the new logic into a leaf module instead of raising this limit."
            )

    for failure in failures:
        print(f"error: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
