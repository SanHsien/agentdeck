# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

import session_hooks
import setup_hook
from tests.helpers import SetupHookPaths, expected_statusline_command

LEGACY_NAME = "usag"


def test_windows_cli_output_reconfigures_both_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    class Stream:
        def __init__(self) -> None:
            self.encodings: list[str] = []

        def reconfigure(self, *, encoding: str) -> None:
            self.encodings.append(encoding)

    stdout = Stream()
    stderr = Stream()
    monkeypatch.setattr(setup_hook, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    setup_hook.configure_windows_utf8_output()

    assert stdout.encodings == ["utf-8"]
    assert stderr.encodings == ["utf-8"]


@pytest.fixture
def setup_paths(patch_setup_hook_paths: Callable[..., SetupHookPaths]) -> SetupHookPaths:
    return patch_setup_hook_paths(legacy_name=LEGACY_NAME)


def test_setup_creates_new_settings_with_usage_statusline(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target

    exit_code = setup_hook.setup()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data["statusLine"]["type"] == "command"
    assert data["statusLine"]["command"] == expected_statusline_command(hook_target)
    assert hook_target.exists()


def test_setup_backs_up_existing_statusline_and_is_idempotent(
    setup_paths: SetupHookPaths,
) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    original = {"type": "command", "command": "echo original"}
    settings.write_text(json.dumps({"statusLine": original}), encoding="utf-8")

    assert setup_hook.setup() == 0
    assert setup_hook.setup() == 0

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == expected_statusline_command(
        setup_hook.FORWARDER_TARGET
    )
    assert data["agentdeck"]["previousStatusLine"] == original
    assert hook_target.exists()
    assert setup_hook.FORWARDER_TARGET.exists()


def test_unsetup_restores_backup_and_removes_hook_files(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    status_file = setup_paths.status_file
    previous = {"type": "command", "command": "echo original"}
    settings.write_text(
        json.dumps(
            {
                "statusLine": {"type": "command", "command": f"/usr/bin/python3 {hook_target}"},
                "agentdeck": {"previousStatusLine": previous},
            }
        ),
        encoding="utf-8",
    )
    hook_target.write_text("print('hook')\n", encoding="utf-8")
    setup_hook.FORWARDER_TARGET.write_text("print('forwarder')\n", encoding="utf-8")
    status_file.write_text("{}", encoding="utf-8")

    exit_code = setup_hook.unsetup()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data["statusLine"] == previous
    assert "usage" not in data
    assert not hook_target.exists()
    assert not setup_hook.FORWARDER_TARGET.exists()
    assert not status_file.exists()


def test_unsetup_without_install_is_safe_and_is_usage_hook_detects_commands(
    setup_paths: SetupHookPaths,
) -> None:
    _ = setup_paths

    assert setup_hook.unsetup() == 0
    assert setup_hook._is_usage_hook({"command": "python3 /tmp/agentdeck-statusline.py"})
    assert not setup_hook._is_usage_hook({"command": "python3 /tmp/other.py"})


def test_migration_removes_legacy_files_and_moves_backup(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    legacy_hook = setup_hook.LEGACY_HOOK_TARGET
    legacy_status = setup_hook.LEGACY_STATUS_FILE
    legacy_hook.write_text("legacy hook\n", encoding="utf-8")
    legacy_status.write_text("{}", encoding="utf-8")
    previous = {"type": "command", "command": "echo original"}
    settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": f"python3 {legacy_hook}",
                },
                LEGACY_NAME: {"previousStatusLine": previous},
            }
        ),
        encoding="utf-8",
    )

    setup_hook._migrate_from_legacy_usage()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert not legacy_hook.exists()
    assert not legacy_status.exists()
    assert "statusLine" not in data
    assert LEGACY_NAME not in data
    assert data["agentdeck"]["previousStatusLine"] == previous


def test_migrate_legacy_usage_skips_bad_utf8_settings(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    settings.write_bytes(b"\xff\xfe{")

    setup_hook._migrate_from_legacy_usage()

    assert settings.read_bytes() == b"\xff\xfe{"


def test_load_settings_bad_utf8_raises_system_exit(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    settings.write_bytes(b"\xff\xfe{")

    with pytest.raises(SystemExit, match="settings.json"):
        setup_hook._load_settings()


@pytest.mark.skipif(
    sys.platform == "win32", reason="exercises POSIX shell quoting via /bin/sh"
)
def test_statusline_command_quotes_paths_with_spaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import subprocess

    bin_dir = tmp_path / "含 空格" / "bin"
    hook_dir = tmp_path / "Claude Code 小工具"
    bin_dir.mkdir(parents=True)
    hook_dir.mkdir()
    argv_file = tmp_path / "argv.txt"
    fake_python = bin_dir / "python3"
    hook_file = hook_dir / "usage statusline.py"
    fake_python.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$1\" > {setup_hook._shell_arg(str(argv_file))}\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    hook_file.write_text("print('unused')\n", encoding="utf-8")

    monkeypatch.setattr(setup_hook, "_find_system_python", lambda: str(fake_python))
    monkeypatch.setattr(setup_hook, "HOOK_TARGET", hook_file)

    cmd = setup_hook._statusline_command()

    result = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert argv_file.read_text(encoding="utf-8").strip() == str(hook_file)


def test_find_system_python_prefers_usr_bin_over_bundled_app_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", "/Applications/usage.app/Contents/MacOS/python")
    monkeypatch.setattr(
        "setup_hook.os.path.exists",
        lambda path: path == "/usr/bin/python3",
    )

    assert setup_hook._find_system_python() == "/usr/bin/python3"


def test_find_system_python_uses_current_interpreter_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", r"C:\\Program Files\\Python\\python.exe")

    assert setup_hook._find_system_python() == r"C:\\Program Files\\Python\\python.exe"


def test_find_system_python_skips_unusable_windows_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    candidates = {
        "python": r"C:\\Users\\test\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe",
        "py": r"C:\\Program Files\\Python\\py.exe",
    }
    monkeypatch.setattr(shutil, "which", candidates.get)
    monkeypatch.setattr(
        setup_hook,
        "_is_working_python",
        lambda path: path == candidates["py"],
    )

    assert setup_hook._find_system_python() == candidates["py"]


def test_find_system_python_uses_working_windows_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    candidate = r"C:\\Program Files\\Python\\python.exe"
    monkeypatch.setattr(shutil, "which", lambda name: candidate if name == "python" else None)
    monkeypatch.setattr(setup_hook, "_is_working_python", lambda path: path == candidate)

    assert setup_hook._find_system_python() == candidate


def test_find_system_python_avoids_non_ascii_windows_interpreter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", r"C:\\專案\\usage\\.venv\\Scripts\\python.exe")
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: r"C:\\Program Files\\Python\\python.exe" if name == "python" else None,
    )
    monkeypatch.setattr(setup_hook, "_is_working_python", lambda _path: True)

    assert setup_hook._find_system_python() == r"C:\\Program Files\\Python\\python.exe"


def test_windows_hook_commands_use_double_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        setup_hook, "_find_system_python", lambda: r"C:\Program Files\Python\python.exe"
    )
    monkeypatch.setattr(
        setup_hook,
        "HOOK_TARGET",
        Path(r"C:\Users\test user\.claude\agentdeck-statusline.py"),
    )
    monkeypatch.setattr(
        setup_hook,
        "FORWARDER_TARGET",
        Path(r"C:\Users\test user\.claude\agentdeck-statusline-forwarder.py"),
    )

    assert setup_hook._statusline_command() == (
        '"C:/Program Files/Python/python.exe" '
        '"C:/Users/test user/.claude/agentdeck-statusline.py"'
    )
    assert setup_hook._forwarder_command() == (
        '"C:/Program Files/Python/python.exe" '
        '"C:/Users/test user/.claude/agentdeck-statusline-forwarder.py"'
    )


def test_windows_statusline_migration_rewrites_legacy_backslash_paths(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        setup_hook, "_find_system_python", lambda: r"C:\Program Files\Python\python.exe"
    )
    command = (
        r"C:\Program Files\Python\python.exe "
        rf"{setup_paths.hook_target}".replace("/", "\\")
    )
    setup_paths.settings.write_text(
        json.dumps({"statusLine": {"type": "command", "command": command}}),
        encoding="utf-8",
    )

    setup_hook._migrate_windows_statusline_command_if_needed()

    data = json.loads(setup_paths.settings.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == expected_statusline_command(setup_paths.hook_target)
    assert data["agentdeck"]["selfHealLog"][-1]["action"] == "migrate_windows_statusline"


def test_windows_statusline_migration_rewrites_non_ascii_interpreter(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        setup_hook, "_find_system_python", lambda: r"C:\\Program Files\\Python\\python.exe"
    )
    setup_paths.settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": (
                        r"C:/Users/USER/Desktop/GitHub專案/usage/.venv/Scripts/python.exe "
                        f"{setup_paths.hook_target}"
                    ),
                }
            }
        ),
        encoding="utf-8",
    )

    setup_hook._migrate_windows_statusline_command_if_needed()

    data = json.loads(setup_paths.settings.read_text(encoding="utf-8"))
    command = data["statusLine"]["command"]
    assert command == expected_statusline_command(setup_paths.hook_target)
    assert command.isascii()


def test_setup_codex_replaces_only_tui_status_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_backup = tmp_path / ".codex" / "agentdeck-backup.json"
    codex_config.parent.mkdir()
    codex_config.write_text(
        """
[other]
status_line = ["external"]

[tui]
status_line = ["old"]

[another]
status_line = ["keep"]
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", codex_backup)

    setup_hook._setup_codex()
    content = codex_config.read_text(encoding="utf-8")

    assert '[other]\nstatus_line = ["external"]' in content
    assert '[another]\nstatus_line = ["keep"]' in content
    assert content.count("status_line = [") == 3
    assert '"five-hour-limit"' in content


def test_setup_codex_ignores_tui_text_outside_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_backup = tmp_path / ".codex" / "agentdeck-backup.json"
    codex_config.parent.mkdir()
    codex_config.write_text(
        '''
note = """
[tui]
"""
# [tui]
'''.lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", codex_backup)

    setup_hook._setup_codex()
    content = codex_config.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    assert content.count("[tui]") == 3
    assert parsed["note"] == "[tui]\n"
    assert parsed["tui"]["status_line"] == setup_hook.CODEX_STATUS_LINE
    assert '"five-hour-limit"' in content


def test_setup_preserves_initial_backup_on_reinstall(
    setup_paths: SetupHookPaths,
) -> None:
    settings = setup_paths.settings
    original = {"type": "command", "command": "echo original"}
    replacement = {"type": "command", "command": "echo replacement"}
    settings.write_text(json.dumps({"statusLine": original}), encoding="utf-8")

    assert setup_hook.setup() == 0

    data = json.loads(settings.read_text(encoding="utf-8"))
    data["statusLine"] = replacement
    settings.write_text(json.dumps(data), encoding="utf-8")

    assert setup_hook.setup() == 0

    reinstalled = json.loads(settings.read_text(encoding="utf-8"))
    assert reinstalled["agentdeck"]["previousStatusLine"] == original


def test_unsetup_codex_removes_only_tui_status_line_without_backup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_backup = tmp_path / ".codex" / "agentdeck-backup.json"
    legacy_backup = tmp_path / ".codex" / "tt-backup.json"
    codex_config.parent.mkdir()
    codex_config.write_text(
        """
[other]
status_line = ["external"]

[tui]
status_line = ["old"]

[another]
status_line = ["keep"]
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", codex_backup)
    monkeypatch.setattr(setup_hook, "LEGACY_CODEX_BACKUP", legacy_backup)

    setup_hook._unsetup_codex()
    content = codex_config.read_text(encoding="utf-8")

    assert '[other]\nstatus_line = ["external"]' in content
    assert '[another]\nstatus_line = ["keep"]' in content
    assert "[tui]\nstatus_line" not in content


def test_unsetup_codex_keeps_backup_when_restore_write_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_backup = tmp_path / ".codex" / "agentdeck-backup.json"
    legacy_backup = tmp_path / ".codex" / "tt-backup.json"
    codex_config.parent.mkdir()
    codex_config.write_text('[tui]\nstatus_line = ["old"]\n', encoding="utf-8")
    codex_backup.write_text(json.dumps({"status_line": ["original"]}), encoding="utf-8")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", codex_backup)
    monkeypatch.setattr(setup_hook, "LEGACY_CODEX_BACKUP", legacy_backup)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(setup_hook, "_atomic_write_text", _boom)

    with pytest.raises(OSError):
        setup_hook._unsetup_codex()

    # A failed restore must leave the backup intact so a retry can still recover.
    assert codex_backup.exists()


def test_read_codex_config_bad_utf8_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_config.parent.mkdir()
    codex_config.write_bytes(b"\xff\xfe[tui]\n")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)

    assert setup_hook._read_codex_config() is None


def test_setup_codex_warns_when_existing_config_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_config.parent.mkdir()
    codex_config.write_bytes(b"\xff\xfe[tui]\n")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)

    setup_hook._setup_codex()

    assert "Codex" in capsys.readouterr().out


def test_unsetup_codex_bad_utf8_backup_falls_back_to_empty_status_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_backup = tmp_path / ".codex" / "agentdeck-backup.json"
    legacy_backup = tmp_path / ".codex" / "tt-backup.json"
    codex_config.parent.mkdir()
    codex_config.write_text('[tui]\nstatus_line = ["old"]\n', encoding="utf-8")
    codex_backup.write_bytes(b"\xff\xfe{")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", codex_config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", codex_backup)
    monkeypatch.setattr(setup_hook, "LEGACY_CODEX_BACKUP", legacy_backup)

    setup_hook._unsetup_codex()

    content = codex_config.read_text(encoding="utf-8")
    assert "status_line = []" in content
    assert tomllib.loads(content)["tui"]["status_line"] == []
    assert not codex_backup.exists()


def test_self_heal_installs_when_no_statusline(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target

    session_hooks.self_heal()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert data["statusLine"]["command"] == expected_statusline_command(hook_target)
    assert data["agentdeck"]["selfHealLog"][-1]["action"] == "install_hook"


def test_self_heal_skips_external_statusline(setup_paths: SetupHookPaths) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    external = {"type": "command", "command": "python3 ccusage.py"}
    settings.write_text(json.dumps({"statusLine": external}), encoding="utf-8")

    session_hooks.self_heal()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert data == {"statusLine": external}
    assert not hook_target.exists()


def test_self_heal_updates_owned_hook(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    source = setup_paths.hook_source
    source.write_text('__version__ = "1.0"\n', encoding="utf-8")
    monkeypatch.setattr(setup_hook, "_resolve_hook_source", lambda: source)
    settings.write_text(
        json.dumps(
            {"statusLine": {"type": "command", "command": f"/usr/bin/python3 {hook_target}"}}
        ),
        encoding="utf-8",
    )
    hook_target.write_text('__version__ = "0.9"\n', encoding="utf-8")

    session_hooks.self_heal()
    data = json.loads(settings.read_text(encoding="utf-8"))

    assert hook_target.read_text(encoding="utf-8") == '__version__ = "1.0"\n'
    assert data["agentdeck"]["selfHealLog"][-1]["action"] == "update_hook"


def test_self_heal_migrates_bundled_python_commands(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
    tmp_path: Path,
) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    resume_source = tmp_path / "usage_session_resume.py"
    resume_source.write_text('__version__ = "1.0"\n', encoding="utf-8")
    monkeypatch.setattr(session_hooks, "_resolve_resume_source", lambda: resume_source)
    resume_target = tmp_path / ".claude" / "agentdeck-session-resume.py"
    monkeypatch.setattr(session_hooks, "RESUME_HOOK_TARGET", resume_target)
    settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": f"/Applications/usage.app/Contents/MacOS/python {hook_target}",
                },
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": session_hooks.RESUME_MATCHER,
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": (
                                        "/Applications/usage.app/Contents/MacOS/python "
                                        f"{resume_source}"
                                    ),
                                }
                            ],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    session_hooks._migrate_bundled_python_commands_if_needed()

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == expected_statusline_command(hook_target)
    hooks = data["hooks"]["SessionStart"][0]["hooks"]
    assert hooks[0]["command"] == expected_statusline_command(resume_target)
    migrate_entries = [
        entry
        for entry in data["agentdeck"]["selfHealLog"]
        if entry["action"] == "migrate_bundled_python"
    ]
    assert migrate_entries
    assert "statusLine=direct" in migrate_entries[-1]["detail"]
    assert "resume" in migrate_entries[-1]["detail"]


def test_self_heal_keeps_correct_python_commands_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    setup_paths: SetupHookPaths,
    tmp_path: Path,
) -> None:
    settings = setup_paths.settings
    hook_target = setup_paths.hook_target
    resume_target = tmp_path / ".claude" / "agentdeck-session-resume.py"
    monkeypatch.setattr(session_hooks, "RESUME_HOOK_TARGET", resume_target)
    resume_command = session_hooks._resume_command()
    settings.write_text(
        json.dumps(
            {
                "statusLine": {
                    "type": "command",
                    "command": f"/usr/bin/python3 {hook_target}",
                },
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": session_hooks.RESUME_MATCHER,
                            "hooks": [{"type": "command", "command": resume_command}],
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    session_hooks._migrate_bundled_python_commands_if_needed()

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["statusLine"]["command"] == f"/usr/bin/python3 {hook_target}"
    assert data["hooks"]["SessionStart"][0]["hooks"][0]["command"] == resume_command
    assert "usage" not in data


def test_writing_through_a_symlink_keeps_the_link(tmp_path: Path) -> None:
    """os.replace swaps the directory entry, so writing straight at the link
    turns a settings file someone keeps in a dotfiles repo into a regular file
    -- detached, with our copy as the only one left."""
    real = tmp_path / "dotfiles" / "settings.json"
    real.parent.mkdir()
    real.write_text('{"old": true}', encoding="utf-8")
    link = tmp_path / "settings.json"
    try:
        link.symlink_to(real)
    except OSError as exc:  # pragma: no cover - needs developer mode on Windows
        pytest.skip(f"symlink creation is not permitted here: {exc}")

    setup_hook._atomic_write_text(link, '{"new": true}')

    assert link.is_symlink(), "the link was replaced by a regular file"
    assert real.read_text(encoding="utf-8") == '{"new": true}'


def _codex_config_with(status_line: list[str]) -> str:
    body = ",\n".join(f'  "{segment}"' for segment in status_line)
    return f'[tui]\nstatus_line = [\n{body},\n]\n'


def test_upgrading_our_own_codex_status_line_keeps_the_users_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The upgrade must not treat our own previous output as the user's setting.

    Backing it up would overwrite the only record of what they actually had, and
    uninstalling would then hand them a status line they never chose.
    """
    config = tmp_path / "config.toml"
    backup = tmp_path / "agentdeck-backup.json"
    config.write_text(_codex_config_with(setup_hook.LEGACY_CODEX_STATUS_LINES[0]), encoding="utf-8")
    backup.write_text('{"status_line": ["their", "own", "choice"]}\n', encoding="utf-8")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", backup)

    setup_hook._setup_codex()

    assert "git-branch" in config.read_text(encoding="utf-8")
    assert json.loads(backup.read_text(encoding="utf-8")) == {
        "status_line": ["their", "own", "choice"]
    }, "the upgrade overwrote the user's real backup with our own old value"


def test_a_users_own_codex_status_line_is_still_backed_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.toml"
    backup = tmp_path / "agentdeck-backup.json"
    config.write_text(_codex_config_with(["project", "model"]), encoding="utf-8")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", config)
    monkeypatch.setattr(setup_hook, "CODEX_BACKUP", backup)

    setup_hook._setup_codex()

    assert json.loads(backup.read_text(encoding="utf-8")) == {
        "status_line": ["project", "model"]
    }


def test_an_older_agentdeck_status_line_still_counts_as_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Someone who has not upgraded yet must not be told the hook is foreign --
    that is what would refuse to uninstall it for them."""
    config = tmp_path / "config.toml"
    config.write_text(_codex_config_with(setup_hook.LEGACY_CODEX_STATUS_LINES[0]), encoding="utf-8")
    monkeypatch.setattr(setup_hook, "CODEX_CONFIG", config)

    assert setup_hook.is_codex_setup() is True


def test_the_new_segments_are_ones_codex_actually_supports() -> None:
    """Every segment name has to exist in Codex CLI or the status line silently
    renders nothing for it. Verified against the installed binary on 2026-08-13
    (codex-cli 0.146.0): all seven identifiers are present."""
    assert setup_hook.CODEX_STATUS_LINE == [
        "project",
        "git-branch",
        "five-hour-limit",
        "weekly-limit",
        "context-remaining",
        "used-tokens",
        "model-with-reasoning",
    ]


def _agy_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    settings = tmp_path / "settings.json"
    hook = tmp_path / "agentdeck-statusline-agy.py"
    sidecar = tmp_path / "agentdeck-previous-statusline.json"
    monkeypatch.setattr(setup_hook, "AGY_SETTINGS", settings)
    monkeypatch.setattr(setup_hook, "AGY_HOOK_TARGET", hook)
    monkeypatch.setattr(setup_hook, "AGY_PREVIOUS_STATUSLINE", sidecar)
    return settings, hook, sidecar


def test_the_antigravity_command_runs_on_this_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upstream hardcodes /usr/bin/python3. Installing that on Windows writes a
    status line that can never run and leaves "Statusline Error" in the CLI, so
    the interpreter has to be resolved the same way the Claude hook resolves it.
    """
    settings, hook, _sidecar = _agy_paths(tmp_path, monkeypatch)
    settings.write_text('{"theme": "dark"}\n', encoding="utf-8")

    assert setup_hook._setup_agy() is True

    command = json.loads(settings.read_text(encoding="utf-8"))["statusLine"]["command"]
    assert "/usr/bin/python3" not in command
    interpreter = shlex.split(command, posix=False)[0].strip('"')
    assert Path(os.path.expanduser(interpreter)).exists() or shutil.which(interpreter)
    assert hook.is_file(), "the hook script was not copied next to the settings"


def test_installing_antigravity_keeps_the_users_own_status_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, _hook, sidecar = _agy_paths(tmp_path, monkeypatch)
    settings.write_text(
        json.dumps({"statusLine": {"type": "command", "command": "their-own"}}) + "\n",
        encoding="utf-8",
    )

    assert setup_hook._setup_agy() is True
    assert json.loads(sidecar.read_text(encoding="utf-8"))["command"] == "their-own"

    assert setup_hook._unsetup_agy() is True
    restored = json.loads(settings.read_text(encoding="utf-8"))["statusLine"]
    assert restored["command"] == "their-own"
    assert not sidecar.exists()


def test_uninstalling_antigravity_leaves_the_script_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Antigravity reads its settings once at startup, so deleting the script
    races any CLI that is launching -- and that session shows a status line
    error for its whole life. An unreferenced copy costs nothing."""
    settings, hook, _sidecar = _agy_paths(tmp_path, monkeypatch)
    settings.write_text("{}\n", encoding="utf-8")
    setup_hook._setup_agy()

    setup_hook._unsetup_agy()

    assert "statusLine" not in json.loads(settings.read_text(encoding="utf-8"))
    assert hook.is_file()


def test_antigravity_is_not_installed_when_its_cli_never_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing ~/.gemini means Antigravity's CLI is not set up here. Creating
    the file would leave configuration for a tool the user does not run."""
    settings, _hook, _sidecar = _agy_paths(tmp_path, monkeypatch)

    assert setup_hook._setup_agy() is False
    assert not settings.exists()
