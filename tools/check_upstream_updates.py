#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Report upstream commits this fork has not reviewed yet.

Upstream is still active, so "are we behind, and does it matter?" needs asking on
a schedule rather than whenever someone remembers. This reads the sync-point
block in ``docs/UPSTREAM.md``, asks GitHub what landed upstream after
``last_reviewed``, and writes a Markdown report.

It reports against ``last_reviewed``, never ``last_merged``. Commits that were
examined and deliberately skipped must stay quiet, or every run would re-list
decisions already made — and a report that repeats itself gets ignored, which
defeats the point of having one.

    python tools/check_upstream_updates.py --output report.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_MD = ROOT / "docs" / "UPSTREAM.md"
SYNC_START_MARKER = "<!-- sync-points:start -->"
SYNC_END_MARKER = "<!-- sync-points:end -->"
DEFAULT_REPO = "aqua5230/usage"
API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 20.0
# GitHub's compare endpoint caps the commit list; a fork this far behind needs a
# human look anyway, so truncation is reported rather than paged through.
MAX_COMMITS_SHOWN = 50


class UpstreamCheckError(RuntimeError):
    """The sync-point block is missing or malformed."""


def parse_sync_points(markdown_text: str) -> dict[str, Any]:
    """Extract and validate the JSON block between the sync-point markers."""
    if SYNC_START_MARKER not in markdown_text or SYNC_END_MARKER not in markdown_text:
        raise UpstreamCheckError("docs/UPSTREAM.md is missing the sync-points markers")
    body = markdown_text.split(SYNC_START_MARKER, 1)[1].split(SYNC_END_MARKER, 1)[0]
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, re.DOTALL)
    if match is None:
        raise UpstreamCheckError("no ```json block between the sync-points markers")
    try:
        data = json.loads(match.group(1))
    except ValueError as exc:
        raise UpstreamCheckError(f"sync-points JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise UpstreamCheckError("sync-points JSON must be an object")

    branches = data.get("branches")
    if not isinstance(branches, dict) or not branches:
        raise UpstreamCheckError("sync-points needs a non-empty 'branches' object")
    for name, info in branches.items():
        if not isinstance(info, dict):
            raise UpstreamCheckError(f"branch {name!r} must map to an object")
        reviewed = info.get("last_reviewed")
        if not isinstance(reviewed, str) or not reviewed.strip():
            # An empty marker would make every run report the entire upstream
            # history, so refuse rather than produce a useless report.
            raise UpstreamCheckError(f"branch {name!r} has no usable 'last_reviewed'")
    return data


def load_sync_points(path: Path = UPSTREAM_MD) -> dict[str, Any]:
    return parse_sync_points(path.read_text(encoding="utf-8"))


def _request(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "usage-upstream-check",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - fixed https host
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def fetch_new_commits(
    repo: str, branch: str, last_reviewed: str, *, token: str | None = None
) -> list[dict[str, str]]:
    """Commits on ``branch`` after ``last_reviewed``, oldest first.

    Uses the compare endpoint, whose ``commits`` list excludes the base — so the
    result is exactly "newer than reviewed", with no off-by-one at the boundary.
    """
    url = f"{API_ROOT}/repos/{repo}/compare/{last_reviewed}...{branch}"
    payload = _request(url, token)
    if not isinstance(payload, dict):
        raise UpstreamCheckError(f"unexpected compare payload for {branch}")
    commits = payload.get("commits")
    if not isinstance(commits, list):
        return []
    out: list[dict[str, str]] = []
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        sha = str(commit.get("sha") or "")
        message = ""
        detail = commit.get("commit")
        if isinstance(detail, dict):
            message = str(detail.get("message") or "")
        out.append(
            {
                "sha": sha[:7],
                "title": message.splitlines()[0] if message else "(no message)",
                "url": str(commit.get("html_url") or ""),
            }
        )
    return out


def collect_results(
    sync_points: dict[str, Any], *, repo: str | None = None, token: str | None = None
) -> list[dict[str, Any]]:
    effective_repo = repo or str(sync_points.get("repo") or DEFAULT_REPO)
    results: list[dict[str, Any]] = []
    branches = sync_points["branches"]
    for name, info in branches.items():
        last_reviewed = str(info["last_reviewed"])
        try:
            commits = fetch_new_commits(effective_repo, name, last_reviewed, token=token)
            error: str | None = None
        except (urllib.error.URLError, urllib.error.HTTPError, UpstreamCheckError) as exc:
            # A network or API failure must not look like "nothing new"; surface it
            # so a silent report is never mistaken for an up-to-date fork.
            commits = []
            error = str(exc)
        results.append(
            {
                "branch": name,
                "last_reviewed": last_reviewed,
                "last_merged": info.get("last_merged"),
                "commits": commits,
                "error": error,
            }
        )
    return results


def render_markdown(results: list[dict[str, Any]], repo: str) -> str:
    lines = [
        "## 上游更新檢查",
        "",
        f"上游：[`{repo}`](https://github.com/{repo})",
        "",
    ]
    for result in results:
        branch = result["branch"]
        lines.append(f"### `{branch}`")
        lines.append("")
        lines.append(f"- `last_reviewed`：`{result['last_reviewed']}`")
        if result.get("last_merged"):
            lines.append(f"- `last_merged`：`{result['last_merged']}`")
        if result["error"]:
            lines.append(f"- ⚠️ 查詢失敗，**不代表沒有更新**：{result['error']}")
            lines.append("")
            continue
        commits = result["commits"]
        if not commits:
            lines.append("- 沒有比 `last_reviewed` 更新的 commit。")
            lines.append("")
            continue
        lines.append(f"- 有 **{len(commits)}** 個未審視的 commit（由舊到新）：")
        lines.append("")
        for commit in commits[:MAX_COMMITS_SHOWN]:
            sha = commit["sha"]
            link = f"[`{sha}`]({commit['url']})" if commit["url"] else f"`{sha}`"
            lines.append(f"  - {link} {commit['title']}")
        if len(commits) > MAX_COMMITS_SHOWN:
            lines.append(f"  - …另有 {len(commits) - MAX_COMMITS_SHOWN} 筆未列出")
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            "處理方式見 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)：**採用**就推進 `last_merged` 與 "
            "`last_reviewed`；**不採用**只推進 `last_reviewed`，並在 Skipped 表補一列理由。",
            "",
            "只推進標記卻不記理由，等於把「為什麼跳過」丟掉。",
        ]
    )
    return "\n".join(lines) + "\n"


def has_updates(results: list[dict[str, Any]]) -> bool:
    # An errored branch counts as needing attention: treating a failed lookup as
    # "nothing new" would let the fork drift silently behind.
    return any(result["commits"] or result["error"] for result in results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=None, help="Override the upstream repo.")
    parser.add_argument("--output", type=Path, default=None, help="Write the report here.")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Append has_updates=<bool> to $GITHUB_OUTPUT for the workflow.",
    )
    args = parser.parse_args(argv)

    try:
        sync_points = load_sync_points()
    except (OSError, UpstreamCheckError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    repo = args.repo or str(sync_points.get("repo") or DEFAULT_REPO)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    results = collect_results(sync_points, repo=repo, token=token)
    report = render_markdown(results, repo)

    if args.output is not None:
        args.output.write_text(report, encoding="utf-8", newline="\n")
    else:
        print(report)

    updates = has_updates(results)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if args.github_output and github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"has_updates={'true' if updates else 'false'}\n")
    print(f"has_updates={updates}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
