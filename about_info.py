# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>

from __future__ import annotations

from i18n import _t

PROJECT_HOMEPAGE = "https://github.com/SanHsien/agentdeck"


def text(language: str, version: str) -> str:
    """Build the localized About text shown by every Windows entry point."""
    return _t(language, "about_body", version=version, website=PROJECT_HOMEPAGE)
