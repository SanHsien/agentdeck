# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Tray notice for new agent-relay mail.

agent-relay (https://github.com/SanHsien/agent-relay) is a file + git mailbox the
coding agents use to pass work to each other. Its own scheduled task pulls the
store and rings doorbells; this module only adds a tray notice while agentdeck is
running, reading the mailbox files directly per the agent-relay SPEC (no import,
no network, no git). Nothing happens unless ~/.agent-relay/config.json exists.

Layout read here:  <store>/mailboxes/<agent>/new/<id>.json
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from i18n import _t

logger = logging.getLogger(__name__)

SCHEMA = "agent-relay/envelope@1"
KEEP_SEEN = 500


@dataclass(frozen=True)
class Mail:
    id: str
    sender: str
    subject: str


def relay_home() -> Path:
    return Path(os.environ.get("AGENT_RELAY_HOME") or Path.home() / ".agent-relay")


def seen_path() -> Path:
    return Path(os.path.expanduser("~/.agentdeck/relay-seen.json"))


def load_config(home: Path) -> tuple[Path, str] | None:
    """Return (store, agent) or None when agent-relay is not set up on this machine."""
    try:
        cfg = json.loads((home / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    store, agent = cfg.get("store"), cfg.get("agent")
    if not isinstance(store, str) or not isinstance(agent, str) or not agent:
        return None
    return Path(store), agent


def new_mail(store: Path, agent: str) -> list[Mail]:
    """Unread envelopes in the agent's new/ folder, oldest first. Bad files are skipped."""
    folder = store / "mailboxes" / agent / "new"
    if not folder.is_dir():
        return []
    found: list[Mail] = []
    for path in folder.glob("*.json"):
        if path.name.startswith("."):
            continue
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(env, dict) or env.get("schema") != SCHEMA:
            continue
        found.append(
            Mail(
                str(env.get("id", path.stem)),
                str(env.get("from", "?")),
                str(env.get("subject", "")),
            )
        )
    found.sort(key=lambda mail: mail.id)
    return found


def unseen(mails: list[Mail], seen: list[str]) -> list[Mail]:
    known = set(seen)
    return [mail for mail in mails if mail.id not in known]


def _load_seen(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(item) for item in data] if isinstance(data, list) else []


def _save_seen(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ids[-KEEP_SEEN:]), encoding="utf-8")


def tick(
    icon: object,
    language: str,
    home: Path | None = None,
    seen_file: Path | None = None,
) -> list[Mail]:
    """Notify once per new message. Called on every tray refresh, so it stays local and cheap."""
    setup = load_config(home or relay_home())
    if setup is None:
        return []
    store, agent = setup
    seen_file = seen_file or seen_path()
    seen = _load_seen(seen_file)
    fresh = unseen(new_mail(store, agent), seen)
    if not fresh:
        return []
    notify = getattr(icon, "notify", None)
    if callable(notify):
        latest = fresh[-1]
        with contextlib.suppress(Exception):
            notify(
                _t(language, "relay_mail_body", sender=latest.sender, subject=latest.subject),
                _t(language, "relay_mail_title", agent=agent, count=len(fresh)),
            )
    try:
        _save_seen(seen_file, seen + [mail.id for mail in fresh])
    except OSError:
        logger.warning("could not record seen relay mail", exc_info=True)
    return fresh
