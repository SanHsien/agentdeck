# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty
# disclaimer.

"""Backend for the "AI 人才市場" panel.

Upstream implemented this by shelling out to ``vendor/instate-cli``, a binary
built from a private project on the author's machine. Its source repo and its
distribution repo are both 404 to everyone else, and the artifact is a macOS
executable, so the feature was unreachable from a public clone on either
platform. This fork replaced that binary with :mod:`persona_store`, which reads
role definitions from ``personas/*.json`` in this repository.

This module stays as the panel's entry point so neither the panel nor the AI
Council picker had to change. Every function returns a dict and never raises, so
a malformed pack degrades to an empty-state panel instead of taking the tray down
with it. Folder and file pickers are the host's job — the tray owns those dialogs
(see ``discussion_window_win``), because they are platform-specific and this
module is not.
"""

from __future__ import annotations

import logging
from typing import Any

import persona_store

logger = logging.getLogger(__name__)


def _guard(operation: str, call: Any, *args: Any) -> dict[str, Any]:
    """Run a store call, converting any failure into an error payload."""
    try:
        result = call(*args)
    except Exception as exc:  # noqa: BLE001 - the panel must never crash the tray
        logger.warning("persona store %s failed", operation, exc_info=True)
        return {"ok": False, "status": "error", "error": str(exc)}
    return result if isinstance(result, dict) else {"ok": False, "status": "error"}


def list_state(lang: str | None = None) -> dict[str, Any]:
    return _guard("list_state", persona_store.list_state, lang)


def list_personas(lang: str | None = None) -> list[dict[str, str]]:
    """Flat role records for the AI Council persona picker."""
    try:
        return persona_store.list_personas(lang)
    except Exception:  # noqa: BLE001 - an empty picker beats a broken window
        logger.warning("persona listing failed", exc_info=True)
        return []


def install_role(role_id: str, lang: str | None = None) -> dict[str, Any]:
    return _guard("install_role", persona_store.install_role, role_id, lang)


def uninstall_role(role_id: str) -> dict[str, Any]:
    return _guard("uninstall_role", persona_store.uninstall_role, role_id)


def restore_role(role_id: str) -> dict[str, Any]:
    return _guard("restore_role", persona_store.restore_role, role_id)


def ignore_drift(role_id: str) -> dict[str, Any]:
    return _guard("ignore_drift", persona_store.ignore_drift, role_id)


def set_folder(role_id: str, path: str) -> dict[str, Any]:
    return _guard("set_folder", persona_store.set_folder, role_id, path)
