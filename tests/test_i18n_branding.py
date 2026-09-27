# SPDX-License-Identifier: AGPL-3.0-only
"""Guard the product name in user-visible strings.

De-branding this fork has leaked three times now, always the same way: the
Traditional Chinese string gets updated and the English one keeps saying
``usage``, or a string nobody thought of -- a single-instance dialog, a report
footer -- keeps the upstream name for months because nothing looks at it.

The check is narrow on purpose. The product name is always lowercase, so only
a standalone lowercase ``usage`` is treated as branding; ``Usage`` in title
case is the ordinary English noun and stays legal. The keys below genuinely
mean the noun in lowercase ("% of usage", "No token usage data") and are
listed one by one, so adding a new one is a deliberate act rather than a
silently widened pattern.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

I18N_PATH = Path(__file__).resolve().parent.parent / "i18n.json"

# The bare word here is the English noun, not the old product name.
NOUN_KEYS = frozenset(
    {
        "discussion_section_start",
        "history_load_error_file",
        "no_token_data",
        "report_empty_daily",
        "report_empty_models",
        "report_empty_projects",
        "report_insights_action_spike_share",
        "report_insights_shift_model_up",
        "report_insights_shift_model_up_plain",
        "report_insights_shift_new_project",
        "report_trend_compare_new",
    }
)

_BRAND = re.compile(r"(?<![\w-])usage(?![\w-])")


def test_no_user_visible_string_still_carries_the_upstream_product_name() -> None:
    bundle = json.loads(I18N_PATH.read_text(encoding="utf-8"))

    leaks = [
        f"[{language}] {key}: {value}"
        for language, section in bundle.items()
        for key, value in section.items()
        if isinstance(value, str) and key not in NOUN_KEYS and _BRAND.search(value)
    ]

    assert not leaks, "strings still say 'usage' where they mean the product:\n" + "\n".join(leaks)


def test_the_allowlist_does_not_outlive_the_strings_it_covers() -> None:
    """An allowlist entry whose string no longer contains the word is a hole:
    it would silently permit a future rewrite of that key to reintroduce the
    old name."""
    bundle = json.loads(I18N_PATH.read_text(encoding="utf-8"))

    stale = [
        key
        for key in NOUN_KEYS
        if not any(
            isinstance(section.get(key), str) and _BRAND.search(section[key])
            for section in bundle.values()
        )
    ]

    assert not stale, f"NOUN_KEYS entries no longer needed: {stale}"
