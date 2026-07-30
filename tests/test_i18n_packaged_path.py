# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Regression tests for ``i18n.packaged_resource_path``.

In a frozen build the module lives inside the bundle, so the source-adjacent
path points into an archive rather than at a readable file — reading it raised
``NotADirectoryError`` at launch. The fix prefers PyInstaller's ``sys._MEIPASS``
and falls back to the source path only when running outside a bundle.

These cases covered py2app's ``RESOURCEPATH`` until macOS support was removed on
2026-07-29. Nothing sets that variable now, so they moved to ``_MEIPASS`` and one
test was added to pin that the old variable is genuinely ignored.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from i18n import packaged_resource_path


def test_prefers_the_bundle_when_the_file_is_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    bundled = bundle / "i18n.json"
    bundled.write_text("{}", encoding="utf-8")
    source = tmp_path / "src" / "i18n.json"
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert packaged_resource_path("i18n.json", source) == bundled


def test_falls_back_to_the_source_path_outside_a_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    source = tmp_path / "i18n.json"

    assert packaged_resource_path("i18n.json", source) == source


def test_falls_back_when_the_bundle_lacks_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A resource the build forgot to declare must not resolve to a path that does
    # not exist; falling back to the source copy turns a packaging mistake into a
    # working app instead of a read error at some random later moment.
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    source = tmp_path / "src" / "i18n.json"
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert packaged_resource_path("i18n.json", source) == source


def test_an_empty_meipass_is_treated_as_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "i18n.json"
    monkeypatch.setattr(sys, "_MEIPASS", "", raising=False)

    assert packaged_resource_path("i18n.json", source) == source


def test_nested_resource_names_resolve_under_the_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # persona_store asks for "personas" and html_report for
    # "critters/<beast>/wrapped.png", so names with separators have to work.
    bundle = tmp_path / "_internal"
    nested = bundle / "critters" / "phoenix"
    nested.mkdir(parents=True)
    target = nested / "wrapped.png"
    target.write_bytes(b"png")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    resolved = packaged_resource_path(
        "critters/phoenix/wrapped.png", tmp_path / "src" / "wrapped.png"
    )

    assert resolved == target


def test_a_source_path_that_points_inside_an_archive_is_avoided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end repro of the original crash.

    Pre-fix the source-mode path was the only option, and in a frozen build it
    resolved to something like ``lib/python313.zip/i18n.json`` — a path through a
    regular file, which raises ``NotADirectoryError`` on read. This rebuilds that
    shape and asserts the bundled copy wins.
    """
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    (bundle / "i18n.json").write_text('{"en": {}}', encoding="utf-8")

    fake_archive = bundle / "lib" / "python313.zip"
    fake_archive.parent.mkdir()
    fake_archive.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty-zip footer
    crashing_source_path = fake_archive / "i18n.json"
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    resolved = packaged_resource_path("i18n.json", crashing_source_path)

    assert resolved != crashing_source_path
    assert resolved.read_text(encoding="utf-8") == '{"en": {}}'


def test_py2apps_resourcepath_is_no_longer_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # macOS packaging is gone. A RESOURCEPATH in the environment now belongs to
    # some other tool, not to a bundle we produced, so following it would read a
    # stranger's file.
    bundle = tmp_path / "Resources"
    bundle.mkdir()
    (bundle / "i18n.json").write_text("{}", encoding="utf-8")
    source = tmp_path / "src" / "i18n.json"
    monkeypatch.setenv("RESOURCEPATH", str(bundle))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert packaged_resource_path("i18n.json", source) == source
