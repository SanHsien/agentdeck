# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_upstream_updates", ROOT / "tools" / "check_upstream_updates.py"
)
assert _spec is not None and _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

VALID = """
<!-- sync-points:start -->
```json
{
  "repo": "aqua5230/usage",
  "branches": {"main": {"last_reviewed": "abc1234", "last_merged": "abc1234"}}
}
```
<!-- sync-points:end -->
"""


def test_parses_the_sync_block() -> None:
    data = check.parse_sync_points(VALID)

    assert data["repo"] == "aqua5230/usage"
    assert data["branches"]["main"]["last_reviewed"] == "abc1234"


@pytest.mark.parametrize(
    "text",
    [
        "no markers here",
        "<!-- sync-points:start -->\nno json\n<!-- sync-points:end -->",
        "<!-- sync-points:start -->\n```json\n{not json}\n```\n<!-- sync-points:end -->",
        '<!-- sync-points:start -->\n```json\n{"branches": {}}\n```\n<!-- sync-points:end -->',
    ],
)
def test_malformed_blocks_are_rejected(text: str) -> None:
    with pytest.raises(check.UpstreamCheckError):
        check.parse_sync_points(text)


@pytest.mark.parametrize("marker", ["", "   ", None, 123])
def test_an_unusable_last_reviewed_is_rejected(marker: Any) -> None:
    # An empty marker would make the compare endpoint report the entire upstream
    # history every week, which is the same as reporting nothing useful.
    block = json.dumps({"branches": {"main": {"last_reviewed": marker}}})
    text = "<!-- sync-points:start -->\n```json\n" + block + "\n```\n<!-- sync-points:end -->"

    with pytest.raises(check.UpstreamCheckError):
        check.parse_sync_points(text)


def test_the_real_upstream_doc_is_valid() -> None:
    # Guards the checked-in doc: a typo there breaks the weekly job silently.
    data = check.load_sync_points()

    assert data["repo"] == "aqua5230/usage"
    assert "main" in data["branches"]


def test_fetch_new_commits_excludes_the_base(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "commits": [
            {"sha": "1111111aaa", "commit": {"message": "first\n\nbody"}, "html_url": "u1"},
            {"sha": "2222222bbb", "commit": {"message": "second"}, "html_url": "u2"},
        ]
    }
    monkeypatch.setattr(check, "_request", lambda url, token: payload)

    commits = check.fetch_new_commits("owner/repo", "main", "base123")

    assert [c["sha"] for c in commits] == ["1111111", "2222222"]
    assert commits[0]["title"] == "first"  # body dropped, subject kept


def test_a_lookup_failure_is_reported_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, token: Any) -> Any:
        raise check.UpstreamCheckError("API down")

    monkeypatch.setattr(check, "_request", boom)
    results = check.collect_results(check.parse_sync_points(VALID))

    # Treating a failed lookup as "nothing new" would let the fork drift behind
    # while the weekly report claimed everything was fine.
    assert results[0]["error"] == "API down"
    assert check.has_updates(results) is True
    assert "不代表沒有更新" in check.render_markdown(results, "owner/repo")


def test_no_new_commits_means_no_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check, "_request", lambda url, token: {"commits": []})
    results = check.collect_results(check.parse_sync_points(VALID))

    assert check.has_updates(results) is False
    assert "沒有比" in check.render_markdown(results, "owner/repo")


def test_report_lists_commits_and_points_at_the_procedure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = {"sha": "abc1234", "commit": {"message": "fix: thing"}, "html_url": "u"}
    payload = {"commits": [commit]}
    monkeypatch.setattr(check, "_request", lambda url, token: payload)
    results = check.collect_results(check.parse_sync_points(VALID))

    report = check.render_markdown(results, "aqua5230/usage")

    assert "abc1234" in report
    assert "fix: thing" in report
    assert "docs/UPSTREAM.md" in report
    # The report must state both halves of the procedure; recording the marker
    # without the reason is how "why did we skip that?" becomes unanswerable.
    assert "last_merged" in report
    assert "Skipped" in report


def test_long_commit_lists_are_truncated_with_a_count(monkeypatch: pytest.MonkeyPatch) -> None:
    commits = [
        {"sha": f"{index:07d}", "commit": {"message": f"c{index}"}, "html_url": ""}
        for index in range(check.MAX_COMMITS_SHOWN + 5)
    ]
    monkeypatch.setattr(check, "_request", lambda url, token: {"commits": commits})
    results = check.collect_results(check.parse_sync_points(VALID))

    report = check.render_markdown(results, "owner/repo")

    assert "另有 5 筆未列出" in report


def test_a_change_to_a_file_this_fork_lacks_cannot_reach_us(tmp_path: Path) -> None:
    """Upstream commits its AI digest most days, touching a file we deleted.

    Left unfiltered those bury the commits that matter, and a report nobody
    reads is the same as no report.
    """
    assert check.cannot_affect_fork(
        [{"filename": "ai_updates.json", "status": "modified"}], root=tmp_path
    )
    assert check.cannot_affect_fork(
        [
            {"filename": "menubar.py", "status": "modified"},
            {"filename": "tests/test_menubar.py", "status": "removed"},
        ],
        root=tmp_path,
    )


def test_a_file_we_do_have_always_needs_review(tmp_path: Path) -> None:
    (tmp_path / "wintray.py").write_text("", encoding="utf-8")

    assert not check.cannot_affect_fork(
        [
            {"filename": "menubar.py", "status": "modified"},
            {"filename": "wintray.py", "status": "modified"},
        ],
        root=tmp_path,
    )


def test_an_added_file_is_never_auto_skipped(tmp_path: Path) -> None:
    """A new upstream file is absent here for the same reason a deleted one is,
    but it is what an arriving feature looks like -- and porting features is
    this fork's entire premise."""
    assert not check.cannot_affect_fork(
        [{"filename": "brand_new_feature.py", "status": "added"}], root=tmp_path
    )


def test_an_empty_file_list_is_never_auto_skipped(tmp_path: Path) -> None:
    """No file list means the lookup told us nothing, not that nothing changed."""
    assert not check.cannot_affect_fork([], root=tmp_path)


def test_a_failed_lookup_leaves_the_commit_for_a_human(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> list[dict[str, str]]:
        raise check.UpstreamCheckError("rate limited")

    monkeypatch.setattr(check, "fetch_commit_files", boom)
    commits = [{"sha": "abc1234", "title": "something", "url": ""}]

    check.classify_commits("owner/repo", commits)

    assert commits[0]["relevance"] == "unknown"
    assert check.needs_review(commits) == commits


def test_too_many_commits_falls_back_to_reviewing_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fork this far behind needs a person, not a few hundred API calls."""
    calls = 0

    def counted(*args: object, **kwargs: object) -> list[dict[str, str]]:
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(check, "fetch_commit_files", counted)
    commits = [
        {"sha": f"{i:07d}", "title": "x", "url": ""}
        for i in range(check.MAX_COMMITS_CLASSIFIED + 1)
    ]

    check.classify_commits("owner/repo", commits)

    assert calls == 0
    assert all(commit["relevance"] == "unknown" for commit in commits)


def test_a_run_of_ignorable_commits_does_not_raise_an_issue() -> None:
    """has_updates must mean "a person has something to do"."""
    commits: list[dict[str, str]] = [
        {"sha": "1", "title": "chore: sync AI updates", "relevance": "ignorable"},
        {"sha": "2", "title": "chore: sync AI updates", "relevance": "ignorable"},
    ]
    results: list[dict[str, Any]] = [
        {
            "branch": "main",
            "last_reviewed": "aaa",
            "last_merged": "aaa",
            "error": None,
            "commits": commits,
        }
    ]

    assert not check.has_updates(results)

    commits.append({"sha": "3", "title": "feat: something", "relevance": "review"})
    assert check.has_updates(results)
