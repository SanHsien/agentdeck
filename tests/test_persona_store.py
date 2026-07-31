# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import persona_store

PACK = {
    "id": "demo",
    "name": {"zh-TW": "示範", "en": "Demo"},
    "subtitle": {"zh-TW": "說明", "en": "Subtitle"},
    "icon": "🧪",
    "roles": [
        {
            "id": "demo-role",
            "name": {"zh-TW": "角色", "en": "Role"},
            "persona_name": {"zh-TW": "小示", "en": "Demy"},
            "description": {"zh-TW": "描述", "en": "Description"},
            "icon": "🔍",
            "system_prompt": {"zh-TW": "提示", "en": "Prompt"},
            "quick_tasks": {"zh-TW": ["任務"], "en": ["Task"]},
        }
    ],
}


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point every on-disk path at tmp_path; never touch a real tool directory.

    CODEX_DIR matters as much as AGENTS_DIR: roles install into every detected
    tool, so leaving it unpatched writes into the developer's own
    ``~/.codex/agents`` while the suite runs.
    """
    personas = tmp_path / "personas"
    personas.mkdir()
    (personas / "demo.json").write_text(json.dumps(PACK), encoding="utf-8")
    monkeypatch.setattr(persona_store, "PERSONA_DIR", personas)
    monkeypatch.setattr(persona_store, "AGENTS_DIR", tmp_path / "claude" / "agents")
    monkeypatch.setattr(persona_store, "CODEX_DIR", tmp_path / "codex")
    monkeypatch.setattr(persona_store, "STATE_FILE", tmp_path / "state.json")
    (tmp_path / "claude").mkdir()
    (tmp_path / "codex").mkdir()
    return tmp_path


def test_list_state_shape_matches_what_the_panel_reads(store: Path) -> None:
    state = persona_store.list_state("zh-TW")

    assert state["ok"] is True
    pack = state["packs"][0]
    assert pack["name"] == "示範"
    assert pack["countLabel"] == "0/1"
    role = pack["roles"][0]
    for key in (
        "id",
        "name",
        "personaName",
        "description",
        "systemPrompt",
        "icon",
        "installed",
        "drifted",
        "quickTasks",
        "selectedFolderLabel",
    ):
        assert key in role, key
    assert role["name"] == "角色"
    assert role["quickTasks"] == ["任務"]


def test_language_falls_back_to_english(store: Path) -> None:
    role = persona_store.list_state("en")["packs"][0]["roles"][0]

    assert role["name"] == "Role"


def test_install_writes_a_claude_subagent_definition(store: Path) -> None:
    result = persona_store.install_role("demo-role", "en")

    assert result["ok"] is True
    text = persona_store.agent_path("demo-role").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert 'name: "Role"' in text
    assert 'description: "Description"' in text
    assert text.rstrip().endswith("Prompt")
    assert persona_store.list_state("en")["packs"][0]["roles"][0]["installed"] is True


def test_install_rejects_an_unknown_role(store: Path) -> None:
    assert persona_store.install_role("nope")["status"] == "missing"


@pytest.mark.parametrize("role_id", ["../escape", "Upper", "with space", "trailing-", ""])
def test_install_rejects_ids_that_could_escape_the_agents_directory(
    store: Path, role_id: str
) -> None:
    # Ids become filenames under ~/.claude/agents, so anything that could climb
    # out of it must be refused before a path is built.
    assert persona_store.install_role(role_id)["ok"] is False


def test_hand_edits_are_reported_as_drift(store: Path) -> None:
    persona_store.install_role("demo-role", "en")
    path = persona_store.agent_path("demo-role")
    path.write_text(path.read_text(encoding="utf-8") + "\nedited by hand\n", encoding="utf-8")

    role = persona_store.list_state("en")["packs"][0]["roles"][0]

    assert role["drifted"] is True


def test_restore_rewrites_the_file_and_clears_drift(store: Path) -> None:
    persona_store.install_role("demo-role", "en")
    path = persona_store.agent_path("demo-role")
    path.write_text("clobbered", encoding="utf-8")

    persona_store.restore_role("demo-role")

    assert "Prompt" in path.read_text(encoding="utf-8")
    assert persona_store.list_state("en")["packs"][0]["roles"][0]["drifted"] is False


def test_ignore_drift_silences_the_warning_without_rewriting(store: Path) -> None:
    persona_store.install_role("demo-role", "en")
    path = persona_store.agent_path("demo-role")
    path.write_text("mine now", encoding="utf-8")

    persona_store.ignore_drift("demo-role")

    assert persona_store.list_state("en")["packs"][0]["roles"][0]["drifted"] is False
    assert path.read_text(encoding="utf-8") == "mine now"


def test_a_foreign_agent_file_is_never_silently_overwritten(store: Path) -> None:
    # The maintainer already had ~/.claude/agents/code-reviewer.md before this
    # feature existed. Overwriting a same-named file we did not create would
    # destroy someone's own agent.
    agents = store / "claude" / "agents"
    agents.mkdir(parents=True)
    foreign = agents / "demo-role.md"
    foreign.write_text("my own agent", encoding="utf-8")

    listing = persona_store.list_state("en")["packs"][0]["roles"][0]
    assert listing["installed"] is False
    assert listing["foreign"] is True

    result = persona_store.install_role("demo-role", "en")

    assert result["ok"] is True
    # The report names the tool, because a role now lands in more than one.
    assert "Claude Code" in result["replaced_backup"]
    backups = list(agents.glob("demo-role.md.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "my own agent"
    assert "Prompt" in foreign.read_text(encoding="utf-8")


def test_uninstall_and_restore_refuse_to_touch_a_foreign_file(store: Path) -> None:
    agents = store / "claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "demo-role.md").write_text("my own agent", encoding="utf-8")

    assert persona_store.uninstall_role("demo-role")["status"] == "foreign"
    assert persona_store.restore_role("demo-role")["status"] == "foreign"
    assert (agents / "demo-role.md").read_text(encoding="utf-8") == "my own agent"


def test_uninstall_removes_our_own_file(store: Path) -> None:
    persona_store.install_role("demo-role", "en")

    assert persona_store.uninstall_role("demo-role")["ok"] is True
    assert not persona_store.agent_path("demo-role").is_file()


def test_a_malformed_pack_is_skipped_not_fatal(store: Path) -> None:
    (store / "personas" / "broken.json").write_text("{not json", encoding="utf-8")

    state = persona_store.list_state("en")

    assert state["ok"] is True
    assert [pack["id"] for pack in state["packs"]] == ["demo"]


def test_list_personas_skips_roles_with_no_prompt(store: Path) -> None:
    pack: dict[str, Any] = json.loads(json.dumps(PACK))
    pack["id"] = "empty"
    pack["roles"][0]["id"] = "no-prompt"
    pack["roles"][0]["system_prompt"] = ""
    (store / "personas" / "empty.json").write_text(json.dumps(pack), encoding="utf-8")

    ids = [persona["id"] for persona in persona_store.list_personas("en")]

    # A seat briefed with an empty prompt is indistinguishable from no persona,
    # so offering it in the picker would be a silent no-op.
    assert "no-prompt" not in ids
    assert "demo-role" in ids


def test_shipped_packs_are_valid() -> None:
    # Guards the real personas/ directory: every id unique and usable as a
    # filename, and both shipped languages present for user-visible fields.
    seen: set[str] = set()
    packs = list(persona_store.PERSONA_DIR.glob("*.json"))
    assert packs, "no persona packs shipped"
    for path in packs:
        pack = json.loads(path.read_text(encoding="utf-8"))
        assert persona_store.ID_RE.match(pack["id"]), pack["id"]
        for role in pack["roles"]:
            assert persona_store.ID_RE.match(role["id"]), role["id"]
            assert role["id"] not in seen, f"duplicate role id: {role['id']}"
            seen.add(role["id"])
            for field in ("name", "persona_name", "description", "system_prompt"):
                value = role[field]
                assert isinstance(value, dict), f"{role['id']}.{field} must be per-language"
                for language in persona_store.SUPPORTED_LANGUAGES:
                    assert value.get(language), f"{role['id']}.{field} missing {language}"


def test_a_role_lands_in_every_tool_the_machine_actually_has(store: Path) -> None:
    """Installing into one tool only means the role silently does not exist in
    the other, which the user reads as the install having failed."""
    result = persona_store.install_role("demo-role", "en")

    assert result["ok"] is True
    assert result["targets"] == ["Claude Code", "Codex"]
    assert (store / "claude" / "agents" / "demo-role.md").is_file()
    assert (store / "codex" / "agents" / "demo-role.toml").is_file()


def test_each_tool_gets_its_own_format_not_a_copy(store: Path) -> None:
    """Codex reads TOML with developer_instructions; Claude reads YAML
    frontmatter. Copying one into the other produces a file neither can load."""
    persona_store.install_role("demo-role", "en")

    claude = (store / "claude" / "agents" / "demo-role.md").read_text(encoding="utf-8")
    codex = (store / "codex" / "agents" / "demo-role.toml").read_text(encoding="utf-8")

    assert claude.startswith("---\n")
    assert 'name: "Role"' in claude
    assert codex.startswith('name = "Role"')
    assert 'developer_instructions = """' in codex
    assert "Prompt" in codex


def test_a_tool_that_is_not_installed_is_left_alone(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tool's own directory existing is the evidence it is used at all."""
    monkeypatch.setattr(persona_store, "CODEX_DIR", store / "no-codex-here")

    result = persona_store.install_role("demo-role", "en")

    assert result["targets"] == ["Claude Code"]
    assert not (store / "no-codex-here").exists()


def test_a_foreign_file_in_one_tool_blocks_uninstalling_from_both(store: Path) -> None:
    """Removing the copies we own and leaving the rest would hand the user a
    half-removed role with no way to tell what happened."""
    persona_store.install_role("demo-role", "en")
    (store / "codex" / "agents" / "demo-role.toml").write_text("hand written", encoding="utf-8")
    state = json.loads((store / "state.json").read_text(encoding="utf-8"))
    del state["roles"]["demo-role"]["digests"]["codex"]
    (store / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert persona_store.uninstall_role("demo-role")["status"] == "foreign"
    assert (store / "claude" / "agents" / "demo-role.md").is_file()


def test_a_hand_edit_in_any_tool_counts_as_drift(store: Path) -> None:
    persona_store.install_role("demo-role", "en")
    codex_file = store / "codex" / "agents" / "demo-role.toml"
    codex_file.write_text(codex_file.read_text(encoding="utf-8") + "\n# mine\n", encoding="utf-8")

    assert persona_store.list_state("en")["packs"][0]["roles"][0]["drifted"] is True


def test_every_shipped_role_renders_as_loadable_toml() -> None:
    """Codex will not read a file it cannot parse, and it fails silently.

    A prompt containing a bare triple quote would close the block early and
    corrupt the rest of the file, so the escaping has to hold for every role
    actually shipped -- not just the fixture.
    """
    import tomllib

    for pack in persona_store._load_packs():
        for role in pack["roles"]:
            for language in persona_store.SUPPORTED_LANGUAGES:
                rendered = persona_store.render_codex_agent_file(role, language)
                parsed = tomllib.loads(rendered)
                assert parsed["name"], f"{role['id']} ({language}) rendered an empty name"
                assert parsed["developer_instructions"].strip(), (
                    f"{role['id']} ({language}) rendered empty instructions"
                )


def test_a_prompt_containing_a_triple_quote_still_parses() -> None:
    import tomllib

    role = {
        "id": "tricky",
        "name": {"en": "Tricky"},
        "description": {"en": "d"},
        "system_prompt": {"en": 'Use """ to open a block, like this.'},
    }

    parsed = tomllib.loads(persona_store.render_codex_agent_file(role, "en"))

    assert "to open a block" in parsed["developer_instructions"]
