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
        "User-Agent": "agentdeck-upstream-check",
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


# Classifying costs one API call per commit. Upstream commits roughly daily, so
# a weekly check is a handful of calls; a long gap should degrade to "review
# everything by hand" rather than hammer the API.
MAX_COMMITS_CLASSIFIED = 40


def fetch_commit_files(repo: str, sha: str, *, token: str | None = None) -> list[dict[str, str]]:
    """The paths one commit touched, with the status of each."""
    payload = _request(f"{API_ROOT}/repos/{repo}/commits/{sha}", token)
    if not isinstance(payload, dict):
        raise UpstreamCheckError(f"unexpected commit payload for {sha}")
    files = payload.get("files")
    if not isinstance(files, list):
        return []
    return [
        {"filename": str(f.get("filename") or ""), "status": str(f.get("status") or "")}
        for f in files
        if isinstance(f, dict)
    ]


# Paths where a change cannot carry an idea worth porting -- a data mirror and
# translations of documents this fork does not keep. Deliberately tiny, and it
# must stay that way: "this fork does not have the file" is NOT a reason to
# skip. A macOS-only fix is written against a platform we dropped, but the
# reasoning behind it often applies here, and porting reasoning is what this
# fork is for. Those get flagged for a quick read, never auto-skipped.
NO_PORTABLE_CONTENT = {
    "ai_updates.json",
    "README.ja.md",
    "README.ko.md",
    "README.zh-CN.md",
}


def carries_no_portable_idea(files: list[dict[str, str]]) -> bool:
    """Whether a commit is pure content churn with no concept behind it."""
    if not files:
        return False
    return all(
        entry["status"] != "added" and entry["filename"] in NO_PORTABLE_CONTENT
        for entry in files
    )


def touches_nothing_we_have(files: list[dict[str, str]], *, root: Path = ROOT) -> bool:
    """Whether every path is absent here -- a hint about effort, not a verdict.

    Such a commit cannot be cherry-picked, but it can still describe a bug we
    also have or a behaviour worth copying. It is surfaced separately so the
    reader knows to judge the idea rather than the diff.
    """
    if not files:
        return False
    for entry in files:
        if entry["status"] == "added":
            return False
        name = entry["filename"]
        if not name or (root / name).exists():
            return False
    return True


def classify_commits(
    repo: str, commits: list[dict[str, str]], *, token: str | None = None, root: Path = ROOT
) -> None:
    """Annotate each commit in place with whether a human needs to read it."""
    if len(commits) > MAX_COMMITS_CLASSIFIED:
        for commit in commits:
            commit["relevance"] = "unknown"
        return
    for commit in commits:
        try:
            files = fetch_commit_files(repo, commit["sha"], token=token)
        except (urllib.error.URLError, urllib.error.HTTPError, UpstreamCheckError):
            # Never let a failed lookup silently promote a commit to "ignorable".
            commit["relevance"] = "unknown"
            continue
        if carries_no_portable_idea(files):
            commit["relevance"] = "no-content"
        elif touches_nothing_we_have(files, root=root):
            # Not portable as a patch; possibly portable as an idea.
            commit["relevance"] = "port-check"
        else:
            commit["relevance"] = "review"
        commit["paths"] = ", ".join(entry["filename"] for entry in files[:4])


def needs_review(commits: list[dict[str, str]]) -> list[dict[str, str]]:
    """Everything a person still has to form an opinion about.

    ``port-check`` counts. A macOS-only commit cannot be cherry-picked, but the
    fork exists to port ideas, and deciding "not worth porting" is a judgement
    only a person can make.
    """
    return [c for c in commits if c.get("relevance") != "no-content"]


def fetch_new_tickets(
    repo: str, kind: str, last_reviewed: int, *, token: str | None = None
) -> list[dict[str, Any]]:
    """Upstream pull requests or issues numbered above ``last_reviewed``.

    ``state=all`` is deliberate. An item opened and closed between two scheduled
    runs was still never triaged here, and a pull request closed *without*
    merging never reaches the commit axis at all -- which is exactly the class
    of "upstream declined it, this fork might still want it".

    Uses this module's own REST path rather than `gh`: the commit axis has
    always gone through `_request`, and a second, differently-behaving route to
    the same data is a liability, not a convenience.

    The issues endpoint returns pull requests too -- they share a number space
    -- so for ``kind == "issue"`` anything carrying a ``pull_request`` key is
    dropped. Presence, not truthiness: GitHub has returned an empty object
    there, and a truthiness test would let pull requests be counted twice.
    """
    endpoint = "pulls" if kind == "pr" else "issues"
    per_page = 100
    items: list[dict[str, Any]] = []
    for page in range(1, 11):  # 1000 items, matching the rest of the fleet
        url = (
            f"https://api.github.com/repos/{repo}/{endpoint}"
            f"?state=all&sort=created&direction=desc&per_page={per_page}&page={page}"
        )
        batch = _request(url, token)
        if not isinstance(batch, list) or not batch:
            break
        for item in batch:
            number = int(item["number"])
            if number <= last_reviewed:
                # Sorted newest first, so nothing below this is newer.
                return sorted(items, key=lambda entry: entry["number"])
            if kind == "issue" and "pull_request" in item:
                continue
            items.append({"number": number, "title": item.get("title", "")})
        if len(batch) < per_page:
            break
    return sorted(items, key=lambda entry: entry["number"])


def collect_ticket_results(
    sync_points: dict[str, Any], *, repo: str | None = None, token: str | None = None
) -> list[dict[str, Any]]:
    """One result per ticket axis, with failures recorded as errors.

    A failed query becomes ``error``, never an empty list. "Not checked" and
    "nothing to review" look identical in a green report, and only one of them
    is true.
    """
    effective_repo = repo or str(sync_points.get("repo") or DEFAULT_REPO)
    tickets = sync_points.get("tickets") or {}

    results: list[dict[str, Any]] = []
    for kind, label in (("pr", "Pull requests"), ("issue", "Issues")):
        last_reviewed = int(tickets.get(f"reviewed_{kind}_through", 0) or 0)
        try:
            items = fetch_new_tickets(
                effective_repo, kind, last_reviewed, token=token
            )
            error: str | None = None
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
            ValueError,
            KeyError,
        ) as exc:
            items, error = [], str(exc)
        results.append(
            {
                "kind": kind,
                "label": label,
                "last_reviewed": last_reviewed,
                "items": items,
                "error": error,
            }
        )
    return results


def render_ticket_markdown(ticket_results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for result in ticket_results:
        lines += [
            f"## Upstream {result['label']}",
            "",
            f"Triaged through `#{result['last_reviewed']}` (queried `state=all`).",
            "",
        ]
        if result["error"]:
            lines += [
                "**Not checked**: the query failed. This run is not evidence that",
                "nothing changed.",
                "",
                f"```text\n{result['error']}\n```",
                "",
            ]
            continue
        items = result["items"]
        if not items:
            lines += ["No new items above that number.", ""]
            continue
        lines += [
            f"{len(items)} new item(s) to triage.",
            "",
            "| Item | Title |",
            "| --- | --- |",
        ]
        for item in items:
            # Computed outside the f-string: a backslash inside an f-string
            # expression is a SyntaxError before Python 3.12.
            title = str(item["title"]).replace("|", "\\|")
            lines.append(f"| #{item['number']} | {title} |")
        lines += [
            "",
            "Record the verdict in `docs/UPSTREAM.md`, then raise",
            f"`tickets.reviewed_{result['kind']}_through` in the sync points.",
            "",
        ]
    return "\n".join(lines)


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
            classify_commits(effective_repo, commits, token=token)
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
        direct = [c for c in commits if c.get("relevance") in ("review", "unknown")]
        port_check = [c for c in commits if c.get("relevance") == "port-check"]
        no_content = [c for c in commits if c.get("relevance") == "no-content"]

        def _bullet(commit: dict[str, str], indent: str = "  ") -> str:
            sha = commit["sha"]
            link = f"[`{sha}`]({commit['url']})" if commit["url"] else f"`{sha}`"
            return f"{indent}- {link} {commit['title']}"

        def _group(title: str, group: list[dict[str, str]], *, paths: bool = False) -> None:
            if not group:
                return
            lines.append(f"- **{title}：{len(group)} 個**（由舊到新）：")
            lines.append("")
            for commit in group[:MAX_COMMITS_SHOWN]:
                suffix = f" — `{commit.get('paths')}`" if paths and commit.get("paths") else ""
                lines.append(_bullet(commit) + suffix)
            if len(group) > MAX_COMMITS_SHOWN:
                lines.append(f"  - …另有 {len(group) - MAX_COMMITS_SHOWN} 筆未列出")
            lines.append("")

        _group("需要人工審視（動到本 fork 也有的檔案）", direct)
        # Not auto-skipped on purpose. The patch will not apply, but the reasoning
        # behind it may still be worth porting -- deciding that is a human call,
        # and this fork exists to port ideas rather than accept gaps.
        _group("需要判斷是否值得移植（只動到本 fork 沒有的檔案）", port_check, paths=True)

        if not direct and not port_check:
            lines.append("- 沒有需要人工審視的 commit。")
            lines.append("")

        if no_content:
            # Folded, not hidden: "the tool decided for me" stays auditable, and
            # the sync point is still advanced by a person.
            lines.append(
                f"<details><summary>另有 {len(no_content)} 個 commit 只同步資料、"
                "沒有可移植的概念（可直接推進 <code>last_reviewed</code>）</summary>"
            )
            lines.append("")
            for commit in no_content[:MAX_COMMITS_SHOWN]:
                paths = commit.get("paths")
                suffix = f" — `{paths}`" if paths else ""
                lines.append(_bullet(commit, indent="") + suffix)
            lines.append("")
            if not direct and not port_check:
                lines.append(f"推進到：`{no_content[-1]['sha']}`")
            lines.append("</details>")
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
    """True when something needs a person, not merely when upstream moved.

    Upstream commits its AI digest most days and those touch files this fork
    deleted. Counting them would open an issue every week that says "advance
    last_reviewed past seven chores", which trains the reader to ignore it.
    """
    return any(result["error"] or needs_review(result["commits"]) for result in results)

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
    ticket_results = collect_ticket_results(sync_points, repo=repo, token=token)
    report = render_markdown(results, repo)
    report = report.rstrip("\n") + "\n\n" + render_ticket_markdown(ticket_results)

    if args.output is not None:
        args.output.write_text(report, encoding="utf-8", newline="\n")
    else:
        print(report)

    # Tickets feed the same signal as commits. The sync points have carried
    # `tickets.reviewed_*_through` all along with nothing reading them, so those
    # two axes were not "checked and clear" -- they were never checked, and the
    # report was green for the same reason it was green before they existed.
    #
    # No relevance split here: the commit axis can filter upstream's daily AI
    # digest because that noise is identifiable, but every ticket above the
    # reviewed number is something a person still has to read.
    updates = (
        has_updates(results)
        or any(result["items"] or result["error"] for result in ticket_results)
    )
    github_output = os.environ.get("GITHUB_OUTPUT")
    if args.github_output and github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"has_updates={'true' if updates else 'false'}\n")
    print(f"has_updates={updates}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
