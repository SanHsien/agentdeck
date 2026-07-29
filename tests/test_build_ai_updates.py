# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_ai_updates", ROOT / "scripts" / "build_ai_updates.py"
)
assert _spec is not None and _spec.loader is not None
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def _data(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "generated_at": "2026-07-29",
        "tools": [
            {
                "id": "claude_code",
                "name": "Claude Code",
                "versions": [
                    {
                        "version": "2.1.219",
                        "period": "2026-07-24",
                        "items": [
                            {
                                "title": {"zh-TW": "標題", "en": "Title"},
                                "body": {"zh-TW": "內文 `x`", "en": "Body `x`"},
                                "original": "Original note",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    base.update(overrides)
    return base


def test_body_markup_is_escaped_before_code_spans_are_restored() -> None:
    # The data is third-party text. Escaping first and only re-enabling code
    # spans afterwards means a payload inside backticks stays inert.
    rendered = build.render_text("<script>alert(1)</script> and `<b>x</b>`")

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<code>&lt;b&gt;x&lt;/b&gt;</code>" in rendered


def test_only_the_two_shipped_languages_are_rendered() -> None:
    # The data carries five languages; rendering the three no locale can select
    # would triple the page for no reader.
    assert build.LANGUAGES == ("zh-TW", "en")

    page = build.render_page(_data())

    assert 'data-lang="zh-TW"' in page
    assert 'data-lang="en"' in page
    assert 'data-lang="ja"' not in page
    assert 'data-lang="ko"' not in page
    assert 'data-lang="zh-CN"' not in page


def test_traditional_chinese_is_the_visible_pane() -> None:
    page = build.render_page(_data())

    assert '<div class="pane" data-lang="zh-TW">' in page
    assert '<div class="pane" data-lang="en" hidden>' in page


@pytest.mark.parametrize(
    ("values", "language", "expected"),
    [
        ({"zh-TW": "中", "en": "E"}, "zh-TW", "中"),
        ({"en": "E"}, "zh-TW", "E"),  # missing translation falls back to English
        ({"ja": "J"}, "zh-TW", "J"),  # neither shipped language present
        ({}, "en", ""),
        ("plain", "en", "plain"),
    ],
)
def test_translation_fallback(values: Any, language: str, expected: str) -> None:
    assert build._pick(values, language) == expected


def test_a_version_without_items_says_so_instead_of_rendering_an_empty_list() -> None:
    data = _data()
    data["tools"][0]["versions"][0]["items"] = []

    page = build.render_page(data)

    assert "這個工具目前沒有收錄的更新。" in page
    assert "No updates recorded for this tool yet." in page


def test_render_is_deterministic() -> None:
    # No generation timestamp: rebuilding without a data change must produce a
    # byte-identical page, or every rebuild would churn the diff.
    data = _data()

    assert build.render_page(data) == build.render_page(data)


def test_checked_in_page_matches_the_checked_in_data() -> None:
    # Guards against the data being synced from upstream without rebuilding.
    data = json.loads((ROOT / "ai_updates.json").read_text(encoding="utf-8"))
    published = (ROOT / "docs" / "ai-updates" / "index.html").read_text(encoding="utf-8")

    assert build.render_page(data) == published


def test_page_is_self_contained() -> None:
    page = build.render_page(_data())

    # GitHub Pages serves this publicly; no third-party requests should ride along.
    assert "<script src=" not in page
    assert "<link rel=\"stylesheet\"" not in page
    assert "http://" not in page
