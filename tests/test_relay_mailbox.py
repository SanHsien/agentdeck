# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "agentdeck". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Tray notice for agent-relay mail: reads files only, notifies once per message."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import relay_mailbox as relay


@pytest.fixture(autouse=True)
def _isolated_relay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # load_config() honours these overrides, so an operator who exports them would
    # otherwise point every test below at their real mailbox instead of tmp_path.
    for name in ("AGENT_RELAY_HOME", "AGENT_RELAY_STORE", "AGENT_RELAY_AGENT"):
        monkeypatch.delenv(name, raising=False)


class FakeIcon:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def notify(self, body: str, title: str) -> None:
        self.calls.append((body, title))


def _setup(tmp_path: Path, agent: str = "claude-code") -> tuple[Path, Path]:
    home = tmp_path / "relay-home"
    store = tmp_path / "store"
    home.mkdir()
    config = {"store": str(store), "agent": agent}
    (home / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return home, store


def _deliver(
    store: Path, agent: str, env_id: str, subject: str = "s", schema: str = relay.SCHEMA
) -> None:
    box = store / "mailboxes" / agent / "new"
    box.mkdir(parents=True, exist_ok=True)
    env = {"schema": schema, "id": env_id, "from": "commander", "to": agent, "subject": subject}
    (box / f"{env_id}.json").write_text(json.dumps(env), encoding="utf-8")


def test_silent_when_agent_relay_is_not_set_up(tmp_path: Path) -> None:
    icon = FakeIcon()
    assert relay.tick(icon, "en", home=tmp_path / "missing", seen_file=tmp_path / "seen.json") == []
    assert icon.calls == []


def test_notifies_once_per_message(tmp_path: Path) -> None:
    home, store = _setup(tmp_path)
    seen = tmp_path / "seen.json"
    icon = FakeIcon()
    _deliver(store, "claude-code", "20261020T000000000Z-aaaaaa", "first")
    _deliver(store, "claude-code", "20261020T000001000Z-bbbbbb", "second")

    fresh = relay.tick(icon, "en", home=home, seen_file=seen)
    assert [m.subject for m in fresh] == ["first", "second"]
    assert icon.calls == [("commander: second", "New mail for claude-code (2)")]

    assert relay.tick(icon, "en", home=home, seen_file=seen) == []
    assert len(icon.calls) == 1

    _deliver(store, "claude-code", "20261020T000002000Z-cccccc", "third")
    assert [m.subject for m in relay.tick(icon, "en", home=home, seen_file=seen)] == ["third"]


def test_skips_temp_corrupt_and_foreign_files(tmp_path: Path) -> None:
    home, store = _setup(tmp_path)
    box = store / "mailboxes" / "claude-code" / "new"
    box.mkdir(parents=True)
    (box / ".tmp-x.json").write_text("{half", encoding="utf-8")
    (box / "bad.json").write_text("{not json", encoding="utf-8")
    _deliver(store, "claude-code", "other", schema="something-else@1")
    assert relay.new_mail(store, "claude-code") == []


def test_other_mailboxes_are_ignored(tmp_path: Path) -> None:
    home, store = _setup(tmp_path, agent="claude-code")
    _deliver(store, "hermes", "20261020T000000000Z-aaaaaa")
    assert relay.tick(FakeIcon(), "en", home=home, seen_file=tmp_path / "seen.json") == []


def test_env_overrides_match_the_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, _ = _setup(tmp_path, agent="claude-code")
    other = tmp_path / "other-store"
    monkeypatch.setenv("AGENT_RELAY_STORE", str(other))
    monkeypatch.setenv("AGENT_RELAY_AGENT", "hermes")
    assert relay.load_config(home) == (other, "hermes")
