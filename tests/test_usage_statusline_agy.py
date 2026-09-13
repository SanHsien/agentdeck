# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import usage_statusline_agy


@pytest.mark.parametrize(
    ("value", "expected"),
    [(999_499, "999k"), (999_500, "1.0M"), (999_949_999, "999.9M"), (999_950_000, "1.0B")],
)
def test_fmt_tokens_never_prints_a_unit_that_does_not_exist(value: int, expected: str) -> None:
    """The Antigravity line formats tokens the same way; upstream 45b27ee fixed both."""
    assert usage_statusline_agy.fmt_tokens(value) == expected


def test_render_localizes_effort_without_repeating_english_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "agy_statusline_input.json"
    data: dict[str, Any] = json.loads(fixture.read_text(encoding="utf-8"))
    monkeypatch.setenv("AGENTDECK_LANG", "zh-TW")

    rendered = usage_statusline_agy.render(data)

    assert "Gemini 3.6 Flash/速答" in rendered
    assert "(Low)" not in rendered
