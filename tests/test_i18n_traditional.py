# SPDX-License-Identifier: AGPL-3.0-only
"""Keep the zh-TW bundle actually written in Traditional Chinese.

This fork ships two languages, and Traditional Chinese is the maintainer's
own. It still carried 52 strings in Simplified -- "暂无数据", "加载数据",
"消息", "会话", "限额" -- inherited from upstream and invisible to every gate
in the build, because a wrong-script string is a perfectly valid string.

The check is a character blocklist, not a converter. It cannot know that
"分布" should be "分佈"; what it can do is fail the moment a Simplified-only
form reappears, which is exactly how these 52 arrived. Characters that exist
in both scripts (目, 置, 配, 段, 消, 加, 字, 周, 布, 余) are deliberately left
out -- a check that cries wolf on correct text gets switched off.

Scope is i18n.json's zh-TW section: the user-visible contract. Comments and
docstrings are not gated, because docs quoting upstream would trip it.
"""

from __future__ import annotations

import json
from pathlib import Path

I18N_PATH = Path(__file__).resolve().parent.parent / "i18n.json"

# Simplified-only forms whose Traditional counterpart is a different character.
SIMPLIFIED_ONLY = frozenset("个会创动历复导总报换据数无时暂条来检测滚览计话读转载长间项额")


def test_the_traditional_bundle_contains_no_simplified_characters() -> None:
    bundle = json.loads(I18N_PATH.read_text(encoding="utf-8"))

    offenders = [
        f"{key}: {value}  <- {''.join(sorted(SIMPLIFIED_ONLY & set(value)))}"
        for key, value in bundle["zh-TW"].items()
        if isinstance(value, str) and SIMPLIFIED_ONLY & set(value)
    ]

    assert not offenders, "zh-TW strings written in Simplified:\n" + "\n".join(offenders)


def test_the_blocklist_excludes_characters_shared_by_both_scripts() -> None:
    """A guard on the guard. Every one of these is correct Traditional and
    appears in shipped strings ("目前", "重置", "配額", "取消"); letting one
    into the blocklist would fail the build on good text and get this check
    deleted rather than fixed."""
    shared = set("目置配段消加字周布余退")

    overlap = SIMPLIFIED_ONLY & shared

    assert not overlap, f"characters shared by both scripts are in the blocklist: {overlap}"
