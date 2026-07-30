# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Open replacement for the closed ``instate-cli`` that fed the AI Talent Market.

Upstream's talent market shells out to ``vendor/instate-cli``, a binary built
from a private project on the author's machine. Its source repo and its
distribution repo are both 404 to anyone else, and the artifact is a macOS
executable, so nobody who clones the public repository can use the feature — not
even on macOS. Removing the panel was one option; reimplementing the backend in
the open was the better one, because the panel UI and the bridge are already here
and AGPL-licensed. Only the data and the install logic were missing.

This module supplies both:

* role definitions live in ``personas/*.json`` in this repository, so they are
  auditable and editable rather than compiled into an opaque binary;
* installing a role writes a Claude Code subagent definition into
  ``~/.claude/agents/<role-id>.md``.

It deliberately mirrors the shapes ``talent_market_bridge`` already returned, so
the existing panel and the AI Council persona picker need no changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from i18n import packaged_resource_path

PERSONA_DIR = packaged_resource_path("personas", Path(__file__).with_name("personas"))
AGENTS_DIR = Path(os.path.expanduser("~/.claude/agents"))
STATE_FILE = Path(os.path.expanduser("~/.agentdeck/persona_state.json"))

# Role and pack ids become filenames under ~/.claude/agents, so they may not
# contain anything that could escape that directory or collide after
# normalisation on a case-insensitive filesystem.
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SUPPORTED_LANGUAGES = ("zh-TW", "en")


class PersonaError(Exception):
    """A pack file is malformed. Raised only while loading, never per-role."""


def _text(value: Any, language: str) -> str:
    """Resolve a field that may be a plain string or a per-language mapping."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for candidate in (language, "en", *SUPPORTED_LANGUAGES):
            text = value.get(candidate)
            if isinstance(text, str) and text.strip():
                return text
    return ""


def _text_list(value: Any, language: str) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, dict):
        for candidate in (language, "en", *SUPPORTED_LANGUAGES):
            items = value.get(candidate)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, str)]
    return []


def _load_packs() -> list[dict[str, Any]]:
    """Read every pack file. A malformed pack is skipped, not fatal."""
    if not PERSONA_DIR.is_dir():
        return []
    packs: list[dict[str, Any]] = []
    for path in sorted(PERSONA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            packs.append(data)
    return packs


def agent_path(role_id: str) -> Path:
    return AGENTS_DIR / f"{role_id}.md"


def render_agent_file(role: dict[str, Any], language: str) -> str:
    """Render a role as a Claude Code subagent definition.

    The frontmatter keys are the ones Claude Code reads; the body is the system
    prompt. Values are quoted because a description containing a colon would
    otherwise produce invalid YAML.
    """
    name = _text(role.get("name"), language) or role["id"]
    description = _text(role.get("description"), language)
    prompt = _text(role.get("system_prompt"), language)
    escaped_name = name.replace('"', '\\"')
    escaped_description = description.replace('"', '\\"')
    return (
        "---\n"
        f'name: "{escaped_name}"\n'
        f'description: "{escaped_description}"\n'
        "---\n\n"
        f"{prompt.strip()}\n"
    )


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_state() -> dict[str, Any]:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def _role_state(state: dict[str, Any], role_id: str) -> dict[str, Any]:
    roles = state.get("roles")
    if isinstance(roles, dict):
        entry = roles.get(role_id)
        if isinstance(entry, dict):
            return entry
    return {}


def is_ours(role_id: str, state: dict[str, Any]) -> bool:
    """Whether we are the ones who wrote the installed agent file.

    A user may already have an agent of the same name — `code-reviewer` is a
    likely collision, and one that really happened on the maintainer's machine
    during development. Treating a stranger's file as "installed" would let a
    later install or restore silently overwrite work we never created.
    """
    return isinstance(_role_state(state, role_id).get("digest"), str)


def _is_drifted(role_id: str, state: dict[str, Any]) -> bool:
    """True when the installed file no longer matches what we wrote.

    Drift is what the user edited by hand. Reporting it lets the panel offer a
    restore instead of silently overwriting someone's changes on the next
    install — which is the behaviour that would actually lose work.
    """
    entry = _role_state(state, role_id)
    installed_digest = entry.get("digest")
    if not isinstance(installed_digest, str):
        return False
    if entry.get("ignore_drift") is True:
        return False
    try:
        current = agent_path(role_id).read_text(encoding="utf-8")
    except OSError:
        return False
    return _digest(current) != installed_digest


def list_state(lang: str | None = None) -> dict[str, Any]:
    """Return the panel payload, in the same shape the CLI produced."""
    language = lang if lang in SUPPORTED_LANGUAGES else "en"
    state = _load_state()
    packs_out: list[dict[str, Any]] = []
    for pack in _load_packs():
        roles_out: list[dict[str, Any]] = []
        raw_roles = pack.get("roles")
        if not isinstance(raw_roles, list):
            continue
        for role in raw_roles:
            if not isinstance(role, dict):
                continue
            role_id = role.get("id")
            if not isinstance(role_id, str) or not ID_RE.match(role_id):
                continue
            entry = _role_state(state, role_id)
            folder = entry.get("folder")
            roles_out.append(
                {
                    "id": role_id,
                    "name": _text(role.get("name"), language),
                    "personaName": _text(role.get("persona_name"), language),
                    "description": _text(role.get("description"), language),
                    "systemPrompt": _text(role.get("system_prompt"), language),
                    "icon": role.get("icon") if isinstance(role.get("icon"), str) else "",
                    # "installed" means installed *by us*. A same-named file we
                    # did not write is reported as foreign instead, so the panel
                    # never offers a restore that would overwrite it.
                    "installed": agent_path(role_id).is_file() and is_ours(role_id, state),
                    "foreign": agent_path(role_id).is_file() and not is_ours(role_id, state),
                    "drifted": _is_drifted(role_id, state),
                    "quickTasks": _text_list(role.get("quick_tasks"), language),
                    "selectedFolderLabel": folder if isinstance(folder, str) else "",
                }
            )
        if not roles_out:
            continue
        installed = sum(1 for role in roles_out if role["installed"])
        packs_out.append(
            {
                "id": pack["id"],
                "name": _text(pack.get("name"), language),
                "subtitle": _text(pack.get("subtitle"), language),
                "icon": pack.get("icon") if isinstance(pack.get("icon"), str) else "",
                "countLabel": f"{installed}/{len(roles_out)}",
                "roles": roles_out,
            }
        )
    return {"ok": True, "status": "ok", "language": language, "packs": packs_out}


def _find_role(role_id: str) -> dict[str, Any] | None:
    for pack in _load_packs():
        roles = pack.get("roles")
        if not isinstance(roles, list):
            continue
        for role in roles:
            if isinstance(role, dict) and role.get("id") == role_id:
                return role
    return None


def install_role(role_id: str, lang: str | None = None) -> dict[str, Any]:
    if not ID_RE.match(role_id):
        return {"ok": False, "status": "error", "error": f"invalid role id: {role_id}"}
    role = _find_role(role_id)
    if role is None:
        return {"ok": False, "status": "missing", "error": f"unknown role: {role_id}"}
    language = lang if lang in SUPPORTED_LANGUAGES else "en"
    content = render_agent_file(role, language)
    state = _load_state()
    path = agent_path(role_id)
    backup: str | None = None
    try:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        if path.is_file() and not is_ours(role_id, state):
            # Someone else's agent under the same name. Never clobber it —
            # move it aside and report where it went, so it can be put back.
            existing = path.read_text(encoding="utf-8")
            target = path.with_name(f"{role_id}.md.bak-{_digest(existing)[:8]}")
            target.write_text(existing, encoding="utf-8", newline="\n")
            backup = target.name
        path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as exc:
        return {"ok": False, "status": "error", "error": str(exc)}
    roles = state.setdefault("roles", {})
    if isinstance(roles, dict):
        entry = roles.setdefault(role_id, {})
        if isinstance(entry, dict):
            entry["digest"] = _digest(content)
            entry["language"] = language
            entry.pop("ignore_drift", None)
    _save_state(state)
    result: dict[str, Any] = {"ok": True, "status": "installed", "role": role_id}
    if backup is not None:
        result["replaced_backup"] = backup
    return result


def uninstall_role(role_id: str) -> dict[str, Any]:
    if not ID_RE.match(role_id):
        return {"ok": False, "status": "error", "error": f"invalid role id: {role_id}"}
    path = agent_path(role_id)
    if path.is_file() and not is_ours(role_id, _load_state()):
        # We did not create this file, so we have no basis for deleting it.
        return {"ok": False, "status": "foreign", "error": f"not installed by usage: {role_id}"}
    try:
        if path.is_file():
            path.unlink()
    except OSError as exc:
        return {"ok": False, "status": "error", "error": str(exc)}
    state = _load_state()
    roles = state.get("roles")
    if isinstance(roles, dict):
        roles.pop(role_id, None)
        _save_state(state)
    return {"ok": True, "status": "uninstalled", "role": role_id}


def restore_role(role_id: str) -> dict[str, Any]:
    """Rewrite the installed file from the pack, discarding hand edits."""
    state = _load_state()
    if agent_path(role_id).is_file() and not is_ours(role_id, state):
        return {"ok": False, "status": "foreign", "error": f"not installed by usage: {role_id}"}
    entry = _role_state(state, role_id)
    language = entry.get("language")
    return install_role(role_id, language if isinstance(language, str) else None)


def ignore_drift(role_id: str) -> dict[str, Any]:
    if _find_role(role_id) is None:
        return {"ok": False, "status": "missing", "error": f"unknown role: {role_id}"}
    state = _load_state()
    roles = state.setdefault("roles", {})
    if isinstance(roles, dict):
        entry = roles.setdefault(role_id, {})
        if isinstance(entry, dict):
            entry["ignore_drift"] = True
    _save_state(state)
    return {"ok": True, "status": "ignored", "role": role_id}


def set_folder(role_id: str, path: str) -> dict[str, Any]:
    if _find_role(role_id) is None:
        return {"ok": False, "status": "missing", "error": f"unknown role: {role_id}"}
    state = _load_state()
    roles = state.setdefault("roles", {})
    if isinstance(roles, dict):
        entry = roles.setdefault(role_id, {})
        if isinstance(entry, dict):
            if path:
                entry["folder"] = path
            else:
                entry.pop("folder", None)
    _save_state(state)
    return {"ok": True, "status": "ok", "role": role_id, "folder": path}


def list_personas(lang: str | None = None) -> list[dict[str, str]]:
    """Flat role records for the AI Council persona picker."""
    state = list_state(lang)
    personas: list[dict[str, str]] = []
    packs = state.get("packs")
    if not isinstance(packs, list):
        return personas
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        for role in pack.get("roles", []):
            if not isinstance(role, dict):
                continue
            if not role.get("systemPrompt"):
                # A role with no prompt cannot brief a participant, so offering
                # it in the picker would produce a silently unchanged seat.
                continue
            personas.append(
                {
                    "id": str(role["id"]),
                    "name": str(role.get("name") or role["id"]),
                    "persona_name": str(role.get("personaName") or ""),
                    "description": str(role.get("description") or ""),
                    "system_prompt": str(role["systemPrompt"]),
                    "pack_id": str(pack.get("id") or ""),
                    "pack_name": str(pack.get("name") or ""),
                }
            )
    return personas
