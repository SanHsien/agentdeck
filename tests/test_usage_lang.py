# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import ctypes
import sys
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
    assert detect_lang({"LANG": "zh_TW.UTF-8"}) == "zh-TW"


def test_detect_lang_reads_zh_hant_locale() -> None:
    assert detect_lang({"LANG": "zh-Hant-TW"}) == "zh-TW"


def test_detect_lang_reads_zh_hk_locale_as_traditional() -> None:
    assert detect_lang({"LANG": "zh_HK.UTF-8"}) == "zh-TW"


@pytest.mark.parametrize("code", ["zh_CN.UTF-8", "zh-Hans", "zh-Hans-CN", "zh_SG", "zh"])
def test_detect_lang_maps_every_chinese_variant_to_traditional(code: str) -> None:
    # The UI ships Traditional Chinese and English only. A Simplified Chinese
    # reader is better served by zh-TW than by falling through to English.
    assert detect_lang({"LANG": code}) == "zh-TW"


@pytest.mark.parametrize("code", ["ja", "ko", "de_DE.UTF-8", "fr-FR"])
def test_detect_lang_unshipped_language_falls_back_to_en(code: str) -> None:
    assert detect_lang({"LANG": code}) == "en"


def test_detect_lang_prefers_usage_lang_over_tt_lang() -> None:
    assert detect_lang({"USAGE_LANG": "zh-TW", "TT_LANG": "en"}) == "zh-TW"
    assert detect_lang({"USAGE_LANG": "en", "TT_LANG": "zh-TW"}) == "en"


def test_detect_lang_prefers_usage_lang_over_tt_lang_and_lang() -> None:
    env = {"USAGE_LANG": "en", "TT_LANG": "zh-TW", "LANG": "zh_TW.UTF-8"}
    assert detect_lang(env) == "en"


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
    for key in ("USAGE_LANG", "TT_LANG", "LANG"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    _fake_windll(monkeypatch, 1028)

    assert detect_lang() == "zh-TW"


def test_detect_lang_env_var_beats_windows_ui_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USAGE_LANG", "en")
    monkeypatch.setattr(sys, "platform", "win32")
    _fake_windll(monkeypatch, 1028)  # system says zh-TW

    assert detect_lang() == "en"
