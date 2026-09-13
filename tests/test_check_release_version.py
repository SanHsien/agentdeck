# SPDX-License-Identifier: AGPL-3.0-only
"""The release guard: a tag must be strictly newer than everything before it.

A mistyped tag is not caught by anything else. The build succeeds, the zip is
attached, and the only symptom appears on a user's machine, where the update
check compares versions and decides there is nothing to install.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_release_version as guard  # noqa: E402


def _fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    tags: list[str],
    drafts: tuple[str, ...] = (),
) -> None:
    payload = json.dumps([{"tagName": tag, "isDraft": tag in drafts} for tag in tags])

    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=payload, stderr="")

    # Patch by name so mypy does not have to treat the script's stdlib import as
    # a re-exported attribute.
    monkeypatch.setattr("check_release_version.subprocess.run", fake_run)


def test_the_tag_being_released_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    """This fork creates the GitHub release first and lets the resulting tag push
    drive the workflow, so the version under test is already published by the
    time the guard runs. Comparing against a set containing itself would refuse
    every single release."""
    _fake_gh(monkeypatch, ["v0.39.1", "v0.39.0", "v0.38.0"])

    assert guard.main(["owner/repo", "v0.39.1"]) == 0


def test_an_older_tag_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh(monkeypatch, ["v0.39.0", "v0.38.0"])

    assert guard.main(["owner/repo", "v0.37.9"]) == 1


def test_re_cutting_a_superseded_version_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-publishing an old number silently replaces what users already have.
    The release that superseded it is still in the set, so this is caught."""
    _fake_gh(monkeypatch, ["v0.39.1", "v0.39.0", "v0.38.0"])

    assert guard.main(["owner/repo", "v0.39.0"]) == 1


def test_re_cutting_the_newest_version_cannot_be_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The honest limit of checking after the release exists: re-cutting the
    newest published version is indistinguishable from publishing it. Asserted
    so the gap is a recorded decision rather than a surprise."""
    _fake_gh(monkeypatch, ["v0.39.0", "v0.38.0"])

    assert guard.main(["owner/repo", "v0.39.0"]) == 0


def test_a_newer_tag_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh(monkeypatch, ["v0.39.1", "v0.39.0"])

    assert guard.main(["owner/repo", "v0.40.0"]) == 0


def test_the_first_release_has_nothing_to_compare_against(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_gh(monkeypatch, ["v0.1.0"])

    assert guard.main(["owner/repo", "v0.1.0"]) == 0


def test_drafts_do_not_count_as_published(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh(monkeypatch, ["v9.9.9", "v0.38.0"], drafts=("v9.9.9",))

    assert guard.main(["owner/repo", "v0.39.0"]) == 0


def test_a_malformed_historical_tag_does_not_block_a_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Old tags predate the versioning rule. Refusing to ship because one of
    them cannot be parsed would punish today's release for yesterday's mess."""
    _fake_gh(monkeypatch, ["nightly", "v0.38.0"])

    assert guard.main(["owner/repo", "v0.39.0"]) == 0


def test_a_malformed_new_tag_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """SemVer is required for what this fork publishes; an unparseable tag
    cannot be shown to be newer than anything."""
    _fake_gh(monkeypatch, ["v0.38.0"])

    assert guard.main(["owner/repo", "nightly-2026-08-10"]) == 1


def test_bad_arguments_report_usage() -> None:
    assert guard.main(["only-one"]) == 2


def test_the_windows_version_resource_tracks_pyproject() -> None:
    """The exe's version comes from pyproject, not a second copy that can drift.

    A blank or stale version on a downloaded binary is unfalsifiable from the
    outside: the properties dialog simply shows nothing.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import make_version_file

    rendered = make_version_file.render("1.2.3")

    assert "filevers=(1, 2, 3, 0)" in rendered
    assert "StringStruct('ProductVersion', '1.2.3')" in rendered
    assert "StringStruct('ProductName', 'agentdeck')" in rendered


def test_a_version_that_is_not_semver_is_refused() -> None:
    """Truncating a four-part or pre-release tag here would make the exe claim
    a version that was never released."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import make_version_file

    for bad in ("1.2", "1.2.3.4", "1.2.3-rc1"):
        with pytest.raises(ValueError):
            make_version_file.version_tuple(bad)


def test_every_stdlib_hook_script_is_bundled() -> None:
    """A hook script missing from the build fails silently: the installer's
    source lookup returns None and the feature simply never installs, with
    nothing on screen to say why. Caught exactly that way for the Antigravity
    status line, which shipped absent from its first build.
    """
    root = Path(__file__).resolve().parent.parent
    build = (root / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    missing = [
        script.name
        for script in sorted(root.glob("usage_statusline*.py"))
        + sorted(root.glob("usage_session_resume.py"))
        + sorted(root.glob("usage_terse*.py"))
        if f"'{script.name}'" not in build
    ]

    assert not missing, f"hook scripts absent from the Windows bundle: {missing}"
