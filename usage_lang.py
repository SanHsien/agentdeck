# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import os
import sys
from collections.abc import Mapping


def _normalize_lang(code: str | None) -> str:
    """Map any locale code onto one of the two shipped UI languages.

    The UI ships Traditional Chinese and English only. Every Chinese variant
    resolves to zh-TW — a Simplified Chinese reader is far better served by
    Traditional Chinese than by English — and everything else falls back to
    English.
    """
    if not code:
        return "en"
    normalized = code.split(".")[0].strip().lower().replace("_", "-")

    if normalized == "zh" or normalized.startswith("zh-"):
        return "zh-TW"
    return "en"


def _detect_windows_lang() -> str:
    try:
        import ctypes
        import locale

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return "en"
        lang_id = int(windll.kernel32.GetUserDefaultUILanguage())
        return _normalize_lang(locale.windows_locale.get(lang_id))
    except Exception:
        return "en"


def detect_lang(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    for key in ("USAGE_LANG", "TT_LANG", "LANG"):
        value = source.get(key, "").strip()
        if value:
            return _normalize_lang(value)
    if env is None and sys.platform == "win32":
        return _detect_windows_lang()
    return "en"
