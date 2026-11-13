from __future__ import annotations

import json
import re
from datetime import datetime, tzinfo
from pathlib import Path

import pytest

import pricing
import usage_statusline_agy
import usage_terse_mode
import usage_terse_reminder
from ui.tables import MODEL_SHORT


@pytest.mark.parametrize(
    ("lang", "floor", "structure"),
    [("zh-TW", "讀一遍就懂", "因為、所以、但是、如果"),
     ("en", "clear on a first read", "because/so/but/if")],
)
def test_terse_preserves_readability(lang: str, floor: str, structure: str) -> None:
    instruction = usage_terse_mode._DEFAULT_INSTRUCTION[lang]
    assert floor in instruction
    assert structure in instruction
    assert floor in usage_terse_reminder._DEFAULT_REMINDER[lang]


def test_fable_52_offline_price_and_short_name() -> None:
    fallback = pricing._fallback_pricing()
    assert fallback["claude-fable-5-2"] == {
        "input_cost_per_token": 8e-6,
        "output_cost_per_token": 40e-6,
        "cache_creation_input_token_cost": 10e-6,
        "cache_read_input_token_cost": 0.2e-6,
    }
    assert pricing._resolve_model_key("claude-fable-5-1", fallback) == "claude-fable-5-1"
    assert MODEL_SHORT["claude-fable-5-2"] == "Fable 5.2"


@pytest.mark.parametrize(
    ("lang", "expected_five", "expected_weekly"),
    [("zh-TW", "14:40(剩2h", "11/14 18:00(剩4d"),
     ("en", "14:40(2h", "11/14 18:00(4d")],
)
def test_agy_reset_clock(
    monkeypatch: pytest.MonkeyPatch, lang: str, expected_five: str, expected_weekly: str
) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> FixedDatetime:
            value = cls(2026, 11, 10, 11, 56)
            return value if tz is None else value.astimezone(tz)

    monkeypatch.setattr(usage_statusline_agy, "datetime", FixedDatetime)
    monkeypatch.setenv("AGENTDECK_LANG", lang)
    fixture = Path(__file__).parent / "fixtures" / "agy_statusline_input.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    data["terminal_width"] = 300
    data["model"]["id"] = "Gemini 3.6 Flash"
    data["quota"] = {
        "gemini-5h": {"remaining_fraction": 0.6, "reset_in_seconds": 2 * 3600 + 44 * 60},
        "gemini-weekly": {
            "remaining_fraction": 0.7,
            "reset_in_seconds": 4 * 86400 + 6 * 3600 + 4 * 60,
        },
    }
    rendered = usage_statusline_agy.render(data)
    output = re.sub(r"\x1b\[[0-9;]*m", "", rendered)
    assert expected_five in output
    assert expected_weekly in output
    data["terminal_width"] = 60
    narrow = usage_statusline_agy.render(data)
    assert "14:40" not in narrow
    assert "18:00" not in narrow
