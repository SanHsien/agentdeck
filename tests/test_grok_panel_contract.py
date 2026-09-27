# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

from pathlib import Path

import wintray
from panels.payload import _state_payload
from state import menubar_state

PANELS_DIR = Path(__file__).resolve().parent.parent / "assets" / "panels"


def test_every_quota_panel_has_a_grok_card_and_stale_hooks() -> None:
    for _panel_id, _key, filename in wintray.available_panels():
        html = (PANELS_DIR / filename).read_text(encoding="utf-8")
        assert 'data-card="grok"' in html, filename
        assert "data-grok-stale" in html, filename
        assert "data-grok-stale-age" in html, filename
        assert "data-grok-stale-tooltip" in html, filename
        assert '.hide-grok [data-card="grok"]' in html, filename
        assert "--grok:" in html, filename


def test_panel_core_treats_grok_as_a_quota_card() -> None:
    core = (PANELS_DIR / "panel_core.js").read_text(encoding="utf-8")
    assert 'QUOTA_CARD_IDS = ["claude", "codex", "agy", "grok"]' in core
    assert "function renderGrok" in core
    assert "hide-grok" in core
    assert "state.hideGrok" in core


def test_state_payload_includes_available_and_hidden_grok() -> None:
    weekly = menubar_state.QuotaRowState(
        title="Weekly",
        percent=60.0,
        percent_text="60% used",
        reset_text="Resets in 1d",
        color=menubar_state.GROK_COLOR,
    )
    missing = menubar_state._missing_row("Weekly", menubar_state.CLAUDE_COLOR, "en")
    visible = menubar_state.PopoverState(
        language="en",
        claude_session=missing,
        claude_weekly=missing,
        codex_session=missing,
        codex_weekly=missing,
        agy_session=missing,
        agy_weekly=missing,
        agy_group_name="",
        grok_weekly=weekly,
        projects=[],
        projects_7d=[],
        projects_30d=[],
        projects_all=[],
        rate_text="",
        status_text="",
        today_text="",
        statusline={},
        hide_grok=False,
        grok_stale={"ageText": "about 40 minutes ago"},
    )
    payload = _state_payload(visible)
    grok = payload["grok"]
    assert isinstance(grok, dict)
    weekly = grok["weekly"]
    assert isinstance(weekly, dict)
    card_order = payload["cardOrder"]
    assert isinstance(card_order, list)

    assert weekly["percent"] == 60.0
    assert grok["stale"] == {"ageText": "about 40 minutes ago"}
    assert payload["hideGrok"] is False
    assert card_order[-1] == "grok"

    visible.hide_grok = True
    assert _state_payload(visible)["hideGrok"] is True
