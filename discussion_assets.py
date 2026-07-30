# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""macOS window shell for the PyObjC-free AI council bridge."""

# This module is imported and type-checked on Windows CI too (its non-GUI
# helpers are tested there), but its AppKit/WebKit imports and classes are
# gated behind `if sys.platform == "darwin":`. mypy's platform narrowing
# statically skips that block on a win32 run, so every name it would have
# bound (NSWindow, WKWebView, _DiscussionWindow, ...) looks undefined to
# methods that reference them elsewhere in the file — hence `name-defined`
# joining the existing PyObjC-stub suppressions below.
# mypy: disable-error-code="import-untyped,import-not-found,misc,name-defined"
from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from discussion_session import DebateStyle
from i18n import _load_i18n_bundle, packaged_resource_path
from panels.payload import _data_uri
from usage_lang import detect_lang

ATTACHMENTS_DIR = Path(os.path.expanduser("~/.agentdeck/discussion_attachments"))
ATTACHMENT_MAX_FILES = 50
ATTACHMENT_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
DROP_MAX_BYTES = 20 * 1024 * 1024
THUMBNAIL_MAX_PIXELS = 128


def _attachment_timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def build_attachment_name(stamp: str, index: int, suffix: str) -> str:
    """Pure filename builder so naming is testable without touching disk."""
    return f"{stamp}-{index}{suffix}"


def _next_attachment_path(suffix: str, directory: Path) -> Path:
    stamp = _attachment_timestamp()
    index = 1
    while True:
        candidate = directory / build_attachment_name(stamp, index, suffix)
        if not candidate.exists():
            return candidate
        index += 1


def save_attachment_bytes(
    data: bytes,
    suffix: str,
    directory: Path = ATTACHMENTS_DIR,
) -> Path:
    """Persist raw image bytes under the managed directory and prune old files."""
    directory.mkdir(parents=True, exist_ok=True)
    target = _next_attachment_path(suffix, directory)
    target.write_bytes(data)
    prune_attachments(directory=directory)
    return target


def import_attachment_file(
    src: str,
    directory: Path = ATTACHMENTS_DIR,
) -> Path | None:
    """Copy a user-picked image into the managed directory; None on bad input."""
    path = Path(src)
    if not path.is_file() or path.suffix.lower() not in ATTACHMENT_SUFFIXES:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    target = _next_attachment_path(path.suffix.lower(), directory)
    shutil.copy2(path, target)
    prune_attachments(directory=directory)
    return target


def attachment_thumbnail_data_uri(path: Path) -> str | None:
    """Return a small PNG data URI for a managed image, or None on failure."""
    if sys.platform != "darwin" or not path.is_file():
        return None
    try:
        from AppKit import NSBitmapImageFileTypePNG, NSBitmapImageRep, NSImage, NSMakeSize

        image = NSImage.alloc().initWithContentsOfFile_(str(path))
        if image is None:
            return None
        size = image.size()
        longest = max(float(size.width), float(size.height))
        if longest <= 0:
            return None
        scale = min(1.0, THUMBNAIL_MAX_PIXELS / longest)
        image.setSize_(NSMakeSize(size.width * scale, size.height * scale))
        tiff = image.TIFFRepresentation()
        representation = NSBitmapImageRep.imageRepWithData_(tiff)
        png = representation.representationUsingType_properties_(
            NSBitmapImageFileTypePNG, {}
        )
        if png is None:
            return None
        return "data:image/png;base64," + base64.b64encode(bytes(png)).decode("ascii")
    except Exception:
        return None


def prune_attachments(
    directory: Path = ATTACHMENTS_DIR,
    keep: int = ATTACHMENT_MAX_FILES,
) -> None:
    """Keep only the newest ``keep`` files, deleting the oldest by mtime."""
    if not directory.exists() or keep < 0:
        return
    files = [entry for entry in directory.iterdir() if entry.is_file()]
    if len(files) <= keep:
        return
    files.sort(key=lambda entry: entry.stat().st_mtime)
    for stale in files[: len(files) - keep]:
        with contextlib.suppress(OSError):
            stale.unlink()

SCRIPT_HANDLER_NAME = "usageDiscussion"
WINDOW_AUTOSAVE_NAME = "usage.discussion.window"
BUILTIN_PARTICIPANTS = ("claude", "codex", "agy")
PARTICIPANT_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
    "agy": "Antigravity",
}
ALLOWED_MODELS: dict[str, frozenset[str]] = {
    "claude": frozenset({"opus", "sonnet", "haiku"}),
    "codex": frozenset({"gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.6-sol"}),
    "agy": frozenset({"gemini-3.6-flash-high", "gemini-3.1-pro-high"}),
}
RUNNING_STATUSES = frozenset(
    {"PREPARING", "ROUND1_RUNNING", "ROUND2_RUNNING", "SUMMARIZING", "CANCELLING"}
)

ActionName = Literal[
    "discussion_attach",
    "discussion_clear",
    "discussion_detect",
    "discussion_pick_folder",
    "discussion_clear_folder",
    "discussion_start",
    "discussion_stop",
    "discussion_paste_image",
    "discussion_pick_image",
    "discussion_drop_image",
    "discussion_remove_attachment",
    "discussion_submit_guidance",
]


@dataclass(frozen=True)
class DiscussionAction:
    action: ActionName
    topic: str | None = None
    participants: tuple[str, ...] = ()
    moderator_id: str | None = None
    working_directory: str | None = None
    attachments: tuple[str, ...] = ()
    total_rounds: int = 2
    include_summary: bool = True
    end_on_consensus: bool = False
    guidance_between_rounds: bool = False
    models: Mapping[str, str | None] = field(default_factory=dict)
    personas: Mapping[str, str | None] = field(default_factory=dict)
    debate_style: DebateStyle = DebateStyle.CONSTRUCTIVE
    attachment_path: str | None = None
    attachment_data: str | None = None
    attachment_name: str | None = None
    guidance_text: str | None = None


def parse_discussion_action(raw: object) -> DiscussionAction:
    """Validate one JSON-string action without touching PyObjC or the bridge."""
    if not isinstance(raw, str):
        raise ValueError("action message must be a JSON string")
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("action message is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("action message must contain an object")
    action = payload.get("action")
    if action not in {
        "discussion_attach",
        "discussion_clear",
        "discussion_detect",
        "discussion_pick_folder",
        "discussion_clear_folder",
        "discussion_start",
        "discussion_stop",
        "discussion_paste_image",
        "discussion_pick_image",
        "discussion_drop_image",
        "discussion_remove_attachment",
        "discussion_submit_guidance",
    }:
        raise ValueError("unknown discussion action")
    if action == "discussion_submit_guidance":
        text_value = payload.get("text")
        if not isinstance(text_value, str):
            raise ValueError("discussion_submit_guidance requires a string text")
        return DiscussionAction(
            cast(ActionName, action),
            guidance_text=text_value,
        )
    if action == "discussion_remove_attachment":
        path_value = payload.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError("discussion_remove_attachment requires a string path")
        return DiscussionAction(
            cast(ActionName, action),
            attachment_path=path_value,
        )
    if action == "discussion_drop_image":
        data_value = payload.get("data")
        name_value = payload.get("name")
        if not isinstance(data_value, str) or not data_value.strip():
            raise ValueError("discussion_drop_image requires base64 data")
        if not isinstance(name_value, str) or not name_value.strip():
            raise ValueError("discussion_drop_image requires a filename")
        return DiscussionAction(
            cast(ActionName, action),
            attachment_data=data_value,
            attachment_name=name_value,
        )
    if action != "discussion_start":
        return DiscussionAction(cast(ActionName, action))

    topic = payload.get("topic")
    participant_value = payload.get("participants")
    moderator_value = payload.get("moderatorId")
    working_directory_value = payload.get("workingDir")
    if not isinstance(topic, str):
        raise ValueError("discussion_start requires a string topic")
    if not isinstance(participant_value, list) or not participant_value:
        raise ValueError("discussion_start requires at least one participant")
    if not all(isinstance(item, str) for item in participant_value):
        raise ValueError("discussion_start participants must be strings")
    participants = tuple(cast(list[str], participant_value))
    if len(participants) != len(set(participants)):
        raise ValueError("discussion_start participants must be unique")
    if any(item not in BUILTIN_PARTICIPANTS for item in participants):
        raise ValueError("discussion_start contains an unknown participant")
    if moderator_value is not None and not isinstance(moderator_value, str):
        raise ValueError("discussion_start moderatorId must be a string or null")
    if working_directory_value is not None and not isinstance(
        working_directory_value, str
    ):
        raise ValueError("discussion_start workingDir must be a string or null")
    attachments_value = payload.get("attachments")
    rounds_value = payload.get("totalRounds", 2)
    include_summary_value = payload.get("includeSummary", True)
    end_on_consensus_value = payload.get("endOnConsensus", False)
    guidance_between_rounds_value = payload.get("guidanceBetweenRounds", False)
    debate_style_value = payload.get("debateStyle", DebateStyle.CONSTRUCTIVE.value)
    if not isinstance(rounds_value, int) or isinstance(rounds_value, bool):
        raise ValueError("discussion_start totalRounds must be an integer")
    if not isinstance(include_summary_value, bool):
        raise ValueError("discussion_start includeSummary must be a boolean")
    if not isinstance(end_on_consensus_value, bool):
        raise ValueError("discussion_start endOnConsensus must be a boolean")
    if not isinstance(guidance_between_rounds_value, bool):
        raise ValueError("discussion_start guidanceBetweenRounds must be a boolean")
    if not isinstance(debate_style_value, str):
        raise ValueError("discussion_start debateStyle must be a string")
    try:
        debate_style = DebateStyle(debate_style_value)
    except ValueError as exc:
        raise ValueError("discussion_start has an unknown debateStyle") from exc
    if attachments_value is not None:
        if not isinstance(attachments_value, list) or not all(
            isinstance(item, str) for item in attachments_value
        ):
            raise ValueError("discussion_start attachments must be a list of strings")
        attachments = tuple(cast(list[str], attachments_value))
    else:
        attachments = ()
    moderator_id = moderator_value
    if moderator_id is not None and moderator_id not in participants:
        raise ValueError("discussion_start moderatorId must be selected")
    models = _parse_discussion_models(payload.get("models"))
    personas = _parse_discussion_personas(payload.get("personas"))
    return DiscussionAction(
        cast(ActionName, action),
        topic=topic,
        participants=participants,
        moderator_id=moderator_id,
        working_directory=working_directory_value or None,
        attachments=attachments,
        total_rounds=min(5, max(1, rounds_value)),
        include_summary=include_summary_value,
        end_on_consensus=end_on_consensus_value,
        guidance_between_rounds=guidance_between_rounds_value,
        models=models,
        personas=personas,
        debate_style=debate_style,
    )


def _parse_discussion_models(raw: object) -> dict[str, str | None]:
    """Validate the optional per-participant model map; absent means all default."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("discussion_start models must be an object")
    models: dict[str, str | None] = {}
    for key, value in raw.items():
        if key not in BUILTIN_PARTICIPANTS:
            raise ValueError("discussion_start models has an unknown participant")
        if value is None or value == "":
            models[key] = None
        elif isinstance(value, str):
            if value not in ALLOWED_MODELS[key]:
                raise ValueError("discussion_start models has an unknown model")
            models[key] = value
        else:
            raise ValueError("discussion_start models values must be strings or null")
    return models


def _parse_discussion_personas(raw: object) -> dict[str, str | None]:
    """Validate the optional per-participant persona map; absent means neutral."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("discussion_start personas must be an object")
    personas: dict[str, str | None] = {}
    for key, value in raw.items():
        if key not in BUILTIN_PARTICIPANTS:
            raise ValueError("discussion_start personas has an unknown participant")
        if value is None or value == "":
            personas[key] = None
        elif isinstance(value, str):
            personas[key] = value
        else:
            raise ValueError("discussion_start personas values must be strings or null")
    return personas


def estimate_cli_calls(
    participant_count: int,
    total_rounds: int = 2,
    include_summary: bool = True,
) -> int:
    """Return the maximum calls shown before a discussion starts."""
    if participant_count <= 0:
        return 0
    return participant_count * min(5, max(1, total_rounds)) + int(include_summary)


def serialize_javascript_call(function_name: str, payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"window.{function_name}({encoded})"


def serialize_event_batch(
    events: Sequence[Mapping[str, object]],
    snapshot: Mapping[str, object],
) -> str:
    """Add snapshot-only turn metadata before sending one JavaScript batch."""
    turn_streaming: dict[str, bool] = {}
    turns = snapshot.get("turns")
    if isinstance(turns, list):
        for item in turns:
            if not isinstance(item, dict):
                continue
            turn_id = item.get("id")
            supports_stream = item.get("supports_token_stream")
            if isinstance(turn_id, str) and isinstance(supports_stream, bool):
                turn_streaming[turn_id] = supports_stream

    enriched: list[dict[str, object]] = []
    for source_event in events:
        event = dict(source_event)
        turn_id = event.get("turn_id")
        payload_value = event.get("payload")
        payload = dict(payload_value) if isinstance(payload_value, dict) else {}
        if isinstance(turn_id, str) and turn_id in turn_streaming:
            payload["supports_token_stream"] = turn_streaming[turn_id]
        event["payload"] = payload
        enriched.append(event)
    return serialize_javascript_call("discussionApplyEvents", enriched)


def _load_discussion_html(language: str | None = None) -> str:
    path = packaged_resource_path(
        "windows/discussion.html",
        Path(__file__).with_name("assets") / "windows" / "discussion.html",
    )
    html = path.read_text(encoding="utf-8")
    return (
        html.replace("{{CLAUDE_ICON}}", _data_uri("claude.webp"))
        .replace("{{CODEX_ICON}}", _data_uri("codex.webp"))
        .replace(
            "{{I18N_BUNDLE}}",
            json.dumps(_load_i18n_bundle(), ensure_ascii=False),
        )
        .replace(
            "{{INITIAL_LANGUAGE}}",
            json.dumps(language or detect_lang()),
        )
    )


