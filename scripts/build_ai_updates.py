#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Render ``ai_updates.json`` into a self-hosted AI Update Daily page.

Upstream publishes its own page from a separate repository that carries no
license, so it cannot be forked and republished. It does not need to be: the
data file itself ships inside this AGPL-3.0 repository and arrives refreshed
with every upstream merge, so this renderer reads what we already hold and
writes a page onto this fork's own GitHub Pages site.

Output is a single self-contained file with no external requests, and depends
only on the data — no generation timestamp — so rebuilding without a data change
produces a byte-identical page and reviewing the diff stays meaningful.

    python scripts/build_ai_updates.py
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "ai_updates.json"
OUTPUT_FILE = REPO_ROOT / "docs" / "ai-updates" / "index.html"

# This fork ships two UI languages; the data carries five. Rendering the three
# nobody can select would triple the page for no reader.
LANGUAGES = ("zh-TW", "en")
DEFAULT_LANGUAGE = "zh-TW"

UI_TEXT = {
    "zh-TW": {
        "title": "AI 更新日報",
        "tagline": "Claude Code、Codex、Antigravity 與相關工具的更新彙整",
        "generated": "資料日期",
        "original": "官方原文",
        "empty": "這個工具目前沒有收錄的更新。",
        "source": "資料來自 usage 專案內的 ai_updates.json，隨上游同步更新。",
        "back": "← 回到 usage",
    },
    "en": {
        "title": "AI Update Daily",
        "tagline": "Release notes for Claude Code, Codex, Antigravity and related tools",
        "generated": "Data date",
        "original": "Original text",
        "empty": "No updates recorded for this tool yet.",
        "source": (
            "Data comes from ai_updates.json inside the usage project, "
            "refreshed with upstream."
        ),
        "back": "← Back to usage",
    },
}

_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def render_text(raw: str) -> str:
    """Escape a data string, then re-enable the one bit of markup it uses.

    The bodies are prose with `backtick` code spans. Everything is escaped
    first so nothing in the data can inject markup, and only the code spans are
    turned back into tags afterwards — on the already-escaped text, so a span's
    contents stay inert.
    """
    escaped = html.escape(raw, quote=False)
    return _CODE_SPAN_RE.sub(r"<code>\1</code>", escaped)


def _pick(values: Any, language: str) -> str:
    """Return a translation, falling back to English then to any value present."""
    if not isinstance(values, dict):
        return str(values or "")
    for candidate in (language, "en"):
        text = values.get(candidate)
        if isinstance(text, str) and text.strip():
            return text
    for text in values.values():
        if isinstance(text, str) and text.strip():
            return text
    return ""


def render_items(version: dict[str, Any], language: str, strings: dict[str, str]) -> str:
    items = version.get("items")
    if not isinstance(items, list) or not items:
        return f'<p class="empty">{html.escape(strings["empty"])}</p>'
    rendered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = render_text(_pick(item.get("title"), language))
        body = render_text(_pick(item.get("body"), language))
        original = item.get("original")
        original_block = ""
        if isinstance(original, str) and original.strip():
            original_block = (
                f'<details class="original"><summary>{html.escape(strings["original"])}'
                f"</summary><p>{render_text(original)}</p></details>"
            )
        rendered.append(
            f'<li class="item"><h4>{title}</h4><p>{body}</p>{original_block}</li>'
        )
    return f'<ul class="items">{"".join(rendered)}</ul>'


def render_language(data: dict[str, Any], language: str) -> str:
    strings = UI_TEXT[language]
    tools = data.get("tools")
    sections = []
    if isinstance(tools, list):
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            name = html.escape(str(tool.get("name") or tool.get("id") or ""))
            versions = tool.get("versions")
            blocks = []
            if isinstance(versions, list):
                for version in versions:
                    if not isinstance(version, dict):
                        continue
                    label = html.escape(str(version.get("version") or ""))
                    period = html.escape(str(version.get("period") or ""))
                    blocks.append(
                        f'<section class="version"><h3><span class="ver">{label}</span>'
                        f'<span class="period">{period}</span></h3>'
                        f"{render_items(version, language, strings)}</section>"
                    )
            sections.append(
                f'<section class="tool"><h2>{name}</h2>{"".join(blocks)}</section>'
            )
    return "".join(sections)


def render_page(data: dict[str, Any]) -> str:
    generated = html.escape(str(data.get("generated_at") or ""))
    panes = []
    for language in LANGUAGES:
        strings = UI_TEXT[language]
        hidden = "" if language == DEFAULT_LANGUAGE else " hidden"
        panes.append(
            f'<div class="pane" data-lang="{language}"{hidden}>'
            f'<header><h1>{html.escape(strings["title"])}</h1>'
            f'<p class="tagline">{html.escape(strings["tagline"])}</p>'
            f'<p class="meta">{html.escape(strings["generated"])}: {generated}</p></header>'
            f'<main>{render_language(data, language)}</main>'
            f'<footer><p>{html.escape(strings["source"])}</p>'
            f'<p><a href="../">{html.escape(strings["back"])}</a> · '
            f'<a href="https://github.com/SanHsien/usage">github.com/SanHsien/usage</a></p>'
            f"</footer></div>"
        )
    buttons = "".join(
        f'<button type="button" data-pick="{lang}"'
        f'{" aria-current=\"true\"" if lang == DEFAULT_LANGUAGE else ""}>'
        f'{"繁體中文" if lang == "zh-TW" else "English"}</button>'
        for lang in LANGUAGES
    )
    return f"""<!doctype html>
<html lang="{DEFAULT_LANGUAGE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(UI_TEXT[DEFAULT_LANGUAGE]["title"])} — usage</title>
<style>
:root {{ color-scheme: dark; --bg:#0a0a0a; --card:#161616; --line:#2a2a2a;
  --fg:#f2f2f2; --dim:#9a9a9a; --accent:#f49164; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.7 -apple-system,
  "Segoe UI","Noto Sans TC",system-ui,sans-serif; }}
.wrap {{ max-width:820px; margin:0 auto; padding:32px 20px 64px }}
.langbar {{ display:flex; gap:8px; justify-content:flex-end; margin-bottom:24px }}
.langbar button {{ background:var(--card); color:var(--dim); border:1px solid var(--line);
  border-radius:999px; padding:6px 14px; font:inherit; font-size:.85rem; cursor:pointer }}
.langbar button[aria-current="true"] {{ color:var(--fg); border-color:var(--accent) }}
h1 {{ font-size:1.9rem; margin:0 0 6px }}
.tagline {{ color:var(--dim); margin:0 0 4px }}
.meta {{ color:var(--dim); font-size:.85rem; margin:0 0 32px }}
.tool > h2 {{ font-size:1.3rem; margin:40px 0 12px; padding-bottom:8px;
  border-bottom:1px solid var(--line) }}
.version {{ margin:0 0 24px }}
.version h3 {{ display:flex; gap:10px; align-items:baseline; font-size:1rem; margin:18px 0 10px }}
.ver {{ color:var(--accent); font-weight:700 }}
.period {{ color:var(--dim); font-size:.8rem }}
.items {{ list-style:none; margin:0; padding:0; display:grid; gap:12px }}
.item {{ background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:14px 16px }}
.item h4 {{ margin:0 0 6px; font-size:1rem }}
.item p {{ margin:0; color:#dcdcdc }}
.empty {{ color:var(--dim); font-style:italic }}
code {{ background:#000; border:1px solid var(--line); border-radius:4px;
  padding:1px 5px; font-size:.87em }}
.original {{ margin-top:10px }}
.original summary {{ color:var(--dim); font-size:.83rem; cursor:pointer }}
.original p {{ margin:8px 0 0; color:var(--dim); font-size:.9rem }}
footer {{ margin-top:48px; padding-top:20px; border-top:1px solid var(--line);
  color:var(--dim); font-size:.85rem }}
footer a {{ color:var(--accent) }}
</style>
</head>
<body>
<div class="wrap">
<nav class="langbar">{buttons}</nav>
{"".join(panes)}
</div>
<script>
document.querySelector('.langbar').addEventListener('click', function (event) {{
  var button = event.target.closest('button[data-pick]');
  if (!button) return;
  var pick = button.dataset.pick;
  document.documentElement.lang = pick;
  document.querySelectorAll('.pane').forEach(function (pane) {{
    pane.hidden = pane.dataset.lang !== pick;
  }});
  document.querySelectorAll('.langbar button').forEach(function (other) {{
    if (other.dataset.pick === pick) other.setAttribute('aria-current', 'true');
    else other.removeAttribute('aria-current');
  }});
}});
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the page is out of date.",
    )
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    page = render_page(data)

    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != page:
            print(f"FAIL: {args.output} is out of date; run scripts/build_ai_updates.py")
            return 1
        print("PASS: AI Update Daily page is up to date")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8", newline="\n")
    print(f"wrote {args.output.relative_to(REPO_ROOT)} ({len(page):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
