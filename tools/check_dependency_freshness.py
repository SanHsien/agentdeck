#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Compare the dependencies declared in pyproject.toml against PyPI.

Dependabot opens pull requests when a lock entry moves, but it says nothing about
a floor that has quietly aged: a ``rich>=15.0.0`` that PyPI has left three minor
versions behind still looks healthy in ``uv.lock``. This reads every direct
requirement -- runtime, extras, dependency groups, build backend -- asks PyPI for
the current release, and writes a Markdown report.

It compares declarations, never the installed environment, and it never updates
anything. A newer release is a prompt to read the changelog, not a merge.

    python tools/check_dependency_freshness.py --output report.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "agentdeck-dependency-freshness"

_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
_MINIMUM_RE = re.compile(r"(>=|>|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*)")
_RELEASE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*")


def release_key(version: str) -> tuple[int, ...] | None:
    """Return the numeric release segment of a version, or None if unparsable.

    Only the release segment is compared. Pre-release and local suffixes are
    dropped, so 16.0.0rc1 and 16.0.0 rank the same -- close enough to answer
    "has the floor aged?" without pulling in a PEP 440 parser that neither the
    runtime nor the dev group ships.
    """
    match = _RELEASE_RE.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer_version(latest: str, declared: str) -> bool:
    """Is `latest` newer than `declared` at the precision `declared` states?

    A floor of ``pywebview>=5.4`` claims nothing about the patch, so reporting
    5.4.1 against it would be a standing false alarm -- and a monthly report that
    cries wolf is a report nobody opens. The comparison happens at the depth the
    declaration commits to: ``>=6`` on the major alone, ``>=5.4`` on major and
    minor, ``>=11.0.0`` on all three.
    """
    latest_key = release_key(latest)
    declared_key = release_key(declared)
    if latest_key is None or declared_key is None:
        return False
    depth = len(declared_key)
    padded = latest_key + (0,) * (depth - len(latest_key))
    return padded[:depth] > declared_key


def _parse_requirements(requirements: Iterable[str], group: str) -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    for requirement in requirements:
        head = requirement.split(";", 1)[0]
        match = _REQUIREMENT_RE.match(head)
        if not match:
            continue
        name, specifiers = match.groups()
        minimum = _MINIMUM_RE.search(specifiers)
        packages.append(
            {
                "name": name,
                "minimum": minimum.group(2) if minimum else "",
                "requirement": requirement.strip(),
                "group": group,
            }
        )
    return packages


def load_direct_dependencies(
    pyproject_path: Path = ROOT / "pyproject.toml",
) -> list[dict[str, str]]:
    with pyproject_path.open("rb") as file:
        data: dict[str, Any] = tomllib.load(file)

    project: dict[str, Any] = data.get("project", {})
    packages = _parse_requirements(project.get("dependencies", []), "runtime")
    for extra, requirements in project.get("optional-dependencies", {}).items():
        packages.extend(_parse_requirements(requirements, f"extra:{extra}"))
    for group, requirements in data.get("dependency-groups", {}).items():
        packages.extend(_parse_requirements(requirements, f"group:{group}"))
    packages.extend(
        _parse_requirements(data.get("build-system", {}).get("requires", []), "build-system")
    )
    return packages


def fetch_pypi_version(package_name: str, timeout: float = 10.0) -> str | None:
    quoted_name = urllib.parse.quote(package_name, safe="")
    request = urllib.request.Request(
        f"https://pypi.org/pypi/{quoted_name}/json",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    info: dict[str, Any] = payload.get("info", {})
    version = info.get("version")
    return str(version) if version else None


def collect_status(packages: Iterable[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for package in packages:
        minimum = package["minimum"]
        latest = fetch_pypi_version(package["name"])
        check_failed = not minimum or latest is None
        outdated = bool(minimum and latest and is_newer_version(latest, minimum))
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "outdated": outdated,
                "check_failed": check_failed,
            }
        )
    return rows


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# agentdeck dependency freshness",
        "",
        "| Package | Group | Declared | PyPI latest | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["check_failed"]:
            status = "CHECK FAILED"
        elif row["outdated"]:
            status = "REVIEW UPDATE"
        else:
            status = "OK"
        lines.append(
            f"| `{row['name']}` | `{row['group']}` | `{row['requirement']}` | "
            f"`{row['latest']}` | {status} |"
        )
    if not rows:
        lines.append("| - | - | - | - | CHECK FAILED |")
    lines.extend(
        [
            "",
            "This report compares the declarations in `pyproject.toml` with PyPI.",
            "It does not inspect the locked or installed environment, and it never",
            "updates anything.",
            "",
            "## Review policy",
            "",
            "1. Read the release notes, and check the Python and Windows support matrix.",
            "2. Run `uv lock`, `uv sync`, ruff, mypy, and pytest before raising a floor.",
            "3. For pystray, pillow, or pywebview, exercise the tray and webview paths on",
            "   Windows -- CI cannot see a broken tray icon.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_github_output(outdated: bool, check_failed: bool, report_path: Path) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    needs_attention = outdated or check_failed
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"outdated={'true' if outdated else 'false'}\n")
        output.write(f"check_failed={'true' if check_failed else 'false'}\n")
        output.write(f"needs_attention={'true' if needs_attention else 'false'}\n")
        output.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check direct dependencies against PyPI")
    parser.add_argument(
        "--output",
        default="dependency-freshness-report.md",
        help="Markdown report output path",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Write status fields to GITHUB_OUTPUT",
    )
    args = parser.parse_args()

    rows = collect_status(load_direct_dependencies())
    report = render_markdown(rows)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(report)

    outdated = any(bool(row["outdated"]) for row in rows)
    check_failed = not rows or any(bool(row["check_failed"]) for row in rows)
    if args.github_output:
        write_github_output(outdated, check_failed, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
