# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Guard the URLs this fork hands to users.

Renaming the project left stale links three separate times, and each one
pointed somewhere that still belonged to the old name: the update checker
queried upstream's releases, an install script downloaded upstream's hook, and
the AI Update Daily menu item opened a Pages path that 404s. None of them broke
a test, because a URL is just a string until someone clicks it.

Outgoing URLs are their own category during a rename. Grepping for the product
name does not find them -- `aqua5230/usage` contains neither `agentdeck` nor
anything a rename script would look for.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Where the fork actually lives. Anything user-facing must point here.
REPO_URL = "https://github.com/SanHsien/agentdeck"
PAGES_URL = "https://sanhsien.github.io/agentdeck"

# reference/ is upstream's code kept verbatim for porting comparisons, and the
# changelog records what URLs used to be. Both are supposed to name the old repo.
SKIP_DIRS = {
    ".git", ".venv", "build", "dist", "reference", "__pycache__",
    "node_modules", ".ruff_cache", ".mypy_cache", ".pytest_cache",
}
SKIP_FILES = {"CHANGELOG.en.md", "CHANGELOG.md", "uv.lock"}

SHIPPED_SUFFIXES = {".py", ".html", ".json", ".ps1", ".yml", ".yaml"}

STALE = re.compile(
    r"https://(?:github\.com/SanHsien/usage|sanhsien\.github\.io/usage)\b",
    re.IGNORECASE,
)


def _shipped_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SHIPPED_SUFFIXES:
            continue
        if path.name in SKIP_FILES:
            continue
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def test_no_shipped_file_points_at_the_pre_rename_repo() -> None:
    offenders: list[str] = []
    for path in _shipped_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in STALE.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(ROOT).as_posix()}:{line} -> {match.group()}")

    assert not offenders, (
        "these still point at the repository's pre-rename name, which 404s or "
        "sends users to a different project:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    ("module", "attribute", "expected"),
    [("update_checker", "GITHUB_RELEASES_API", "SanHsien/agentdeck")],
)
def test_outgoing_api_calls_name_this_fork(module: str, attribute: str, expected: str) -> None:
    """The update check is the one URL a user never sees but always follows."""
    imported = __import__(module)

    assert expected in getattr(imported, attribute)


def test_every_link_the_menu_opens_belongs_to_this_fork() -> None:
    """Menu links follow the repository name silently; nothing else warns you.

    Both spellings are checked because both have gone stale before: a Pages
    path (`sanhsien.github.io/usage/...`, which 404s after the rename) and a
    repository URL in the generated report footer.
    """
    source = (ROOT / "wintray.py").read_text(encoding="utf-8")

    # Every literal, not just the GitHub-looking ones. Filtering on
    # `"github.com" in url` first meant a link to anywhere else was skipped
    # entirely rather than caught -- the check exempted exactly the URLs most
    # worth objecting to. (It is also what CodeQL flags as incomplete URL
    # substring sanitization, for the same underlying reason.)
    opened = re.findall(r'webbrowser\.open\(\s*f?"([^"]+)"', source)

    assert opened, "no literal link found in the menu; this guard has gone stale"
    for url in opened:
        assert url.startswith((REPO_URL, PAGES_URL)), (
            f"{url} points outside this fork ({REPO_URL} / {PAGES_URL})"
        )


def test_every_link_the_menu_opens_from_a_variable_is_validated() -> None:
    """A literal URL is auditable by reading it; one built at run time is not.

    webbrowser.open(release.html_url) hands an address that arrived over the
    network straight to the browser, and the update prompt shows it to the user
    as the thing to trust. update_checker pins it to this repository's releases
    prefix -- but only that one call is accounted for here, so a new
    variable-valued call has to come with its own validation and be added below.
    """
    import update_checker

    source = (ROOT / "wintray.py").read_text(encoding="utf-8")

    non_literal = re.findall(r'webbrowser\.open\(\s*(?!f?")([^)\s][^)]*)\)', source)

    assert set(non_literal) <= {"release.html_url"}, (
        f"unaccounted-for dynamic link(s) passed to webbrowser.open: {non_literal}. "
        "Validate the value at its source and list it here."
    )
    assert update_checker.RELEASE_URL_PREFIX.startswith(REPO_URL + "/"), (
        "update_checker no longer pins release URLs to this fork"
    )
