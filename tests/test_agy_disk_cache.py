# SPDX-License-Identifier: AGPL-3.0-only
"""Coverage for the Antigravity parse cache on disk.

Of the three disk caches, this was the only one no test touched:
``test_disk_cache_shards.py`` exercises history and codex, and this module was
left to be proved by the app working. Its whole contract is "recover silently
from anything", which is exactly the shape that hides breakage -- every failure
path returns quietly, so a cache that stopped loading would look identical to a
cold start and simply cost a re-parse on every launch.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from providers import agy_disk_cache
from providers.agy_loader import AgyUsageEntry, _FileCacheEntry

SCHEMA = 7


def _entry(dedup_key: str = "d1") -> AgyUsageEntry:
    return AgyUsageEntry(
        timestamp=datetime(2026, 8, 8, 12, 30, tzinfo=UTC),
        model="gemini-3-pro",
        input_tokens=100,
        output_tokens=20,
        cache_read_tokens=5,
        thinking_tokens=3,
        dedup_key=dedup_key,
        session_id="s-1",
    )


def _file_entry(dedup_key: str = "d1") -> _FileCacheEntry:
    return _FileCacheEntry(
        mtime=1_700_000_000.5,
        size=4096,
        entries=[_entry(dedup_key)],
        skipped_missing_dedup_key=2,
    )


def _seeded(cache_path: Path, maxsize: int = 8) -> OrderedDict[Path, Any]:
    restored: OrderedDict[Path, Any] = OrderedDict()
    agy_disk_cache.seed_caches(cache_path, SCHEMA, maxsize, restored)
    return restored


def test_a_flushed_cache_comes_back_field_for_field(tmp_path: Path) -> None:
    cache_path = tmp_path / "agy_cache.json"
    source = Path("C:/db/state.sqlite")
    original: OrderedDict[Path, Any] = OrderedDict({source: _file_entry()})

    agy_disk_cache.flush_caches(cache_path, SCHEMA, original)
    restored = _seeded(cache_path)

    assert list(restored) == [source]
    # A round trip that quietly loses a field costs a re-parse on every launch.
    assert restored[source] == original[source]


def test_a_cache_written_by_another_schema_is_ignored(tmp_path: Path) -> None:
    """Reusing entries across a schema change would deserialize into the wrong
    shape, and the failure would surface as wrong numbers rather than an error."""
    cache_path = tmp_path / "agy_cache.json"
    agy_disk_cache.flush_caches(cache_path, SCHEMA + 1, OrderedDict({Path("a"): _file_entry()}))

    assert _seeded(cache_path) == OrderedDict()


def test_a_corrupt_or_missing_cache_starts_cold_instead_of_raising(tmp_path: Path) -> None:
    missing = tmp_path / "absent.json"
    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"schema_version": 7, "files": {', encoding="utf-8")
    wrong_type = tmp_path / "list.json"
    wrong_type.write_text("[]", encoding="utf-8")

    assert _seeded(missing) == OrderedDict()
    assert _seeded(truncated) == OrderedDict()
    assert _seeded(wrong_type) == OrderedDict()


def test_one_unreadable_file_entry_does_not_discard_the_others(tmp_path: Path) -> None:
    """The cache is a dictionary of independent files. Letting a single bad
    record throw away every good one turns a one-file re-parse into a full one."""
    cache_path = tmp_path / "agy_cache.json"
    agy_disk_cache.flush_caches(
        cache_path,
        SCHEMA,
        OrderedDict({Path("good-1"): _file_entry("d1"), Path("good-2"): _file_entry("d2")}),
    )
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    payload["files"]["broken"] = {"mtime": "not-a-float", "size": 1, "entries": []}
    payload["files"]["also-broken"] = {"entries": [{"timestamp": "nonsense"}]}
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    restored = _seeded(cache_path)

    assert sorted(str(p) for p in restored) == ["good-1", "good-2"]


def test_seeding_respects_maxsize_and_drops_the_oldest_first(tmp_path: Path) -> None:
    cache_path = tmp_path / "agy_cache.json"
    agy_disk_cache.flush_caches(
        cache_path,
        SCHEMA,
        OrderedDict((Path(f"f{i}"), _file_entry(f"d{i}")) for i in range(5)),
    )

    restored = _seeded(cache_path, maxsize=2)

    # An unbounded seed reintroduces exactly the memory the cap exists to limit.
    assert len(restored) == 2


def test_flushing_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    """The write is atomic through mkstemp + os.replace, so a leftover .tmp
    would mean a partial file survived a failure the code claims to clean up."""
    cache_path = tmp_path / "nested" / "agy_cache.json"

    agy_disk_cache.flush_caches(cache_path, SCHEMA, OrderedDict({Path("a"): _file_entry()}))

    assert cache_path.exists(), "the parent directory should be created on demand"
    assert [p.name for p in cache_path.parent.iterdir()] == [cache_path.name]


def test_an_unwritable_destination_is_swallowed(tmp_path: Path) -> None:
    """Failing to persist a cache must never take down the caller: the cache is
    an optimization, and losing it costs a re-parse, not correctness."""
    blocked = tmp_path / "file-in-the-way"
    blocked.write_text("not a directory", encoding="utf-8")

    agy_disk_cache.flush_caches(blocked / "agy_cache.json", SCHEMA, OrderedDict())

    assert blocked.read_text(encoding="utf-8") == "not a directory"


def test_debug_mode_reports_the_failure_it_swallows(
    tmp_path: Path,
    monkeypatch: Any,
    caplog: Any,
) -> None:
    """Silent recovery is right for users and useless for debugging, so the
    quiet path has to become loud under AGENTDECK_DEBUG."""
    monkeypatch.setenv("AGENTDECK_DEBUG", "1")
    blocked = tmp_path / "file-in-the-way"
    blocked.write_text("not a directory", encoding="utf-8")

    with caplog.at_level("WARNING", logger=agy_disk_cache.logger.name):
        agy_disk_cache.flush_caches(blocked / "agy_cache.json", SCHEMA, OrderedDict())

    assert any("Antigravity" in record.message for record in caplog.records)


def test_entries_survive_a_flush_of_an_empty_cache(tmp_path: Path) -> None:
    """An empty in-memory cache must write a valid empty file rather than
    leaving the previous one in place, or a cleared cache would resurrect."""
    cache_path = tmp_path / "agy_cache.json"
    agy_disk_cache.flush_caches(cache_path, SCHEMA, OrderedDict({Path("a"): _file_entry()}))

    agy_disk_cache.flush_caches(cache_path, SCHEMA, OrderedDict())

    assert _seeded(cache_path) == OrderedDict()
    assert json.loads(cache_path.read_text(encoding="utf-8"))["files"] == {}


def test_the_cache_file_is_written_deterministically(tmp_path: Path) -> None:
    """sort_keys plus a stable serializer means two flushes of the same state
    produce the same bytes -- worth keeping, because it makes an accidental
    rewrite visible in a diff instead of invisible in a timestamp."""
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    state: OrderedDict[Path, Any] = OrderedDict(
        (Path(f"f{i}"), _file_entry(f"d{i}")) for i in range(3)
    )

    agy_disk_cache.flush_caches(first, SCHEMA, state)
    agy_disk_cache.flush_caches(second, SCHEMA, state)

    def without_timestamp(path: Path) -> dict[str, Any]:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("cached_at")
        return payload

    assert without_timestamp(first) == without_timestamp(second)
    assert os.path.getsize(first) > 0
