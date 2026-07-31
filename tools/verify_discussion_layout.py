# SPDX-License-Identifier: AGPL-3.0-only
"""Measure the AI Council layout in a real WebView2 and report clipping.

Screenshots show that something looks wrong; they do not say by how much, and
they cannot be diffed. This opens the actual window at a given logical size and
asks the live DOM for geometry, so "the persona dropdown is cut off" becomes a
number of pixels.

Usage:
    python tools/verify_discussion_layout.py                  # default matrix
    python tools/verify_discussion_layout.py 900x640 1280x800
    WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--force-device-scale-factor=1.5 \
        python tools/verify_discussion_layout.py 900x640
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SIZES = ["900x640", "1280x800"]

# Runs inside the page. Returns the numbers that decide pass or fail: whether a
# participant card's controls are reachable without being cut by the scroller.
PROBE = """
(function () {
  var chip = document.querySelector('.participant-chip');
  var scroll = document.querySelector('.controls-scroll');
  if (!chip || !scroll) { return JSON.stringify({error: 'chip or scroller missing'}); }
  var model = chip.querySelector('.participant-model');
  var persona = chip.querySelector('.participant-persona');
  var chipBox = chip.getBoundingClientRect();
  var scrollBox = scroll.getBoundingClientRect();
  function overflow(el) {
    if (!el) { return null; }
    var box = el.getBoundingClientRect();
    return {
      height: Math.round(box.height),
      belowFold: Math.round(box.bottom - scrollBox.bottom),
    };
  }
  return JSON.stringify({
    devicePixelRatio: window.devicePixelRatio,
    viewport: {w: window.innerWidth, h: window.innerHeight},
    scroller: {
      visible: Math.round(scrollBox.height),
      content: scroll.scrollHeight,
      scrollable: scroll.scrollHeight > Math.ceil(scrollBox.height),
    },
    card: {
      height: Math.round(chipBox.height),
      content: chip.scrollHeight,
      clipsOwnChildren: chip.scrollHeight > Math.ceil(chipBox.height) + 1,
    },
    model: overflow(model),
    persona: overflow(persona),
    horizontalScroll: document.documentElement.scrollWidth >
                      document.documentElement.clientWidth,
  });
})()
"""


def probe(width: int, height: int) -> dict[str, Any]:
    import webview

    from discussion_window_win import WindowsDiscussionWindowController

    controller = WindowsDiscussionWindowController()
    result: dict[str, Any] = {}

    def run() -> None:
        try:
            window = controller.window
            assert window is not None
            # resize() only works once the GUI loop owns the window.
            window.resize(width, height)
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"resize failed: {type(exc).__name__}: {exc}"
        time.sleep(6)  # WebView2 init plus first paint and reflow
        try:
            window = controller.window
            assert window is not None
            # Scroll the list to the top so the measurement is deterministic.
            window.evaluate_js(
                "var s=document.querySelector('.controls-scroll'); if (s) s.scrollTop=0;"
            )
            time.sleep(0.4)
            result.update(json.loads(window.evaluate_js(PROBE)))
        except Exception as exc:  # noqa: BLE001 - reported, not raised, so the loop closes
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            controller.shutdown()

    controller.show()
    webview.start(run, debug=False)
    return result


def verdict(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """A card must be fully reachable; scrolling is fine, clipping is not."""
    problems: list[str] = []
    if "error" in data:
        return False, [data["error"]]

    # With the list scrolled to the top, the first card must be whole. Comparing
    # the scroller's height against the card's own box is not enough -- the card
    # can be shorter than its contents and clip them itself.
    card = data["card"]
    if card["clipsOwnChildren"]:
        problems.append(
            f"the card's box is {card['height']}px but its content needs "
            f"{card['content']}px, so the card clips its own controls"
        )
    for name in ("model", "persona"):
        control = data.get(name)
        if control is None:
            problems.append(f"{name} control not found")
            continue
        if control["height"] < 8:
            problems.append(f"{name} collapsed to {control['height']}px")
        if control["belowFold"] > 0:
            problems.append(
                f"{name} extends {control['belowFold']}px past the bottom of the "
                "scroller with the list at the top, so the first card is not whole"
            )
    if data["horizontalScroll"]:
        problems.append("the page scrolls horizontally")
    return not problems, problems


def main() -> int:
    sizes = sys.argv[1:] or DEFAULT_SIZES
    failed = False
    for size in sizes:
        width, height = (int(part) for part in size.lower().split("x"))
        data = probe(width, height)
        ok, problems = verdict(data)
        status = "PASS" if ok else "FAIL"
        print(f"\n=== {size} -> {status} ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        for problem in problems:
            print(f"  - {problem}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
