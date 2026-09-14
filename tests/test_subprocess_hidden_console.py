# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Every spawned console program stays invisible.

This is a tray app with no console of its own, so a `subprocess` call without
`CREATE_NO_WINDOW` flashes a black window on Windows -- the only platform this
fork ships. One call per project lookup or quota ping becomes a stream of
flashes, and the panel can appear behind them (upstream 2a1996e).

An AST scan is the point: a comment saying "remember the flag" is what this
already had, in effect, and 16 of 17 call sites did not have it.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

import subprocess_utils

REPO_ROOT = Path(__file__).resolve().parent.parent

# Scanned: everything the tray process can reach. Not scanned: `tests/` (they
# assert on spawned output), `scripts/` (developer CLIs run from a terminal that
# already has a console), and `reference/` (upstream copies kept for diffing).
SKIP_DIRS = {"tests", "scripts", "reference", "dist", "build", ".venv", "node_modules"}
# The hooks installed into the user's environment run under the system Python
# with no path to this project, so they carry their own copy of the helper.
STANDALONE_HOOKS = {"usage_session_resume.py", "usage_statusline_forwarder.py"}
HELPER_NAMES = {"creation_flags", "_creation_flags"}


def _spawn_calls(tree: ast.AST) -> list[ast.Call]:
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Every spawning entry point, not just the two in use today: a future
        # `subprocess.check_output(["git", ...])` is the same bug, and a guard
        # that stays green through it is worth nothing.
        if isinstance(func, ast.Attribute) and func.attr in {
            "run",
            "Popen",
            "call",
            "check_call",
            "check_output",
        }:
            value = func.value
            if isinstance(value, ast.Name) and value.id == "subprocess":
                calls.append(node)
    return calls


def _hides_console(call: ast.Call) -> bool:
    """`creationflags=` must come from the helper, not a hand-written constant.

    A literal `0x08000000` spelled out at the call site is the same bug one
    refactor later: it is Windows-only, and nothing tells the next reader that.
    """
    for keyword in call.keywords:
        if keyword.arg != "creationflags" or not isinstance(keyword.value, ast.Call):
            continue
        func = keyword.value.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name in HELPER_NAMES:
            return True
    return False


def _python_files() -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob("*.py"):
        relative = path.relative_to(REPO_ROOT)
        if set(relative.parts) & SKIP_DIRS or relative.parts[0].startswith("."):
            continue
        files.append(path)
    return sorted(files)


def test_every_spawn_site_hides_the_console() -> None:
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _spawn_calls(tree):
            if not _hides_console(call):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")

    assert offenders == [], "these spawn a console program without hiding its window: " + ", ".join(
        offenders
    )


def test_the_scan_would_notice_a_bare_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reverse test: the check above is only worth its runtime if it fails."""
    module = tmp_path / "bare.py"
    module.write_text("import subprocess\nsubprocess.run(['git'])\n", encoding="utf-8")

    tree = ast.parse(module.read_text(encoding="utf-8"))
    calls = _spawn_calls(tree)

    assert len(calls) == 1
    assert not _hides_console(calls[0])


@pytest.mark.parametrize("name", sorted(STANDALONE_HOOKS))
def test_standalone_hooks_keep_their_own_copy(name: str) -> None:
    """They cannot import the shared helper, so the copy has to be in the file --
    and it must not be an import, which would break the installed hook."""
    source = (REPO_ROOT / name).read_text(encoding="utf-8")

    assert "def _creation_flags(" in source
    assert "subprocess_utils" not in source.replace("`subprocess_utils`", ""), (
        f"{name} is installed standalone and cannot import the project"
    )


@pytest.mark.parametrize("name", sorted(STANDALONE_HOOKS))
def test_the_copies_behave_like_the_shared_helper(name: str) -> None:
    namespace: dict[str, object] = {}
    exec(  # noqa: S102 - executing this repo's own hook to reach its private helper
        compile((REPO_ROOT / name).read_text(encoding="utf-8"), name, "exec"),
        namespace,
    )

    assert namespace["_creation_flags"]() == subprocess_utils.creation_flags()  # type: ignore[operator]


def test_the_flag_is_used_when_windows_offers_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    assert subprocess_utils.creation_flags() == 0x08000000


def test_it_falls_back_to_the_default_where_the_flag_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-zero `creationflags` is rejected off Windows; `0` is the default."""
    monkeypatch.delattr(subprocess, "CREATE_NO_WINDOW", raising=False)

    assert subprocess_utils.creation_flags() == 0
