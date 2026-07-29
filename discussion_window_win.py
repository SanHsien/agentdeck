# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Windows host for the AI Council window.

``discussion_window.py`` keeps the whole feature's logic — action parsing,
attachment handling, event serialization, HTML loading — platform-neutral, and
wraps it in an NSWindow + WKWebView shell. This module supplies the Windows
shell instead: a second pywebview window on the GUI loop ``wintray`` already
starts, with the same JS contract on both sides.

Only four things actually differ from the macOS host:

* the window is created through ``webview.create_window`` rather than NSWindow;
* JS reaches Python through pywebview's ``js_api`` rather than a
  ``WKScriptMessageHandler``;
* clipboard images come from Pillow's ``ImageGrab`` rather than NSPasteboard;
* folder and file pickers come from pywebview rather than ``NSOpenPanel``.

Everything else is imported from ``discussion_window`` so the two hosts cannot
drift apart.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from discussion_bridge import DiscussionBridge, ParticipantSpec
from discussion_cli import DetectionResult
from discussion_window import (
    ATTACHMENT_SUFFIXES,
    DROP_MAX_BYTES,
    PARTICIPANT_LABELS,
    _load_discussion_html,
    attachment_thumbnail_data_uri,
    import_attachment_file,
    parse_discussion_action,
    save_attachment_bytes,
    serialize_event_batch,
)
from i18n import _t
from talent_market_bridge import list_personas
from usage_lang import detect_lang

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 640
# The macOS host drains at most 50 events per pass so a burst cannot monopolise
# the main thread; keep the same ceiling here for identical pacing.
EVENT_DRAIN_LIMIT = 50


def read_clipboard_image() -> tuple[bytes, str] | None:
    """Return ``(png_bytes, ".png")`` for a bitmap on the clipboard, else ``None``.

    Pillow is already a Windows dependency (pystray needs it), and
    ``ImageGrab.grabclipboard`` covers the case that matters: a screenshot or a
    copied image region. It returns a list of paths when files were copied in
    Explorer instead — that is a file paste, not an image paste, so it is
    rejected here and handled by the file picker path.
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        return None
    try:
        grabbed = ImageGrab.grabclipboard()
    except (OSError, ValueError, NotImplementedError):
        return None
    if grabbed is None or isinstance(grabbed, list):
        return None
    buffer = io.BytesIO()
    try:
        grabbed.convert("RGBA").save(buffer, format="PNG")
    except (OSError, ValueError):
        return None
    return buffer.getvalue(), ".png"


class _DiscussionJSApi:
    """The ``usageDiscussion`` bridge the council HTML calls into."""

    def __init__(self, controller: WindowsDiscussionWindowController) -> None:
        self._controller = controller

    def post(self, raw: object) -> None:
        self._controller.receive_action(raw)


class WindowsDiscussionWindowController:
    """Own the standalone pywebview window and forward bridge state to it."""

    def __init__(self, bridge: DiscussionBridge | None = None) -> None:
        self.bridge = bridge or DiscussionBridge()
        self.window: Any | None = None
        self._attached = False
        self._web_ready = False
        self._shutdown = False
        self._drain_scheduled = False
        self._drain_lock = threading.Lock()
        self._language = detect_lang()
        snapshot = self.bridge.snapshot()
        working_directory = snapshot.get("working_directory")
        self._working_directory = (
            working_directory if isinstance(working_directory, str) else None
        )
        self._attachments: list[dict[str, str]] = []
        self._personas: list[dict[str, str]] = []

    # ---- lifecycle -----------------------------------------------------

    def show(self, close_popover: Any = None) -> None:
        if self._shutdown:
            raise RuntimeError("discussion window controller is shut down")
        if close_popover is not None:
            close_popover()
        if self.window is None:
            self._create_window()
        window = self.window
        assert window is not None
        self._attach()
        with contextlib.suppress(Exception):
            window.show()
        if self._web_ready:
            self._apply_full_state()
        self._schedule_drain()

    def close(self) -> None:
        if self.window is not None:
            with contextlib.suppress(Exception):
                self.window.hide()

    def shutdown(self, timeout_seconds: float = 5.0) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._detach()
        self.bridge.shutdown(timeout_seconds)
        if self.window is not None:
            with contextlib.suppress(Exception):
                self.window.destroy()
        self.window = None
        self._web_ready = False

    def _create_window(self) -> None:
        import webview

        window = webview.create_window(
            _t(self._language, "discussion_window_title"),
            html=_load_discussion_html(self._language),
            js_api=_DiscussionJSApi(self),
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            resizable=True,
        )
        if window is None:
            raise RuntimeError("pywebview did not create the discussion window")
        window.events.loaded += self._on_loaded
        self.window = window

    # ---- bridge plumbing ------------------------------------------------

    def _attach(self) -> None:
        self._attached = True
        self.bridge.set_event_listener(self._bridge_events_ready)

    def _detach(self) -> None:
        self._attached = False
        self.bridge.set_event_listener(None)
        with self._drain_lock:
            self._drain_scheduled = False

    def _bridge_events_ready(self) -> None:
        if not self._attached or self._shutdown:
            return
        self._schedule_drain()

    def _schedule_drain(self) -> None:
        """Drain on a worker thread.

        The macOS host has to hop onto the AppKit main thread before touching
        the web view. pywebview marshals ``evaluate_js`` itself — ``wintray``
        already calls it straight from its polling thread — so the only thing
        left to guard is running one drain at a time.
        """
        if not self._attached or not self._web_ready or self.window is None:
            return
        with self._drain_lock:
            if self._drain_scheduled:
                return
            self._drain_scheduled = True
        threading.Thread(target=self._drain_events, name="usage-council-drain", daemon=True).start()

    def _drain_events(self) -> None:
        with self._drain_lock:
            self._drain_scheduled = False
        if not self._attached or not self._web_ready or self.window is None:
            return
        events = self.bridge.drain_events(EVENT_DRAIN_LIMIT)
        if events:
            script = serialize_event_batch(events, self.bridge.snapshot())
            self._run_script(script)
        if len(events) == EVENT_DRAIN_LIMIT:
            self._schedule_drain()

    def _on_loaded(self) -> None:
        if self._shutdown or self.window is None:
            return
        self._web_ready = True
        if self._attached:
            self._apply_full_state()
            self._schedule_drain()

    # ---- actions from the web view --------------------------------------

    def receive_action(self, raw: object) -> None:
        try:
            action = parse_discussion_action(raw)
            if action.action == "discussion_attach":
                self._apply_full_state()
            elif action.action == "discussion_detect":
                self._apply_detection()
            elif action.action == "discussion_pick_folder":
                selected = self._pick_folder()
                if selected is not None:
                    self._working_directory = selected
                    self._apply_working_directory()
            elif action.action == "discussion_clear_folder":
                self._working_directory = None
                self._apply_working_directory()
            elif action.action == "discussion_paste_image":
                self._handle_paste_image()
            elif action.action == "discussion_drop_image":
                assert action.attachment_data is not None
                assert action.attachment_name is not None
                self._handle_drop_image(action.attachment_data, action.attachment_name)
            elif action.action == "discussion_pick_image":
                self._handle_pick_image()
            elif action.action == "discussion_remove_attachment":
                assert action.attachment_path is not None
                self._remove_attachment(action.attachment_path)
            elif action.action == "discussion_stop":
                self.bridge.stop()
                self._apply_snapshot()
            elif action.action == "discussion_submit_guidance":
                assert action.guidance_text is not None
                self.bridge.submit_guidance(action.guidance_text)
            elif action.action == "discussion_clear":
                result = self.bridge.clear()
                if result.get("status") == "busy":
                    self._evaluate(
                        "discussionApplyError",
                        _t(self._language, "discussion_clear_busy"),
                    )
                else:
                    self._apply_snapshot()
            else:
                self._start_discussion(action)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, never swallowed
            logger.debug("discussion action failed", exc_info=True)
            self._evaluate("discussionApplyError", str(exc))

    def _start_discussion(self, action: Any) -> None:
        assert action.topic is not None
        personas_by_id = {persona["id"]: persona for persona in self._personas}
        specs: list[ParticipantSpec] = []
        for participant_id in action.participants:
            persona_id = action.personas.get(participant_id)
            persona = personas_by_id.get(persona_id) if persona_id is not None else None
            specs.append(
                ParticipantSpec(
                    id=participant_id,
                    label=PARTICIPANT_LABELS[participant_id],
                    adapter_id=participant_id,
                    model=action.models.get(participant_id),
                    persona_prompt=(persona["system_prompt"] if persona else None),
                    persona_label=persona["name"] if persona else None,
                )
            )
        self.bridge.start(
            action.topic,
            specs,
            action.moderator_id,
            working_directory=action.working_directory,
            attachments=action.attachments,
            total_rounds=action.total_rounds,
            include_summary=action.include_summary,
            end_on_consensus=action.end_on_consensus,
            guidance_between_rounds=action.guidance_between_rounds,
            debate_style=action.debate_style,
        )
        snapshot = self.bridge.snapshot()
        working_directory = snapshot.get("working_directory")
        self._working_directory = (
            working_directory if isinstance(working_directory, str) else None
        )
        self._apply_snapshot()

    # ---- state push ------------------------------------------------------

    def _apply_full_state(self) -> None:
        if not self._attached or not self._web_ready:
            return
        self._apply_snapshot()
        self._apply_working_directory()
        self._apply_detection()
        self._apply_personas()
        self._apply_attachments()

    def _apply_snapshot(self) -> None:
        self._evaluate("discussionApplySnapshot", self.bridge.snapshot())

    def _apply_detection(self) -> None:
        detections: list[DetectionResult] = self.bridge.detect_participants()
        self._evaluate(
            "discussionApplyDetection",
            [asdict(detection) for detection in detections],
        )

    def _apply_personas(self) -> None:
        self._personas = list_personas(self._language)
        self._evaluate("discussionApplyPersonas", self._personas)

    def _apply_working_directory(self) -> None:
        self._evaluate("discussionApplyWorkingDir", self._working_directory)

    def _apply_attachments(self, hint: str | None = None) -> None:
        self._evaluate(
            "discussionApplyAttachments",
            {"attachments": list(self._attachments), "hint": hint},
        )

    # ---- attachments -----------------------------------------------------

    def _handle_paste_image(self) -> None:
        result = read_clipboard_image()
        if result is None:
            self._apply_attachments(hint=_t(self._language, "discussion_paste_no_image"))
            return
        data, suffix = result
        if len(data) > DROP_MAX_BYTES:
            self._apply_attachments(
                hint=_t(self._language, "discussion_drop_too_large", name="")
            )
            return
        try:
            target = save_attachment_bytes(data, suffix)
        except OSError:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_failed"))
            return
        self._add_attachment(target)
        self._apply_attachments()

    def _handle_drop_image(self, data: str, name: str) -> None:
        suffix = Path(name).suffix.lower()
        if suffix not in ATTACHMENT_SUFFIXES:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_not_image"))
            return
        try:
            raw = base64.b64decode(data, validate=True)
        except ValueError:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_failed"))
            return
        if len(raw) > DROP_MAX_BYTES:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_too_large"))
            return
        try:
            target = save_attachment_bytes(raw, suffix)
        except OSError:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_failed"))
            return
        self._add_attachment(target)
        self._apply_attachments()

    def _handle_pick_image(self) -> None:
        selected = self._pick_image_file()
        if selected is None:
            return
        try:
            target = import_attachment_file(selected)
        except OSError:
            self._apply_attachments(hint=_t(self._language, "discussion_drop_failed"))
            return
        if target is None:
            self._apply_attachments(hint=_t(self._language, "discussion_paste_no_image"))
            return
        self._add_attachment(target)
        self._apply_attachments()

    def _add_attachment(self, target: Path) -> None:
        attachment = {"name": target.name, "path": str(target)}
        thumbnail = attachment_thumbnail_data_uri(target)
        if thumbnail is not None:
            attachment["thumbnail"] = thumbnail
        self._attachments.append(attachment)

    def _remove_attachment(self, path: str) -> None:
        before = len(self._attachments)
        self._attachments = [
            attachment for attachment in self._attachments if attachment["path"] != path
        ]
        if len(self._attachments) == before:
            return
        with contextlib.suppress(OSError):
            Path(path).unlink()
        self._apply_attachments()

    # ---- native dialogs ---------------------------------------------------

    def _pick_folder(self) -> str | None:
        return self._first_dialog_result(folder=True)

    def _pick_image_file(self) -> str | None:
        return self._first_dialog_result(folder=False)

    def _first_dialog_result(self, *, folder: bool) -> str | None:
        if self.window is None:
            return None
        import webview

        try:
            if folder:
                result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            else:
                patterns = tuple(f"*{suffix}" for suffix in ATTACHMENT_SUFFIXES)
                result = self.window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    allow_multiple=False,
                    file_types=(f"Images ({';'.join(patterns)})",),
                )
        except Exception:  # noqa: BLE001 - a cancelled or failed dialog is not an error
            logger.debug("file dialog failed", exc_info=True)
            return None
        if not result:
            return None
        first = result[0] if isinstance(result, (list, tuple)) else result
        return str(first) if first else None

    # ---- javascript -------------------------------------------------------

    def _evaluate(self, function_name: str, payload: object) -> None:
        if not self._attached or not self._web_ready or self.window is None:
            return
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self._run_script(f"window.{function_name} && window.{function_name}({encoded});")

    def _run_script(self, script: str) -> None:
        window = self.window
        if window is None:
            return
        try:
            window.evaluate_js(script)
        except Exception:  # noqa: BLE001 - a closed window must not kill the bridge
            logger.debug("discussion evaluate_js failed", exc_info=True)
