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
