# SPDX-License-Identifier: AGPL-3.0-only
"""Which panels exist, how tall they open, and which of them are themes.

Split out of ``wintray`` to keep that file under its size ceiling. ``wintray``
re-exports every name here, so ``wintray.PANEL_HEIGHTS`` and
``wintray.available_panels()`` keep working for callers and tests.
"""

from __future__ import annotations

WINDOWS_PANELS = (
    ("classic", "panel_default_name", "classic.html"),
    ("matrix", "panel_matrix", "matrix.html"),
    ("win95", "panel_win95", "win95.html"),
    ("newspaper", "panel_newspaper", "newspaper.html"),
    ("cloud_observation", "panel_cloud_observation", "cloud_observation.html"),
    ("aquarium", "panel_aquarium", "aquarium.html"),
    ("prism_arcade", "panel_prism_arcade", "prism_arcade.html"),
    ("black_hole", "panel_black_hole", "black_hole.html"),
    ("lepidoptera", "panel_lepidoptera", "lepidoptera.html"),
)
# The talent market is a feature screen, not a theme: it shows role cards and
# installs them, and displays no quota at all. Listing it among the themes made
# the theme list lie about what it offers, and let a user land in it by picking
# what looked like a skin. It keeps a panel id because the same window renders
# it, but it is reached from the tray menu and is never restored at startup.
TALENT_PANEL = ("talent_market", "panel_talent_market", "talent_market.html")

# Placeholder heights only: the window opens at these and is corrected the
# moment the WebView reports its real content height. Wrong values cost a
# visible jump on every open -- too small clips, too large leaves a band of
# empty panel.
#
# Measured against this fork's own panels rather than inherited: 2026-08-10,
# Windows 11 at 225% DPI, mock data, reading the height the page reports before
# it is clamped to the work area. Upstream recalibrated the same table against
# macOS, and those numbers describe different panels drawn by a different
# engine.
#
# talent_market keeps its previous value on purpose: it measured 108 under mock
# data because no personas render there, which says nothing about the height it
# needs once the shipped role cards are present.
PANEL_HEIGHTS = {
    "classic": 1026,
    "matrix": 1051,
    "win95": 1045,
    "newspaper": 1045,
    "cloud_observation": 1009,
    "aquarium": 1009,
    "prism_arcade": 1011,
    "black_hole": 1009,
    "lepidoptera": 1046,
    "talent_market": 812,
}


def available_panels() -> tuple[tuple[str, str, str], ...]:
    """The switchable themes -- what the panel menu and tray submenu offer."""
    return WINDOWS_PANELS


def renderable_panels() -> tuple[tuple[str, str, str], ...]:
    """Everything the panel window can load: the themes plus the talent market.

    Kept separate from available_panels() so the feature screen stays out of the
    theme list without becoming unreachable, and so a saved active panel of
    "talent_market" is not restored at startup.
    """
    return (*WINDOWS_PANELS, TALENT_PANEL)
