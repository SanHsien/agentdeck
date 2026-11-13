# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import usage_statusline_agy


@pytest.mark.parametrize(("lang", "label"), [("zh-TW", "深思熟慮"), ("en", "Extended")])
@pytest.mark.parametrize("explicit", [True, False])
def test_render_localizes_xhigh_effort(
    monkeypatch: pytest.MonkeyPatch, lang: str, label: str, explicit: bool,
) -> None:
    monkeypatch.setenv("AGENTDECK_LANG", lang)
    model = {"display_name": "Gemini 4 Hydrogen (XHigh)"}
    if explicit:
        model["effort"] = "xhigh"
    rendered = usage_statusline_agy.render({"model": model})
    assert f"Gemini 4 Hydrogen/{label}" in rendered
    assert "(XHigh)" not in rendered


def test_xhigh_fallback_matches_translation_bundle() -> None:
    bundle = json.loads((Path(__file__).parents[1] / "i18n.json").read_text(encoding="utf-8"))
    for lang in ("zh-TW", "en"):
        assert usage_statusline_agy.STATUSLINE_TRANSLATIONS[lang]["effort_xhigh"] == (
            bundle[lang]["agy_effort_xhigh"]
        )


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


def test_render_groups_quota_above_model_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = Path(__file__).parent / "fixtures" / "agy_statusline_input.json"
    data: dict[str, Any] = json.loads(fixture.read_text(encoding="utf-8"))
    data["terminal_width"] = 80
    monkeypatch.setenv("AGENTDECK_LANG", "en")

    first, second = usage_statusline_agy.render(data).split("\n")

    assert "project" in first
    assert "60%" in first
    assert "Context:" not in first
    assert "Gemini 3.6 Flash/Quick" in second
    assert "Context:" in second


@pytest.mark.parametrize("data", [{}, {"model": {"id": "Gemini"}}])
def test_render_does_not_add_blank_lines(data: dict[str, Any]) -> None:
    rendered = usage_statusline_agy.render(data)
    assert rendered
    assert "\n" not in rendered
