#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Refuse to build a release whose version is not strictly newer than every earlier one.

A mistyped tag -- an old number, or one already published -- otherwise builds all
the way through and only shows up on the user's machine, where the update check
compares versions and quietly decides there is nothing to install.

The tag being released is excluded from the comparison. This fork creates the
GitHub release first and lets the resulting tag push drive the workflow, so by
the time this runs the version under test is already in the published list;
comparing against a set that contains itself would refuse every release. The
question worth asking is whether it is newer than everything that came *before*.

That ordering leaves one case this cannot catch: re-cutting the *newest*
published version looks identical to publishing it for the first time. Every
other mistake is caught -- an older number, or re-cutting anything that is not
the newest -- because the release that superseded it is still in the set.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from update_checker import compare_versions  # noqa: E402


def _strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def published_versions(repo: str, *, exclude_tag: str) -> list[str]:
    result = subprocess.run(
        ["gh", "release", "list", "--repo", repo, "--limit", "200", "--json", "tagName,isDraft"],
        capture_output=True,
        check=True,
        text=True,
    )
    versions = []
    for release in json.loads(result.stdout):
        if release.get("isDraft"):
            continue
        tag = release["tagName"]
        if tag == exclude_tag:
            continue
        versions.append(_strip_v(tag))
    return versions


def latest(versions: list[str]) -> str | None:
    """Newest parseable version, ignoring tags that predate the versioning rule.

    Each candidate is validated against itself first. Taking the first element
    on trust let an unparseable historical tag such as ``nightly`` become the
    incumbent, and every later comparison against it then raised -- blocking
    today's release because of yesterday's mess.
    """
    newest: str | None = None
    for candidate in versions:
        try:
            compare_versions(candidate, candidate)
        except ValueError:
            continue
        if newest is None or compare_versions(candidate, newest) > 0:
            newest = candidate
    return newest


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_release_version.py <repo> <tag>", file=sys.stderr)
        return 2
    repo, tag = argv
    version = _strip_v(tag)

    previous = latest(published_versions(repo, exclude_tag=tag))
    if previous is None:
        print("No earlier published release to compare against.")
        return 0

    try:
        result = compare_versions(version, previous)
    except ValueError:
        print(
            f"::error::Tag {tag!r} is not MAJOR.MINOR.PATCH, so it cannot be "
            f"checked against the previous release ({previous}).",
            file=sys.stderr,
        )
        return 1

    if result <= 0:
        print(
            f"::error::Tag {tag!r} ({version}) is not newer than the previous published "
            f"release ({previous}). Refusing to build a non-monotonic version.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {version} is newer than the previous published release {previous}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
