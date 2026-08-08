# SPDX-License-Identifier: AGPL-3.0-only
"""Keep SECURITY.md's list of outbound connections true.

The claim "here is every endpoint this app contacts" is only worth making if
something enforces it. A prose list decays the moment someone adds a fetch, and
it decays silently -- the app keeps working, the document just quietly becomes
a lie about a privacy-sensitive detail.

So the test reads the URLs out of the shipped code and requires each one to
appear in both language versions. It deliberately looks at what the code does,
not at what a comment says it does.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECURITY_DOCS = ("SECURITY.md", "SECURITY.en.md")

# Not shipped to users: dev tooling, tests, build output and the vendored
# upstream copy kept for reference.
EXCLUDED_DIRS = {
    ".git", ".venv", "build", "dist", "reference", "__pycache__", "fuzz",
    "tests", "tools", "scripts", "node_modules", "docs",
}

# Matches a hostname inside an https URL literal.
_URL = re.compile(r"https://([a-z0-9.-]+)(/[^\s\"')]*)?", re.IGNORECASE)

# URL prefixes that appear as data rather than as something the app connects to.
# Matched against host+path, so an entry cannot accidentally excuse a whole host:
# "api.openai.com/auth" is a JWT claim key, while a real request to
# api.openai.com/anything-else would still have to be disclosed.
NOT_A_CONNECTION = (
    # A JWT claim *key* in analyzer/subscription.py -- parsed, never fetched.
    "api.openai.com/auth",
    # Links the user chooses to open in their own browser, not fetched by us.
    "github.com/",
    "datatracker.ietf.org/",
    "semver.org/",
    "keepachangelog.com/",
    "www.gnu.org/",
)


def _shipped_python_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if not EXCLUDED_DIRS & set(path.relative_to(ROOT).parts)
    ]


def test_every_endpoint_the_app_contacts_is_disclosed() -> None:
    documents = {name: (ROOT / name).read_text(encoding="utf-8") for name in SECURITY_DOCS}

    undisclosed: list[str] = []
    for path in _shipped_python_files():
        source = path.read_text(encoding="utf-8")
        # Only lines that actually build a request, not links in prose.
        for line in source.splitlines():
            if "https://" not in line or line.lstrip().startswith("#"):
                continue
            for host, rest in _URL.findall(line):
                if (host + (rest or "")).startswith(NOT_A_CONNECTION):
                    continue
                for name, text in documents.items():
                    if host not in text:
                        undisclosed.append(f"{path.relative_to(ROOT)}: {host} missing from {name}")

    assert not undisclosed, "outbound endpoints absent from the security disclosure:\n" + "\n".join(
        sorted(set(undisclosed))
    )


def test_the_disclosure_names_the_public_oauth_client() -> None:
    """The GOCSPX- constant in the source reads as a leaked secret to anyone
    scanning the repo. If it ships, the reason it is not one has to ship too."""
    probe = (ROOT / "providers" / "agy_quota_probe.py").read_text(encoding="utf-8")
    if "GOCSPX-" not in probe:
        return

    for name in SECURITY_DOCS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "GOCSPX-" in text, f"{name} does not explain the public OAuth client constant"
        assert "RFC 8252" in text, f"{name} does not cite why a public client is not a secret"
