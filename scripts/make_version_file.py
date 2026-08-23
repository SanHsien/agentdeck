#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate the PyInstaller version resource for the Windows executable.

Without one the shipped exe carries no product name and no version at all:
Windows' file properties dialog is blank, and someone holding a downloaded
agentdeck.exe has no way to tell which release it is short of running it.

The version comes from pyproject.toml, which is already the single source of
truth for the release number, so there is no second place to forget.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'SanHsien'),
          StringStruct('FileDescription', '{description}'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'agentdeck'),
          StringStruct('LegalCopyright', 'AGPL-3.0-only'),
          StringStruct('OriginalFilename', 'agentdeck.exe'),
          StringStruct('ProductName', 'agentdeck'),
          StringStruct('ProductVersion', '{version}'),
        ],
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""

DESCRIPTION = "Claude Code, Codex and Antigravity quota in your system tray"


def project_version(pyproject: Path) -> str:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError(f"project.version is {type(version).__name__}, expected str")
    return version


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """Windows wants four numbers; SemVer gives three.

    Rejecting anything else is deliberate: a pre-release or date-stamped tag
    would silently truncate here, and the exe would then claim a version that
    is not the one that was released.
    """
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"expected a three-part version, got {version!r}")
    major, minor, patch = (int(part) for part in parts)
    return (major, minor, patch, 0)


def render(version: str, description: str = DESCRIPTION) -> str:
    return TEMPLATE.format(
        version=version,
        version_tuple=version_tuple(version),
        description=description,
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <output-path>", file=sys.stderr)
        return 2

    version = project_version(REPO_ROOT / "pyproject.toml")
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(version), encoding="utf-8")
    print(f"wrote {output} for agentdeck {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
