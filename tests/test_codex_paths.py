# SPDX-License-Identifier: AGPL-3.0-only
"""Codex's data directory follows CODEX_HOME.

Someone who sets it -- separate work and personal accounts, a containerised
Codex -- previously got no Codex data at all from this app, and no error either:
every path pointed at ``~/.codex``, which in that setup is empty or absent. A
blank card reads as "Codex has no usage", not as "we looked in the wrong place".
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import codex_paths


def test_codex_home_prefers_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", "D:/work/codex")

    assert codex_paths.codex_home() == Path("D:/work/codex")


def test_codex_home_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)

    assert codex_paths.codex_home() == Path.home() / ".codex"


def test_an_empty_value_is_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """CODEX_HOME= in a shell profile means "no override", not "use the root"."""
    monkeypatch.setenv("CODEX_HOME", "")

    assert codex_paths.codex_home() == Path.home() / ".codex"


def test_a_user_relative_override_is_expanded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", "~/codex-work")

    assert codex_paths.codex_home() == Path.home() / "codex-work"


@pytest.mark.parametrize(
    ("module_name", "attribute", "suffix"),
    [
        ("providers.codex_loader", "SESSIONS_DIR", "sessions"),
        ("providers.codex_loader", "ARCHIVED_SESSIONS_DIR", "archived_sessions"),
        ("providers.codex_loader", "STATE_DB", "state_5.sqlite"),
        ("providers.codex_loader", "LOGS_DB", "logs_2.sqlite"),
        ("setup_hook", "CODEX_CONFIG", "config.toml"),
        ("setup_hook", "CODEX_BACKUP", "agentdeck-backup.json"),
        ("session_hooks", "CODEX_HOOKS_JSON", "hooks.json"),
        ("session_hooks", "CODEX_TERSE_HOOK_TARGET", "agentdeck-terse-mode.py"),
        ("persona_store", "CODEX_DIR", ""),
    ],
)
def test_every_codex_path_follows_the_override(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    attribute: str,
    suffix: str,
) -> None:
    """One missed constant is a half-working install: sessions read from the
    override while the hook is written to the default, and neither side says so.

    The constants are computed at import, so the module is reloaded here -- that
    is also the honest statement of the limit: changing CODEX_HOME while the app
    is running does not move these paths until it restarts.
    """
    override = Path("D:/work/codex")
    monkeypatch.setenv("CODEX_HOME", str(override))
    module = importlib.reload(importlib.import_module(module_name))
    try:
        value = Path(str(getattr(module, attribute)))

        assert value == (override / suffix if suffix else override)
    finally:
        monkeypatch.delenv("CODEX_HOME", raising=False)
        importlib.reload(module)
