# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "sync_ai_updates", ROOT / "scripts" / "sync_ai_updates.py"
)
assert _spec and _spec.loader
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def _digest(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "generated_at": "2026-07-29",
        "tools": [{"name": "Claude Code", "versions": []}],
    }
    data.update(overrides)
    return data


def _padded(data: dict[str, Any]) -> bytes:
    """Serialise past the minimum size guard so shape checks are what is tested."""
    data = dict(data)
    data["_pad"] = "x" * sync.MIN_BYTES
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def test_a_truncated_download_is_refused_even_though_it_parses() -> None:
    """A short payload can still be valid JSON; size is the cheapest tell."""
    with pytest.raises(ValueError, match="bytes"):
        sync.validate(json.dumps(_digest()).encode("utf-8"))


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (b'"just a string"', "top level"),
        (None, "generated_at"),
    ],
)
def test_the_wrong_shape_never_overwrites_the_committed_digest(
    payload: bytes | None, match: str
) -> None:
    raw = payload if payload is not None else _padded(_digest(generated_at=""))
    if payload is not None:
        raw = payload + b" " * sync.MIN_BYTES

    with pytest.raises(ValueError, match=match):
        sync.validate(raw)


def test_an_empty_tool_list_is_refused() -> None:
    with pytest.raises(ValueError, match="tools"):
        sync.validate(_padded(_digest(tools=[])))


def test_a_nameless_tool_is_refused() -> None:
    with pytest.raises(ValueError, match="no name"):
        sync.validate(_padded(_digest(tools=[{"versions": []}])))


def test_a_good_payload_survives_validation() -> None:
    data = sync.validate(_padded(_digest()))

    assert data["generated_at"] == "2026-07-29"


def test_change_detection_compares_content_not_bytes(tmp_path: Path) -> None:
    """A Windows checkout hands back CRLF, and byte equality would then report a
    change on every single run and commit noise forever."""
    data = _digest()
    target = tmp_path / "ai_updates.json"
    serialised = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    target.write_bytes(serialised.replace(b"\n", b"\r\n"))

    assert sync.changed(data, target) is False
    assert sync.changed(_digest(generated_at="2026-08-01"), target) is True


def test_a_missing_or_unreadable_file_counts_as_changed(tmp_path: Path) -> None:
    assert sync.changed(_digest(), tmp_path / "nope.json") is True

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert sync.changed(_digest(), broken) is True


def test_the_workflow_calls_the_script_and_can_write_back() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ai-updates-sync.yml").read_text(encoding="utf-8")

    assert "scripts/sync_ai_updates.py" in workflow
    assert "contents: write" in workflow, "the job must be able to commit the refresh"
    assert "workflow_dispatch" in workflow, "must be runnable on demand, not only on the cron"


def test_the_committed_digest_is_upstreams_verbatim_record() -> None:
    """This file is a mirror. A rename once rewrote upstream's release notes so
    they described a filename that did not exist when those releases shipped."""
    data = json.loads((ROOT / "ai_updates.json").read_text(encoding="utf-8"))

    assert "agentdeck-status.json" not in json.dumps(data, ensure_ascii=False), (
        "ai_updates.json records what other projects shipped; renaming strings "
        "inside it turns history into fiction. Re-run scripts/sync_ai_updates.py."
    )


def test_upstreams_own_product_card_is_replaced_by_ours() -> None:
    """A reader of this fork runs agentdeck, not the project it forked from.

    Leaving upstream's card in would advertise another product's releases as if
    they were the ones the reader can install.
    """
    upstream = _digest(
        tools=[
            {"id": "claude-code", "name": "Claude Code", "versions": []},
            {"id": "usage", "name": "Usage", "versions": [{"version": "0.29.7"}]},
            {"id": "gh", "name": "GitHub CLI", "versions": []},
        ]
    )

    merged = sync.replace_own_tool(upstream)
    names = [tool["name"] for tool in merged["tools"]]

    assert "Usage" not in names
    assert sync.OWN_TOOL_NAME in names
    # Third-party cards keep their order and content.
    assert names.index("Claude Code") < names.index(sync.OWN_TOOL_NAME) < names.index("GitHub CLI")


def test_a_renamed_upstream_card_is_still_matched_by_id() -> None:
    upstream = _digest(tools=[{"id": "usage", "name": "Something Else", "versions": []}])

    names = [tool["name"] for tool in sync.replace_own_tool(upstream)["tools"]]

    assert names == [sync.OWN_TOOL_NAME]


def test_the_changelog_parser_reads_released_versions_only(tmp_path: Path) -> None:
    """Unreleased work must not be announced to users who cannot install it."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n"
        "- **Not shipped yet**: still on a branch.\n\n"
        "## [1.2.0] - 2026-07-31\n\n"
        "### Fixed\n"
        "- **A real fix**: it does the thing.\n"
        "- **Another one**: and this too.\n\n"
        "## [1.1.0] - 2026-07-01\n\n"
        "### Added\n"
        "- **Older**: from before.\n",
        encoding="utf-8",
    )

    parsed = sync.parse_changelog(changelog)

    assert set(parsed) == {"1.2.0", "1.1.0"}
    assert parsed["1.2.0"]["date"] == "2026-07-31"
    assert [title for title, _ in parsed["1.2.0"]["items"]] == ["A real fix", "Another one"]
    assert parsed["1.1.0"]["items"] == [("Older", "from before.")]


def test_the_parser_accepts_both_colon_conventions(tmp_path: Path) -> None:
    """The Chinese changelog uses a full-width colon; the English one does not."""
    changelog = tmp_path / "CHANGELOG.zh-TW.md"
    changelog.write_text(
        "## [1.0.0] - 2026-01-01\n\n### 修正\n- **標題**：內文在這裡。\n",
        encoding="utf-8",
    )

    parsed = sync.parse_changelog(changelog)

    assert parsed["1.0.0"]["items"] == [("標題", "內文在這裡。")]


def test_our_entry_is_built_from_this_repositorys_real_changelogs() -> None:
    entry = sync.build_own_entry()

    assert entry is not None
    assert entry["id"] == sync.OWN_TOOL_ID
    assert entry["versions"], "no released versions were parsed"
    assert len(entry["versions"]) <= sync.OWN_VERSIONS_SHOWN
    newest = entry["versions"][0]
    assert newest["items"], "the newest release produced no items"
    for language in ("en", "zh-TW"):
        assert newest["items"][0]["title"][language].strip(), f"{language} title is empty"
        assert newest["items"][0]["body"][language].strip(), f"{language} body is empty"
