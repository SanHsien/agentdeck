from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import ResumeHookPaths, SetupHookPaths, TerseHookPaths
from tests.helpers import patch_resume_hook_paths as _patch_resume_hook_paths
from tests.helpers import patch_setup_hook_paths as _patch_setup_hook_paths
from tests.helpers import patch_terse_hook_paths as _patch_terse_hook_paths


@pytest.fixture
def patch_setup_hook_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Callable[..., SetupHookPaths]:
    def factory(**kwargs: Any) -> SetupHookPaths:
        return _patch_setup_hook_paths(monkeypatch, tmp_path, **kwargs)

    return factory


@pytest.fixture
def patch_resume_hook_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Callable[..., ResumeHookPaths]:
    def factory(**kwargs: Any) -> ResumeHookPaths:
        return _patch_resume_hook_paths(monkeypatch, tmp_path, **kwargs)

    return factory


@pytest.fixture
def patch_terse_hook_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Callable[..., TerseHookPaths]:
    def factory(**kwargs: Any) -> TerseHookPaths:
        return _patch_terse_hook_paths(monkeypatch, tmp_path, **kwargs)

    return factory


@pytest.fixture(autouse=True)
def _isolate_operator_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the suite off the operator's real usage data.

    Every provider and adapter resolves its source directory and its disk cache
    under the real ``$HOME`` (``~/.claude/projects``, ``~/.codex/sessions``,
    ``~/.gemini/...``, ``~/.agentdeck/*_cache.json``), and the adapters capture
    theirs at *import* time, so patching ``CODEX_HOME`` afterwards changes
    nothing. A test that isolates the source directory but not the cache still
    gets the operator's entries back, because ``_seed_caches_from_disk()``
    reloads them before anything is parsed -- which is how
    ``test_report_today_uses_codex_token_count_deltas`` came to assert 65 tokens
    and read 21.7 million on a machine that actually runs agentdeck. CI never
    saw it: a fresh runner has no ``~/.agentdeck`` and no ``~/.codex``.

    Point every one of those at an empty per-test directory and reset the
    module-level caches and their "already seeded" flags, so forgetting to
    isolate something fails closed (empty) instead of silently reading real
    data. Tests that need fixture data still monkeypatch afterwards, which wins.
    """
    from adapters import claude as claude_adapter
    from adapters import codex as codex_adapter
    from adapters import rate_limits
    from analyzer import persona_loader, reporter
    from providers import agy_loader, agy_quota_probe, codex_loader, history_loader

    home = tmp_path / "isolated-home"
    monkeypatch.setenv("CODEX_HOME", str(home / ".codex"))

    for module, name, relative in (
        (codex_loader, "JSONL_CACHE_PATH", ".agentdeck/codex_jsonl_cache.json"),
        (history_loader, "HISTORY_CACHE_PATH", ".agentdeck/history_jsonl_cache.json"),
        (agy_loader, "AGY_CACHE_PATH", ".agentdeck/agy_db_cache.json"),
        (agy_quota_probe, "CACHE_PATH", ".agentdeck/agy_quota_cache.json"),
        (reporter, "YEAR_CACHE_PATH", ".agentdeck/year_cache.json"),
        (reporter, "YEAR_LEDGER_PATH", ".agentdeck/year_ledger.json"),
        (codex_loader, "SESSIONS_DIR", ".codex/sessions"),
        (codex_loader, "ARCHIVED_SESSIONS_DIR", ".codex/archived_sessions"),
        (codex_loader, "STATE_DB", ".codex/state_5.sqlite"),
        (codex_loader, "LOGS_DB", ".codex/logs_2.sqlite"),
        (history_loader, "CLAUDE_PROJECTS_DIR", ".claude/projects"),
        (persona_loader, "CLAUDE_PROJECTS_DIR", ".claude/projects"),
        (agy_loader, "AGY_SESSIONS_DIR", ".gemini/antigravity-cli/conversations"),
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, home / relative)

    # The adapters store strings, not Paths, and captured them at import.
    for module, name, relative in (
        (codex_adapter, "CODEX_DIR", ".codex"),
        (codex_adapter, "SESSIONS_DIR", ".codex/sessions"),
        (codex_adapter, "STATE_DB", ".codex/state_5.sqlite"),
        (rate_limits, "STATUS_FILE", ".claude/agentdeck-status.json"),
        (rate_limits, "LEGACY_STATUS_FILE", ".claude/usag-status.json"),
        (rate_limits, "TT_STATUS_FILE", ".claude/tt-status.json"),
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, str(home / relative))
    if hasattr(claude_adapter, "CLAUDE_DIRS"):
        monkeypatch.setattr(
            claude_adapter,
            "CLAUDE_DIRS",
            [str(home / ".claude/projects"), str(home / ".config/claude/projects")],
        )

    for module in (codex_loader, history_loader, agy_loader, codex_adapter, claude_adapter):
        cache = getattr(module, "_jsonl_cache", None) or getattr(module, "_file_cache", None)
        if cache is not None:
            cache.clear()
        if hasattr(module, "_disk_cache_seeded"):
            monkeypatch.setattr(module, "_disk_cache_seeded", False)
