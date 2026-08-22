# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_dependency_freshness", ROOT / "tools" / "check_dependency_freshness.py"
)
assert _spec is not None and _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_release_key_reads_the_release_segment_only() -> None:
    assert check.release_key("12.3.0") == (12, 3, 0)
    assert check.release_key("16.0.0rc1") == (16, 0, 0)
    assert check.release_key("6") == (6,)
    assert check.release_key("not-a-version") is None


def test_is_newer_version_respects_the_declared_precision() -> None:
    # A floor that names only the minor says nothing about the patch; reporting
    # 5.4.1 against ">=5.4" every month would train the reader to ignore it.
    assert not check.is_newer_version("5.4.1", "5.4")
    assert check.is_newer_version("6.2.1", "5.4")
    assert not check.is_newer_version("15.0.0", "15.0.0")
    assert check.is_newer_version("12.3.0", "11.0.0")
    assert check.is_newer_version("0.16.4", "0.16.0")


def test_is_newer_version_refuses_to_guess_at_unparsable_versions() -> None:
    assert not check.is_newer_version("unknown", "11.0.0")
    assert not check.is_newer_version("12.3.0", "")


def test_load_direct_dependencies_covers_every_declaration_site(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "\n".join(
            [
                "[build-system]",
                'requires = ["setuptools>=68"]',
                "",
                "[project]",
                'name = "demo"',
                'dependencies = ["rich>=15.0.0,<16.0.0"]',
                "",
                "[project.optional-dependencies]",
                "windows = [\"pystray>=0.19.5; sys_platform == 'win32'\"]",
                "",
                "[dependency-groups]",
                'dev = ["ruff>=0.16.0"]',
            ]
        ),
        encoding="utf-8",
    )

    packages = check.load_direct_dependencies(pyproject)
    by_name = {package["name"]: package for package in packages}

    assert by_name["rich"]["group"] == "runtime"
    assert by_name["pystray"]["group"] == "extra:windows"
    assert by_name["ruff"]["group"] == "group:dev"
    assert by_name["setuptools"]["group"] == "build-system"
    # The environment marker must not end up inside the parsed floor.
    assert by_name["pystray"]["minimum"] == "0.19.5"


def test_the_repository_declarations_parse() -> None:
    packages = check.load_direct_dependencies()
    names = {package["name"] for package in packages}

    assert "rich" in names
    assert all(package["minimum"] for package in packages), (
        "every declaration in pyproject.toml should carry a floor the check can read"
    )


def test_render_markdown_labels_each_status() -> None:
    rows: list[dict[str, Any]] = [
        {
            "name": "pillow",
            "group": "extra:windows",
            "requirement": "pillow>=11.0.0",
            "minimum": "11.0.0",
            "latest": "12.3.0",
            "outdated": True,
            "check_failed": False,
        },
        {
            "name": "rich",
            "group": "runtime",
            "requirement": "rich>=15.0.0,<16.0.0",
            "minimum": "15.0.0",
            "latest": "15.0.0",
            "outdated": False,
            "check_failed": False,
        },
        {
            "name": "ghost",
            "group": "runtime",
            "requirement": "ghost",
            "minimum": "",
            "latest": "unknown",
            "outdated": False,
            "check_failed": True,
        },
    ]

    report = check.render_markdown(rows)

    assert "REVIEW UPDATE" in report
    assert "| OK |" in report
    assert "CHECK FAILED" in report


def test_render_markdown_flags_an_empty_run_as_a_failure() -> None:
    # No rows means the declarations could not be read, not that everything is
    # current -- an empty table that reads as "all clear" would be a lie.
    report = check.render_markdown([])

    assert "CHECK FAILED" in report


def test_write_github_output_reports_attention(tmp_path: Path, monkeypatch: Any) -> None:
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    check.write_github_output(True, False, Path("report.md"))
    written = output.read_text(encoding="utf-8")

    assert "outdated=true" in written
    assert "check_failed=false" in written
    assert "needs_attention=true" in written
    assert "report_path=report.md" in written


def test_write_github_output_is_a_no_op_outside_actions(monkeypatch: Any) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    check.write_github_output(True, True, Path("report.md"))


def test_hold_marker_binds_to_the_package_on_that_line() -> None:
    holds = check.parse_holds(
        'dependencies = ["pillow>=12.3"]  # freshness-hold: 12.x is the floor we want\n'
        'other = ["pystray>=0.19"]\n'
    )

    assert holds == {"pillow": "12.x is the floor we want"}


def test_a_comment_without_the_marker_is_not_a_hold() -> None:
    assert check.parse_holds('x = ["ruff>=0.16"]  # just a note\n') == {}


def test_deferral_without_a_reviewed_release_is_ignored(tmp_path) -> None:
    # Otherwise the entry silences the check forever instead of postponing it.
    path = tmp_path / "deferrals.json"
    path.write_text(json.dumps({"deferrals": {"pillow": {"reason": "later"}}}), encoding="utf-8")

    assert check.load_deferrals(path) == {}


def test_missing_deferrals_file_defers_nothing(tmp_path) -> None:
    assert check.load_deferrals(tmp_path / "absent.json") == {}


def test_aged_floor_needs_review_unless_held_or_deferred() -> None:
    aged = {"outdated": True, "hold": "", "deferred_reason": ""}
    held = {"outdated": True, "hold": "policy", "deferred_reason": ""}
    deferred = {"outdated": True, "hold": "", "deferred_reason": "needs a Windows tray check"}

    assert check.needs_review(aged)
    assert not check.needs_review(held)
    assert not check.needs_review(deferred)
