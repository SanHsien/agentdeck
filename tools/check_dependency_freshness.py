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


HOLD_MARKER = "freshness-hold:"
DEFERRALS_PATH = ROOT / ".github" / "dependency-deferrals.json"


def parse_holds(text: str) -> dict[str, str]:
    """Map package -> reason for ``# freshness-hold:`` comments in pyproject.toml.

    A hold is a standing policy, not a postponement: some floors are the floor we
    want, and re-asking every month turns the report into noise. tomllib drops
    comments, so the marker is read off the raw text of the declaring line.
    """
    holds: dict[str, str] = {}
    for line in text.splitlines():
        head, marker, comment = line.partition("#")
        reason = comment.strip()[len(HOLD_MARKER):].strip()
        if not marker or not comment.strip().startswith(HOLD_MARKER) or not reason:
            continue
        for quoted in re.findall(r"\"([^\"]+)\"|'([^']+)'", head):
            match = _REQUIREMENT_RE.match(quoted[0] or quoted[1])
            if match:
                holds[match.group(1).lower()] = reason
    return holds


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, tuple[str, str]]:
    """Read reviewed-but-not-now decisions: package -> (reviewed release, reason).

    The reviewed release is what makes a deferral expire by itself: once PyPI
    moves past it the report asks again, so a deferral cannot quietly become a
    silenced check. An entry without it is ignored for that reason.
    """
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("deferrals", {})
    except (OSError, ValueError):
        return {}
    deferrals: dict[str, tuple[str, str]] = {}
    for name, entry in (entries or {}).items():
        if not isinstance(entry, dict):
            continue
        latest = str(entry.get("deferredLatest", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if latest and reason:
            deferrals[name.lower()] = (latest, reason)
    return deferrals


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
    holds = parse_holds(pyproject_path.read_text(encoding="utf-8"))

    project: dict[str, Any] = data.get("project", {})
    packages = _parse_requirements(project.get("dependencies", []), "runtime")
    for extra, requirements in project.get("optional-dependencies", {}).items():
        packages.extend(_parse_requirements(requirements, f"extra:{extra}"))
    for group, requirements in data.get("dependency-groups", {}).items():
        packages.extend(_parse_requirements(requirements, f"group:{group}"))
    packages.extend(
        _parse_requirements(data.get("build-system", {}).get("requires", []), "build-system")
    )
    for package in packages:
        package["hold"] = holds.get(package["name"].lower(), "")
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


def collect_status(
    packages: Iterable[dict[str, str]],
    deferrals: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    deferrals = deferrals if deferrals is not None else load_deferrals()
    rows: list[dict[str, Any]] = []
    for package in packages:
        minimum = package["minimum"]
        latest = fetch_pypi_version(package["name"])
        check_failed = not minimum or latest is None
        outdated = bool(minimum and latest and is_newer_version(latest, minimum))
        reviewed, reason = deferrals.get(package["name"].lower(), ("", ""))
        deferred = bool(reviewed and latest and not is_newer_version(latest, reviewed))
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "outdated": outdated,
                "check_failed": check_failed,
                "hold": package.get("hold", ""),
                "deferred_reason": reason if deferred else "",
            }
        )
    return rows


def needs_review(row: dict[str, Any]) -> bool:
    """An aged floor still counts unless a hold or a live deferral covers it."""
    return bool(row["outdated"]) and not row.get("hold") and not row.get("deferred_reason")


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
        elif row["outdated"] and row.get("hold"):
            status = f"HELD: {row['hold']}"
        elif row["outdated"] and row.get("deferred_reason"):
            status = f"DEFERRED at {row['latest']}: {row['deferred_reason']}"
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
            "0. A red line has exactly two honest exits, and both leave a reason behind:",
            "   `# freshness-hold: <why>` on the declaring line for a standing policy, or an",
            "   entry in `.github/dependency-deferrals.json` with `deferredLatest` for",
            "   \"reviewed, not now\" -- that one expires by itself once PyPI moves past the",
            "   release it was reviewed against. Raising a floor to silence the report is not",
            "   one of them: the declaration is a compatibility promise, not a mute button.",
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

    outdated = any(needs_review(row) for row in rows)
    check_failed = not rows or any(bool(row["check_failed"]) for row in rows)
    if args.github_output:
        write_github_output(outdated, check_failed, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
