# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Read-only probes for the session-hook toggles the tray menu shows as checked.

Leaf module split out of `wintray.py` (see `scripts/check_file_size.py`): both
probes swallow every error and report "off", because a menu that cannot read the
hook settings must still render.
"""

from __future__ import annotations


def _session_resume_enabled() -> bool:
    try:
        import session_hooks

        return session_hooks.is_resume_enabled()
    except Exception:
        return False


def _terse_mode_enabled() -> bool:
    try:
        import session_hooks

        return session_hooks.is_terse_mode_enabled()
    except Exception:
        return False
