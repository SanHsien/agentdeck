# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from usage_lang import _detect_windows_lang, detect_lang


def _fake_windll(monkeypatch: pytest.MonkeyPatch, lang_id: int) -> None:
    windll = SimpleNamespace(
        kernel32=SimpleNamespace(GetUserDefaultUILanguage=lambda: lang_id)
    )
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)


def test_detect_lang_defaults_to_en_without_environment() -> None:
    assert detect_lang({}) == "en"


def test_detect_lang_reads_lang_zh_tw_locale() -> None:
    assert detect_lang({"AGENTDECK_LANG": "zh_TW.UTF-8"}) == "zh-TW"


def test_detect_lang_reads_zh_hant_locale() -> None:
    assert detect_lang({"AGENTDECK_LANG": "zh-Hant-TW"}) == "zh-TW"


def test_detect_lang_reads_zh_hk_locale_as_traditional() -> None:
    assert detect_lang({"AGENTDECK_LANG": "zh_HK.UTF-8"}) == "zh-TW"


@pytest.mark.parametrize("code", ["zh_CN.UTF-8", "zh-Hans", "zh-Hans-CN", "zh_SG", "zh"])
def test_detect_lang_maps_every_chinese_variant_to_traditional(code: str) -> None:
    # The UI ships Traditional Chinese and English only. A Simplified Chinese
    # reader is better served by zh-TW than by falling through to English.
    assert detect_lang({"AGENTDECK_LANG": code}) == "zh-TW"


@pytest.mark.parametrize("code", ["ja", "ko", "de_DE.UTF-8", "fr-FR"])
def test_detect_lang_unshipped_language_falls_back_to_en(code: str) -> None:
    assert detect_lang({"AGENTDECK_LANG": code}) == "en"


def test_detect_lang_prefers_usage_lang_over_tt_lang() -> None:
    assert detect_lang({"AGENTDECK_LANG": "zh-TW", "TT_LANG": "en"}) == "zh-TW"
    assert detect_lang({"AGENTDECK_LANG": "en", "TT_LANG": "zh-TW"}) == "en"


def test_detect_lang_prefers_usage_lang_over_tt_lang_and_lang() -> None:
    env = {"AGENTDECK_LANG": "en", "TT_LANG": "zh-TW"}
    assert detect_lang(env) == "en"


def test_lang_from_the_shell_is_ignored() -> None:
    """Git Bash and MSYS export LANG=en_US.UTF-8 regardless of the machine.
    Honouring it meant a zh-TW system launched from Git Bash came up in
    English, with nothing on screen to explain why. The system UI language and
    the two explicit overrides are the only things that decide this.
    """
    assert detect_lang({"LANG": "zh_TW.UTF-8"}) == "en"
    assert detect_lang({"TT_LANG": "zh-TW", "LANG": "en_US.UTF-8"}) == "zh-TW"


@pytest.mark.parametrize(
    ("lang_id", "expected"),
    [
        (1028, "zh-TW"),  # zh_TW
        (2052, "zh-TW"),  # zh_CN — Simplified folds into Traditional
        (1041, "en"),  # ja_JP — not shipped, falls back
        (1042, "en"),  # ko_KR — not shipped, falls back
        (1033, "en"),  # en_US
    ],
)
def test_detect_windows_lang_maps_ui_language_ids(
    monkeypatch: pytest.MonkeyPatch, lang_id: int, expected: str
) -> None:
    _fake_windll(monkeypatch, lang_id)

    assert _detect_windows_lang() == expected


def test_detect_windows_lang_unknown_id_falls_back_to_en(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_windll(monkeypatch, 0x7FFF)

    assert _detect_windows_lang() == "en"


def test_detect_windows_lang_without_windll_falls_back_to_en(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ctypes, "windll", None, raising=False)

    assert _detect_windows_lang() == "en"


def test_detect_lang_uses_windows_ui_language_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("AGENTDECK_LANG", "TT_LANG", "LANG"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    _fake_windll(monkeypatch, 1028)

    assert detect_lang() == "zh-TW"


def test_detect_lang_env_var_beats_windows_ui_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTDECK_LANG", "en")
    monkeypatch.setattr(sys, "platform", "win32")
    _fake_windll(monkeypatch, 1028)  # system says zh-TW

    assert detect_lang() == "en"


def test_no_shipped_script_consults_lang() -> None:
    """The language lookup is copy-pasted into five standalone hook scripts
    because they must run on a bare system Python with no imports of ours. One
    copy left honouring LANG is a hook that disagrees with the app about what
    language the user reads, and nothing else in the suite would notice.
    """
    root = Path(__file__).resolve().parent.parent
    scripts = [root / "usage_lang.py", *sorted(root.glob("usage_statusline*.py")),
               root / "usage_session_resume.py", *sorted(root.glob("usage_terse*.py"))]

    offenders = [
        script.name
        for script in scripts
        if '"LANG"' in script.read_text(encoding="utf-8").split("# LANG is deliberately")[-1]
    ]

    assert not offenders, f"these still read the shell's LANG: {offenders}"
