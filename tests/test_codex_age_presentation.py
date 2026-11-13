# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

"""Old local Codex readings are informational; failed quota fetches still warn."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from i18n import _t

PANELS = Path(__file__).resolve().parents[1] / "assets" / "panels"


@pytest.mark.parametrize("theme", ["classic", "catppuccin", "origami", "stained_glass"])
def test_only_codex_age_is_quiet(theme: str) -> None:
    html = (PANELS / f"{theme}.html").read_text(encoding="utf-8")
    for marker in ("codex-stale", "agy-stale", "grok-stale", "history-error"):
        label = html.split(f"data-{marker} hidden>", 1)[1].split("</div>", 1)[0]
        assert ("⚠" in label) == (marker != "codex-stale")
        assert f"data-{marker}-tooltip" in label
    quiet_rule = re.search(r"\[data-codex-stale\]\s*\{([^}]+)\}", html)
    assert quiet_rule is not None
    assert "color: var(--muted)" in quiet_rule[1]
    # The shared warning class must keep its original color for failed fetches.
    warning_rule = re.search(r"\.codex-stale\s*\{([^}]+)\}", html)
    assert warning_rule is not None
    assert "color: var(--warn)" in warning_rule[1]
    # Same specificity: the quiet rule only wins when it comes after the warning rule.
    assert quiet_rule.start() > warning_rule.start()


@pytest.mark.parametrize(
    ("lang", "minutes", "hours", "session"),
    [
        ("zh-TW", "約 1 分鐘前更新", "約 1 小時前更新", "5 小時"),
        ("en", "updated about 1 min ago", "updated about 1 hr ago", "Session"),
    ],
)
def test_codex_age_describes_last_update(
    lang: str, minutes: str, hours: str, session: str
) -> None:
    assert _t(lang, "codex_stale_minutes", minutes=1) == minutes
    assert _t(lang, "codex_stale_hours", hours=1) == hours
    assert _t(lang, "session_label") == session
