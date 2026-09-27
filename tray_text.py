# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""What the tray icon says: its badge text and its hover tooltip.

Split out of `wintray.py` when the tooltip grew a length cap and pushed that file
past the ceiling `scripts/check_file_size.py` guards. Both functions here are pure
-- state in, string out -- which is exactly the kind of logic that has no reason to
live next to the window plumbing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for typing only
    from state import menubar_state

# Shell_NotifyIcon's szTip holds 128 WCHARs including the terminator, and pystray
# raises ValueError past that. The raise lands inside the refresh path, so an
# over-long tooltip does not just truncate -- it stops the panel updating at all
# (upstream 8eacc3b). Four provider rows with localized window titles reach this.
TOOLTIP_MAX_LENGTH = 127


def tray_icon_style(used_percent: float | None) -> tuple[str, tuple[int, int, int, int]]:
    if used_percent is None:
        return ("--", (110, 118, 129, 255))
    remaining = max(0, min(100, round(100.0 - used_percent)))
    if remaining <= 20:
        color = (255, 69, 58, 255)
    elif remaining <= 50:
        color = (255, 196, 57, 255)
    else:
        color = (244, 145, 100, 255)
    return (str(remaining), color)


def build_tooltip(state: menubar_state.PopoverState) -> str:
    """One line per provider, showing the used share of each window.

    The number is what the panel shows -- `percent` is the used share, which is
    why `menubar_state` renders it through the `percent_used` string. The tray
    used to display `100 - percent`, so hovering the icon and opening the panel
    answered the same question with different numbers.
    """

    def value(row: menubar_state.QuotaRowState) -> str:
        if row.percent is None:
            return "--"
        return f"{max(0, round(row.percent))}%"

    def merged(
        name: str,
        session: menubar_state.QuotaRowState,
        weekly: menubar_state.QuotaRowState,
    ) -> str:
        return f"{name} {session.title}: {value(session)} · {weekly.title}: {value(weekly)}"

    lines = []
    # The panel hides the Claude section on request; a tooltip that still listed
    # it would put back exactly what the preference removes.
    if not state.hide_claude:
        lines.append(merged("Claude", state.claude_session, state.claude_weekly))
    lines.append(merged("Codex", state.codex_session, state.codex_weekly))
    lines.append(merged("Antigravity", state.agy_session, state.agy_weekly))
    if not state.hide_grok:
        lines.append(f"Grok {state.grok_weekly.title}: {value(state.grok_weekly)}")
    text = "\n".join(lines)
    if len(text) <= TOOLTIP_MAX_LENGTH:
        return text
    return text[: TOOLTIP_MAX_LENGTH - 1] + "…"
