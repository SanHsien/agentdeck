# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

from usage_lang import detect_lang


def packaged_resource_path(filename: str, source_mode_path: Path) -> Path:
    """Resolve a data file across source-mode and PyInstaller-bundle layouts.

    Why this exists: in a frozen build this module lives inside the bundle, so
    ``Path(__file__).with_name("i18n.json")`` points at a path through an
    archive rather than at a readable file. PyInstaller sets ``sys._MEIPASS`` to
    the directory it unpacked the declared data files into, so that is checked
    first; in source mode (and in tests) the attribute is absent and the
    source-adjacent path is the correct answer.

    Callers pass the source-mode path explicitly, as the literal
    ``Path(__file__).with_name("...")``, so ``tests/test_packaged_resources.py``
    can statically find every declared resource and check that
    ``scripts/build_windows.ps1`` bundles it under the name asked for here.

    py2app's ``RESOURCEPATH`` was consulted here until macOS support was removed
    on 2026-07-29; nothing sets that variable now.
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        bundled = Path(frozen_root) / filename
        if bundled.exists():
            return bundled
    return source_mode_path


I18N_PATH = packaged_resource_path("i18n.json", Path(__file__).with_name("i18n.json"))


@lru_cache(maxsize=1)
def _load_i18n_bundle() -> dict[str, dict[str, str]]:
    data = json.loads(I18N_PATH.read_text(encoding="utf-8"))
    return {
        str(lang): {str(key): str(value) for key, value in values.items()}
        for lang, values in data.items()
    }


def _t(language: str, key: str, **kwargs: object) -> str:
    bundle = _load_i18n_bundle()
    table = bundle.get(language) or bundle["en"]
    template = table.get(key) or bundle["en"].get(key) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError, TypeError):
        # A malformed placeholder in one locale's string must not crash the UI;
        # fall back to the English template, then to the raw key.
        en_template = bundle["en"].get(key)
        if en_template is not None and en_template != template:
            try:
                return en_template.format(**kwargs)
            except (KeyError, IndexError, ValueError, TypeError):
                pass
        return key


def t(key: str, **kwargs: object) -> str:
    return _t(detect_lang(), key, **kwargs)
