"""Contract tests for the upstream pull-request and issue axes.

Each test names a way those two axes could go quiet without anybody deciding to
stop watching upstream. No test reaches the network.
"""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_upstream_updates as checker  # noqa: E402

SYNC_POINTS = {
    "repo": "example/product",
    "branches": {},
    "tickets": {"reviewed_pr_through": 9, "reviewed_issue_through": 8},
}


class FakeRequest:
    """Stands in for `_request`, recording the URLs it was asked for."""

    def __init__(self, pages: list[list[dict[str, object]]]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str, token: str | None) -> object:
        self.calls.append(url)
        return self.pages.pop(0) if self.pages else []


def test_tickets_are_queried_with_state_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """An item opened and closed between two runs was still never triaged."""
    request = FakeRequest([[{"number": 10, "title": "closed unmerged"}], []])
    monkeypatch.setattr(checker, "_request", request)

    checker.fetch_new_tickets("example/product", "pr", 9)

    assert "state=all" in request.calls[0]


def test_items_at_or_below_reviewed_stop_the_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        checker,
        "_request",
        FakeRequest(
            [[{"number": 11, "title": "new"}, {"number": 9, "title": "old"}]]
        ),
    )

    items = checker.fetch_new_tickets("example/product", "pr", 9)

    assert [item["number"] for item in items] == [11]


def test_issue_endpoint_drops_pull_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Issues and pull requests share a number space on that endpoint.

    The key is tested for presence, not truthiness: GitHub has returned an empty
    object there, and a truthiness test counts pull requests on both axes.
    """
    monkeypatch.setattr(
        checker,
        "_request",
        FakeRequest(
            [
                [
                    {"number": 12, "title": "a real issue"},
                    {"number": 11, "title": "a pull request", "pull_request": {}},
                ],
                [],
            ]
        ),
    )

    items = checker.fetch_new_tickets("example/product", "issue", 8)

    assert [item["number"] for item in items] == [12]


def test_a_failed_query_is_an_error_not_an_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """"Not checked" and "nothing to review" must not look the same."""

    def boom(url: str, token: str | None) -> object:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(checker, "_request", boom)

    results = checker.collect_ticket_results(SYNC_POINTS)

    assert all(result["error"] for result in results)
    assert "Not checked" in checker.render_ticket_markdown(results)


def test_report_covers_both_ticket_axes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checker, "_request", FakeRequest([[], []]))

    report = checker.render_ticket_markdown(
        checker.collect_ticket_results(SYNC_POINTS)
    )

    assert "## Upstream Pull requests" in report
    assert "## Upstream Issues" in report
    assert "`#9`" in report and "`#8`" in report


def test_sync_points_actually_carry_both_ticket_numbers() -> None:
    """The numbers live in docs/UPSTREAM.md, and something reads them."""
    tickets = checker.load_sync_points().get("tickets") or {}

    assert isinstance(tickets.get("reviewed_pr_through"), int)
    assert isinstance(tickets.get("reviewed_issue_through"), int)
