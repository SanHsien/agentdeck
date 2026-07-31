# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from council import discussion_window_win as win

ROOT = Path(__file__).resolve().parents[1]


class _FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.shown = 0
        self.hidden = 0
        self.destroyed = 0
        self.events = SimpleNamespace(loaded=SimpleNamespace(__iadd__=lambda self, fn: self))

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)

    def show(self) -> None:
        self.shown += 1

    def hide(self) -> None:
        self.hidden += 1

    def destroy(self) -> None:
        self.destroyed += 1


def _controller(window: Any = None, *, ready: bool = True) -> Any:
    controller = object.__new__(win.WindowsDiscussionWindowController)
    controller.window = window
    controller._attached = True
    controller._web_ready = ready
    controller._shutdown = False
    controller._language = "en"
    controller._attachments = []
    controller._personas = []
    controller._working_directory = None
    return controller


def test_evaluate_emits_a_guarded_call_with_json_payload() -> None:
    window = _FakeWindow()
    controller = _controller(window)

    controller._evaluate("discussionApplySnapshot", {"status": "idle", "中文": True})

    assert len(window.scripts) == 1
    script = window.scripts[0]
    # The guard matters: the page may post an action before its handlers exist.
    assert script.startswith("window.discussionApplySnapshot && window.discussionApplySnapshot(")
    payload = script[script.index("(") + 1 : script.rindex(")")]
    assert json.loads(payload) == {"status": "idle", "中文": True}


def test_evaluate_is_a_no_op_before_the_page_is_ready() -> None:
    window = _FakeWindow()
    controller = _controller(window, ready=False)

    controller._evaluate("discussionApplySnapshot", {})

    assert window.scripts == []


def test_evaluate_survives_a_window_that_has_gone_away() -> None:
    class _Dead(_FakeWindow):
        def evaluate_js(self, script: str) -> None:
            raise RuntimeError("window is closed")

    controller = _controller(_Dead())

    # A closed window must not take the bridge down with it.
    controller._evaluate("discussionApplyError", "boom")


def test_receive_action_reports_failures_back_to_the_page() -> None:
    window = _FakeWindow()
    controller = _controller(window)

    controller.receive_action({"action": "nope"})

    assert window.scripts, "the failure was swallowed instead of surfaced"
    assert "discussionApplyError" in window.scripts[-1]


def test_clipboard_image_rejects_a_file_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    # Explorer file copies arrive as a list of paths; that is a file paste, not
    # an image paste, and must not be mistaken for bitmap data.
    monkeypatch.setattr(
        win, "read_clipboard_image", win.read_clipboard_image
    )  # keep the real function
    import PIL.ImageGrab as grab

    monkeypatch.setattr(grab, "grabclipboard", lambda: ["C:\\tmp\\a.png"])

    assert win.read_clipboard_image() is None


def test_clipboard_image_encodes_a_bitmap_as_png(monkeypatch: pytest.MonkeyPatch) -> None:
    import PIL.ImageGrab as grab
    from PIL import Image

    monkeypatch.setattr(grab, "grabclipboard", lambda: Image.new("RGB", (4, 4), "red"))

    result = win.read_clipboard_image()

    assert result is not None
    data, suffix = result
    assert suffix == ".png"
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_clipboard_image_returns_none_when_the_clipboard_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import PIL.ImageGrab as grab

    monkeypatch.setattr(grab, "grabclipboard", lambda: None)

    assert win.read_clipboard_image() is None


def test_drain_limit_and_shared_serializer() -> None:
    # The neutral half of the feature lives in discussion_assets and is shared,
    # so a change there must keep serving this host.
    from council import discussion_assets

    events = discussion_assets.serialize_event_batch([], {})

    assert isinstance(events, str)
    assert win.EVENT_DRAIN_LIMIT == 50


def test_participant_controls_reflow_before_the_setup_grid_collapses() -> None:
    html = (ROOT / "assets" / "windows" / "discussion.html").read_text(encoding="utf-8")

    responsive = html.split("@media (max-width: 1050px)", maxsplit=1)[1].split(
        "@media (max-width: 720px)",
        maxsplit=1,
    )[0]

    assert "grid-template-columns: auto minmax(0, 1fr) auto;" in responsive
    assert ".participant-model" in responsive
    assert "grid-row: 2;" in responsive


def test_shutdown_is_idempotent_and_releases_the_window() -> None:
    window = _FakeWindow()
    controller = _controller(window)
    controller.bridge = SimpleNamespace(
        shutdown=lambda timeout: None,
        set_event_listener=lambda listener: None,
    )
    controller._drain_lock = __import__("threading").Lock()
    controller._drain_scheduled = False

    controller.shutdown()
    controller.shutdown()

    assert window.destroyed == 1
    assert controller.window is None


def test_the_participant_scroller_reserves_room_for_a_whole_card() -> None:
    """The list may scroll; it may not cut the first card's controls off.

    When the model and persona controls wrapped onto a second row the cards got
    taller, but ``.controls-scroll`` still had ``min-height: 0``, so at 900x640
    they sat 24px below the fold. A CSS-shape assertion cannot catch that --
    ``tools/verify_discussion_layout.py`` measures it in a real WebView2 -- but
    pinning the reservation here stops it silently going back to zero.
    """
    html = (ROOT / "assets" / "windows" / "discussion.html").read_text(encoding="utf-8")

    scroller = html.split(".controls-scroll {", maxsplit=1)[1].split("}", maxsplit=1)[0]

    assert "min-height: 150px;" in scroller, (
        "the participant scroller must reserve height for the section heading "
        "plus one whole card"
    )
    assert "overflow-y: auto;" in scroller
