# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Resource resolution for the panel assets.

``resolve_resource`` and ``_i18n_path`` are how every panel finds its HTML, its
icons, and its translations. They had no tests: if either resolved wrongly the
symptom is a blank panel at runtime, which is exactly the kind of failure that
should not wait for a person to notice it.

Note the asymmetry between them — ``resolve_resource`` prefixes ``assets/`` under
the bundle root while ``_i18n_path`` does not, because i18n.json is bundled at
the top level and the panel files under ``assets/``. Getting that backwards is
the likely mistake here, so both directions are pinned.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from panels.payload import _i18n_path, resolve_resource

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_resolve_resource_uses_the_repo_assets_outside_a_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    resolved = Path(resolve_resource("panels/classic.html"))

    assert resolved == REPO_ROOT / "assets" / "panels" / "classic.html"
    assert resolved.is_file(), "the real panel asset moved or was renamed"


def test_resolve_resource_prefers_the_bundle_under_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "_internal"
    target = bundle / "assets" / "panels" / "classic.html"
    target.parent.mkdir(parents=True)
    target.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert Path(resolve_resource("panels/classic.html")) == target


def test_resolve_resource_falls_back_when_the_bundle_lacks_the_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    resolved = Path(resolve_resource("panels/classic.html"))

    assert resolved == REPO_ROOT / "assets" / "panels" / "classic.html"


def test_i18n_path_is_at_the_bundle_root_not_under_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # build_windows.ps1 bundles i18n.json with destination "." — putting the
    # lookup under assets/ instead would make every panel render untranslated.
    bundle = tmp_path / "_internal"
    bundle.mkdir()
    target = bundle / "i18n.json"
    target.write_text("{}", encoding="utf-8")
    (bundle / "assets").mkdir()
    (bundle / "assets" / "i18n.json").write_text('{"decoy": {}}', encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert _i18n_path() == target


def test_i18n_path_uses_the_repo_copy_outside_a_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    resolved = _i18n_path()

    assert resolved == REPO_ROOT / "i18n.json"
    assert resolved.is_file()


def test_neither_helper_consults_py2apps_resourcepath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Merge guard, same reasoning as tests/test_i18n_packaged_path.py: upstream
    # still reads RESOURCEPATH in this module, and this fork merges from upstream
    # weekly. Without this, a merge could quietly restore a lookup that macOS
    # removal took out.
    bundle = tmp_path / "Resources"
    (bundle / "panels").mkdir(parents=True)
    (bundle / "panels" / "classic.html").write_text("decoy", encoding="utf-8")
    (bundle / "i18n.json").write_text('{"decoy": {}}', encoding="utf-8")
    monkeypatch.setenv("RESOURCEPATH", str(bundle))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert Path(resolve_resource("panels/classic.html")) != bundle / "panels" / "classic.html"
    assert _i18n_path() != bundle / "i18n.json"
