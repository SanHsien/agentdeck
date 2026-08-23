# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Every packaged resource must be reachable in the frozen bundle.

``i18n.packaged_resource_path(name, source_path)`` looks for ``name`` under
PyInstaller's ``sys._MEIPASS`` and only falls back to ``source_path`` when that
misses. So a resource whose ``--add-data`` destination does not match the name
the code asks for silently rides on the fallback — and the fallback is not a
guarantee, just a coincidence of the onedir layout. If it ever stops matching,
the failure shows up as a blank panel in a shipped exe, not as a red test.

Upstream had the equivalent guard against py2app's ``OPTIONS["resources"]``; it
was deleted with the macOS build, so this is its PyInstaller replacement.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_windows.ps1"
SKIP_DIRS = {"tests", "build", "dist", ".venv", "__pycache__", "reference", "winbuild"}

# Names built at runtime from a variable, with the concrete values they take.
DYNAMIC_RESOURCES = {
    "critters/{beast}/wrapped.png": [
        f"critters/{beast}/wrapped.png" for beast in ("phoenix", "dragon")
    ],
}


def _source_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if SKIP_DIRS.isdisjoint(path.relative_to(ROOT).parts)
    )


def _requested_resource_names() -> set[str]:
    """First-argument literals of every packaged_resource_path call in the tree."""
    names: set[str] = set()
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name != "packaged_resource_path" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
            elif isinstance(first, ast.JoinedStr):
                # An f-string: recover the literal template so the dynamic map
                # below can expand it into the concrete names.
                template = "".join(
                    part.value
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                    else "{beast}"
                    for part in first.values
                )
                names.add(template)
    return names


def _declared_destinations() -> set[str]:
    """``dest`` halves of every --add-data in the build script, as posix paths."""
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    destinations: set[str] = set()
    for spec in re.findall(r"add-data\s+\"([^\"]+)\"", text):
        _, _, dest = spec.rpartition(";")
        dest = dest.strip()
        destinations.add("" if dest == "." else dest.replace("\\", "/").strip("/"))
    return destinations


def _bundled_paths() -> set[str]:
    """Resource paths the bundle will expose, relative to sys._MEIPASS."""
    paths: set[str] = set()
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    for spec in re.findall(r"add-data\s+\"([^\"]+)\"", text):
        source_expr, _, dest = spec.rpartition(";")
        match = re.search(r"'([^']+)'", source_expr)
        if match is None:
            continue
        source = ROOT / match.group(1)
        prefix = "" if dest.strip() == "." else dest.strip().replace("\\", "/").strip("/")
        if source.is_dir():
            # A directory can itself be the resource name — persona_store asks
            # for "personas" and walks it at runtime — so record the destination
            # directory as well as every file inside it.
            if prefix:
                paths.add(prefix)
            for child in source.rglob("*"):
                if child.is_file():
                    rel = child.relative_to(source).as_posix()
                    paths.add(f"{prefix}/{rel}" if prefix else rel)
        elif source.is_file():
            name = source.name
            paths.add(f"{prefix}/{name}" if prefix else name)
    return paths


def _expand(name: str) -> list[str]:
    return DYNAMIC_RESOURCES.get(name, [name])


def test_build_script_declares_data_files() -> None:
    assert _declared_destinations(), "no --add-data found; did the build script change shape?"


def test_every_requested_resource_is_bundled_under_the_name_the_code_asks_for() -> None:
    bundled = _bundled_paths()
    missing = sorted(
        concrete
        for name in _requested_resource_names()
        for concrete in _expand(name)
        if concrete not in bundled
    )

    assert not missing, (
        "packaged_resource_path asks for these names, but no --add-data in "
        f"scripts/build_windows.ps1 puts a file there: {missing}. "
        "The frozen app would fall through to its source-mode path instead of "
        "reading the bundled copy."
    )


@pytest.mark.parametrize(
    "name",
    sorted(
        concrete
        for template in DYNAMIC_RESOURCES
        for concrete in DYNAMIC_RESOURCES[template]
    ),
)
def test_dynamic_resource_sources_exist_in_the_tree(name: str) -> None:
    # The map above is hand-maintained; if a sprite is renamed, fail here rather
    # than let the bundle check pass against a stale list.
    assert (ROOT / "assets" / name).is_file(), f"assets/{name} is missing"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="needs PowerShell 7 to parse")
def test_the_build_script_actually_parses() -> None:
    """The build script must be syntactically valid PowerShell.

    The checks above read the script as text, so they happily pass on a file
    PowerShell cannot run — which is exactly what happened: a comment placed
    inside a backtick-continued command broke the invocation, every --add-data
    assertion still passed, and the break only surfaced when a release build was
    attempted. Parsing costs a second and closes that gap.
    """
    script = (
        "$e=$null; "
        f"$null=[System.Management.Automation.Language.Parser]::ParseFile('{BUILD_SCRIPT}',"
        "[ref]$null,[ref]$e); "
        "if ($e) { $e | ForEach-Object { $_.Message }; exit 1 } else { exit 0 }"
    )
    result = subprocess.run(  # noqa: S603 - fixed executable, generated argument
        ["pwsh", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, f"build_windows.ps1 has syntax errors:\n{result.stdout}"


def test_the_build_script_clears_stale_egg_info_and_checks_the_exe_version() -> None:
    """Both halves of the P6 guard must stay in the build script.

    A leftover ``*.egg-info`` makes ``importlib.metadata`` resolve before the
    pyproject fallback, so the exe gets stamped with whatever version that
    directory records. A fresh CI checkout has none, so the mistake only
    reaches the artifact when a release is cut locally -- and nothing else in
    the pipeline compares the built exe against the tree it came from.
    """
    script = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert '-Filter "*.egg-info"' in script, (
        "build_windows.ps1 must delete stale *.egg-info before building; "
        "without it a local release can be stamped with an older version."
    )
    assert "--doctor" in script, (
        "build_windows.ps1 must ask the built exe for its version."
    )
    assert "Version mismatch" in script, (
        "build_windows.ps1 must fail the build when the exe and pyproject.toml "
        "disagree, not just print the version."
    )


def test_the_release_workflow_checks_the_tag_against_the_exe() -> None:
    """The tag is the one input the build script cannot see."""
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "--doctor" in workflow, "release.yml must verify the tag against the built exe"
    assert "does not match the built executable" in workflow
    assert "scripts/package_windows.ps1" in workflow, (
        "release.yml must package through the shared script so the asset it "
        "uploads has the same layout as a locally built one."
    )
