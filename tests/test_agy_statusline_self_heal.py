from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import session_hooks
import setup_hook


@pytest.fixture
def agy_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    source = tmp_path / "source.py"
    target = tmp_path / "installed.py"
    settings = tmp_path / "settings.json"
    source.write_bytes(b"# new\r\n")
    target.write_bytes(b"# old\n")
    settings.write_text(
        json.dumps({"statusLine": {"command": f"python {target}", "enabled": True}})
    )
    monkeypatch.setattr(setup_hook, "AGY_HOOK_TARGET", target)
    monkeypatch.setattr(setup_hook, "AGY_SETTINGS", settings)
    monkeypatch.setattr(setup_hook, "_resolve_agy_hook_source", lambda: source)
    for name in ("_self_heal_statuslines", "_self_heal_resume", "_self_heal_terse_mode"):
        monkeypatch.setattr(session_hooks, name, lambda: None)
    return source, target


def test_self_heal_atomically_refreshes_stale_agy_copy(
    agy_copy: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source, target = agy_copy
    original_replace = os.replace
    replacements: list[bytes] = []

    def replace(src: str, dst: str | Path) -> None:
        assert target.read_bytes() == b"# old\n"
        replacements.append(Path(src).read_bytes())
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    session_hooks.self_heal()
    assert target.read_bytes() == source.read_bytes()
    assert replacements == [source.read_bytes()]
    session_hooks.self_heal()
    assert len(replacements) == 1


@pytest.mark.parametrize(
    "state", ["missing", "disabled", "removed", "external", "source_missing"]
)
def test_self_heal_does_not_install_or_enable_agy_statusline(
    agy_copy: tuple[Path, Path], state: str
) -> None:
    source, target = agy_copy
    settings = setup_hook.AGY_SETTINGS
    if state == "missing":
        target.unlink()
    elif state == "source_missing":
        source.unlink()
    else:
        statusline = {"command": f"python {target}", "enabled": False}
        if state == "external":
            statusline = {"command": "other.py", "enabled": True}
        settings.write_text(
            json.dumps({} if state == "removed" else {"statusLine": statusline})
        )
    before = settings.read_bytes()
    session_hooks.self_heal()
    assert settings.read_bytes() == before
    if state == "missing":
        assert not target.exists()
    else:
        assert target.read_bytes() == b"# old\n"


def test_failed_agy_replacement_preserves_copy_and_cleans_temporary_file(
    agy_copy: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, target = agy_copy

    def deny_replace(src: str, dst: str | Path) -> None:
        raise PermissionError("replacement denied")

    monkeypatch.setattr(os, "replace", deny_replace)
    session_hooks.self_heal()
    assert target.read_bytes() == b"# old\n"
    assert not list(target.parent.glob("*.tmp"))
