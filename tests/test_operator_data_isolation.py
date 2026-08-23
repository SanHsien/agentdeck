# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Nothing in the suite may read the operator's real usage data.

`tests/conftest.py::_isolate_operator_data` redirects every source directory and
disk cache to a per-test temporary directory. This file is the guard for that
guard: it fails when a new module-level path is added and not isolated, which is
how `ARCHIVED_SESSIONS_DIR` quietly kept `test_report_today_uses_codex_token_...`
reading 21.7 million real tokens while asserting 65 — green on CI, red only on a
machine that actually runs agentdeck.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adapters import claude as claude_adapter
from adapters import codex as codex_adapter
from adapters import rate_limits
from analyzer import persona_loader, reporter
from providers import agy_loader, agy_quota_probe, codex_loader, history_loader

_GUARDED = [
    (codex_loader, "SESSIONS_DIR"),
    (codex_loader, "ARCHIVED_SESSIONS_DIR"),
    (codex_loader, "STATE_DB"),
    (codex_loader, "LOGS_DB"),
    (codex_loader, "JSONL_CACHE_PATH"),
    (history_loader, "CLAUDE_PROJECTS_DIR"),
    (history_loader, "HISTORY_CACHE_PATH"),
    (agy_loader, "AGY_SESSIONS_DIR"),
    (agy_loader, "AGY_CACHE_PATH"),
    (agy_quota_probe, "CACHE_PATH"),
    (persona_loader, "CLAUDE_PROJECTS_DIR"),
    (reporter, "YEAR_CACHE_PATH"),
    (reporter, "YEAR_LEDGER_PATH"),
    (codex_adapter, "CODEX_DIR"),
    (codex_adapter, "SESSIONS_DIR"),
    (codex_adapter, "STATE_DB"),
    (rate_limits, "STATUS_FILE"),
    (rate_limits, "LEGACY_STATUS_FILE"),
    (rate_limits, "TT_STATUS_FILE"),
]


@pytest.mark.parametrize(
    ("module", "name"),
    _GUARDED,
    ids=[f"{module.__name__}.{name}" for module, name in _GUARDED],
)
def test_data_paths_are_redirected_into_the_per_test_directory(
    module: object, name: str, tmp_path: Path
) -> None:
    # The per-test directory itself lives under the real home on Windows, so
    # "not under $HOME" proves nothing here; the isolation being asserted is
    # that the value was redirected into *this test's* tmp_path.
    value = Path(str(getattr(module, name))).resolve()

    assert value.is_relative_to(tmp_path.resolve()), f"{name} was not redirected"


def test_claude_adapter_dirs_are_redirected(tmp_path: Path) -> None:
    for directory in claude_adapter.CLAUDE_DIRS:
        assert Path(directory).resolve().is_relative_to(tmp_path.resolve())
