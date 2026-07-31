#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Refresh the AI Update Daily digest: upstream for other tools, us for us.

The page renders a file committed to this repository, and nothing refreshed it,
so the menu item opened a digest frozen on the day of the fork -- a feature that
looks maintained and is not.

Two sources, because the digest covers two different things:

* **Other tools** (Claude Code, Codex, Antigravity, GitHub CLI) come from
  upstream, which curates them and commits "chore: sync AI updates" every day
  or two. Those entries are copied **verbatim**: they are upstream's editorial
  record of what other projects shipped, including sentences naming files as
  they were called at the time (`usage-status.json`). A blanket rename once
  rewrote those into `agentdeck-status.json`, turning a historical note into a
  false one. Never edit them; this half is a mirror.

* **This project** comes from this repository's own changelogs. Upstream's
  digest carries a card for *its* product, which is not the one the reader is
  running -- a user of this fork wants to know what agentdeck shipped, not what
  `usage` shipped. So upstream's own entry is dropped and replaced.

Exit codes: 0 nothing to do, 10 updated, 1 refused (fetch or sanity check).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "ai_updates.json"
UPSTREAM_URL = "https://raw.githubusercontent.com/aqua5230/usage/main/ai_updates.json"

EXIT_UNCHANGED = 0
EXIT_REFUSED = 1
EXIT_UPDATED = 10

# A truncated download still parses as JSON if it happens to end on a brace, so
# require the shape the renderer depends on before overwriting anything.
MIN_TOOLS = 1
MIN_BYTES = 10_000


def fetch(url: str, *, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(  # noqa: S310 - constant https URL
        url, headers={"User-Agent": "agentdeck-ai-updates-sync"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return bytes(response.read())


def validate(raw: bytes) -> dict[str, Any]:
    """Reject anything that is not a usable digest, loudly."""
    if len(raw) < MIN_BYTES:
        raise ValueError(f"payload is only {len(raw)} bytes; expected at least {MIN_BYTES}")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"top level is {type(data).__name__}, expected an object")
    if not data.get("generated_at"):
        raise ValueError("no generated_at")
    tools = data.get("tools")
    if not isinstance(tools, list) or len(tools) < MIN_TOOLS:
        raise ValueError(f"tools is {tools!r}; expected a non-empty list")
    for tool in tools:
        if not isinstance(tool, dict) or not tool.get("name"):
            raise ValueError(f"a tool entry has no name: {tool!r}")
    return data


def changed(new: dict[str, Any], current_path: Path) -> bool:
    """Compare parsed content, not bytes.

    git may hand back CRLF on a Windows checkout, so a byte comparison would
    report a change on every run and commit noise forever.
    """
    if not current_path.exists():
        return True
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return bool(new != current)


# Upstream's card for its own product, which a reader of this fork is not
# running. Matched on id so a display-name change upstream does not resurrect it.
UPSTREAM_OWN_IDS = {"usage"}
OWN_TOOL_ID = "agentdeck"
OWN_TOOL_NAME = "agentdeck"
OWN_VERSIONS_SHOWN = 3

CHANGELOGS = {"en": REPO_ROOT / "CHANGELOG.md", "zh-TW": REPO_ROOT / "CHANGELOG.zh-TW.md"}

_VERSION_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$")
# "- **Title**: body" (English) or "- **標題**：內文" (Chinese).
_BULLET = re.compile(r"^- \*\*(?P<title>.+?)\*\*[:：]\s*(?P<body>.*)$")


def parse_changelog(path: Path) -> dict[str, dict[str, Any]]:
    """Map version -> {date, items} from one changelog.

    Only released headings are read. ``## [Unreleased]`` is deliberately skipped:
    the digest reports what shipped, and announcing unreleased work would put
    entries in front of users who cannot get them yet.
    """
    versions: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = _VERSION_HEADING.match(line)
        if heading:
            current = {"date": heading.group(2), "items": []}
            versions[heading.group(1)] = current
            continue
        if line.startswith("## "):  # any other section ends the current version
            current = None
            continue
        if current is None:
            continue
        bullet = _BULLET.match(line)
        if bullet:
            current["items"].append((bullet.group("title"), bullet.group("body").strip()))
    return versions


def build_own_entry() -> dict[str, Any] | None:
    """Turn this project's changelogs into a digest tool entry.

    Both languages are parsed and matched by version and position. If they ever
    disagree on how many bullets a release has, the shorter one wins for that
    release rather than pairing a title with someone else's body -- the doc
    parity gate already fails loudly on that kind of drift.
    """
    parsed = {lang: parse_changelog(path) for lang, path in CHANGELOGS.items() if path.exists()}
    if "en" not in parsed or "zh-TW" not in parsed:
        return None

    shared = sorted(
        set(parsed["en"]) & set(parsed["zh-TW"]),
        key=lambda v: tuple(int(part) for part in v.split(".")),
        reverse=True,
    )[:OWN_VERSIONS_SHOWN]
    if not shared:
        return None

    versions: list[dict[str, Any]] = []
    for version in shared:
        en, zh = parsed["en"][version], parsed["zh-TW"][version]
        items = [
            {
                "title": {"en": en_title, "zh-TW": zh_title},
                "body": {"en": en_body, "zh-TW": zh_body},
            }
            for (en_title, en_body), (zh_title, zh_body) in zip(
                en["items"], zh["items"], strict=False
            )
        ]
        if items:
            versions.append({"version": version, "period": en["date"], "items": items})
    if not versions:
        return None
    return {"id": OWN_TOOL_ID, "name": OWN_TOOL_NAME, "versions": versions}


def replace_own_tool(data: dict[str, Any]) -> dict[str, Any]:
    """Swap upstream's product card for this project's, keeping its position."""
    own = build_own_entry()
    tools: list[dict[str, Any]] = []
    inserted = False
    for tool in data["tools"]:
        if str(tool.get("id", "")).lower() in UPSTREAM_OWN_IDS:
            if own is not None and not inserted:
                tools.append(own)
                inserted = True
            continue
        tools.append(tool)
    if own is not None and not inserted:
        tools.append(own)
    return {**data, "tools": tools}


def render_page() -> None:
    subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(REPO_ROOT / "scripts" / "build_ai_updates.py")],
        check=True,
        cwd=REPO_ROOT,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=UPSTREAM_URL)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether an update is available without writing anything",
    )
    args = parser.parse_args()

    try:
        raw = fetch(args.url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"REFUSED: could not fetch {args.url}: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    try:
        data = validate(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"REFUSED: upstream payload rejected: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    data = replace_own_tool(data)

    if not changed(data, DATA_FILE):
        print(f"unchanged (upstream generated_at {data['generated_at']})")
        return EXIT_UNCHANGED

    if args.check:
        print(f"update available (upstream generated_at {data['generated_at']})")
        return EXIT_UPDATED

    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    render_page()
    print(f"updated to upstream generated_at {data['generated_at']}")
    return EXIT_UPDATED


if __name__ == "__main__":
    raise SystemExit(main())
