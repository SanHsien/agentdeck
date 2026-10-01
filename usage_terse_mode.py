#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""usage SessionStart hook — inject terse-mode instructions into a new Claude session.

Claude Code runs this on SessionStart (matcher ``startup|clear``) and pipes the
session JSON on stdin. Unlike ``usage_session_resume.py``, this hook does not
inspect transcripts or git state: if stdin parses as a JSON object at all, it
prints a fixed instruction telling Claude to keep replies terse while leaving
code, commands, file paths, and error messages untouched.

Stdlib-only and 3.9-safe — same constraint as ``usage_statusline.py`` and
``usage_session_resume.py``: it may run under macOS's bundled
``/usr/bin/python3`` (3.9), so no third-party imports, no ``datetime.UTC``, no
runtime ``X | Y`` types. The prompt wording lives in a sidecar written by
``setup_hook``; if that file is missing, this script falls back to embedded
defaults. Any failure exits 0 with no output.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

__version__ = "1.4"


def _read_stdin_utf8() -> str:
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        return sys.stdin.read()
    return cast(bytes, buffer.read()).decode("utf-8", "replace")


PROMPT_SIDECAR = Path(os.path.expanduser("~/.claude/agentdeck-terse-prompt.json"))

_DEFAULT_INSTRUCTION: dict[str, str] = {
    "zh-TW": (
        "（這個對話已開啟「精簡模式」：請在這次對話第一則回覆的最前面提一下這件事——如"
        "果你同時收到其他要打招呼的指示（例如進度交接），就把「精簡模式已開啟」自然併"
        "入那句招呼裡就好，不要另外多開一句；如果沒有其他招呼可以搭，就自己說一行「🐾"
        " 已開啟精簡模式，回覆會盡量簡短，繼續吧！」。整個對話都適用。去掉虛詞贅字、"
        "客套語、重複鋪陳與不必要的過渡句；用詞挑簡短的（例如「修」不要「針對這個問題"
        "實作解決方案」）。精簡是預算，白話是風格：短不等於難懂。挑最口語的說法，能用"
        "日常字就不要用術語（例如「先存檔」不要「先持久化」）。非用不可的技術詞，第一"
        "次出現時在後面補十個字以內的白話解釋，之後直接用。工具或子代理的輸出不要原文"
        "轉貼：先讀懂再用白話重寫成結論，只有程式碼、指令、路徑、錯誤訊息照原文保留。"
        "不要比喻。收尾就三件事：做了什麼、成功沒、下一步做什麼。不用裝飾性表格；除了"
        "開頭那句招呼，內文不放表情符號。不要複述工具名稱或呼叫過程，但開工具前用一句"
        "話說明要做什麼是可以的。不要自創縮寫（例如「設定」別縮成「設」、「函式」別縮"
        "成「函」）——這類縮寫斷詞長度跟完整詞一樣，省不到字數，反而讓讀者要多想一下，"
        "直接用完整詞更省事也更清楚。程式碼、指令、檔案路徑、錯誤訊息一個字都不能省略"
        "或改寫。遇到安全警示、不可逆操作的確認、或多步驟中省略連接詞會有誤讀風險的情"
        "況，這幾種要先恢復完整、講清楚，講完再切回精簡語氣。如果使用者明確要求詳細解"
        "說、逐步教學，或情境需要完整推理，仍以使用者當下的要求為準，不要因為這個模式"
        "而省略關鍵資訊。）"
    ),
    "en": (
        "(Terse mode is on for this entire conversation. Mention this at the very sta"
        "rt of your first reply — if you're already leading with another greeting (e."
        "g. a resume handoff), fold \"terse mode is on\" into that same line instead of"
        " adding a separate one; if there's no other greeting to fold into, say your "
        "own line: \"🐾 Terse mode is on — keeping replies short, let's go!\" Cut fille"
        "r (just/really/basically/actually) and pleasantries (sure/certainly/happy to"
        "). Prefer short synonyms (big, not extensive; fix, not \"implement a solution"
        " for\"). Terse is the budget; plain is the style — short must never mean cryp"
        "tic. Pick the everyday word over the jargon one (\"save it first\", not \"persi"
        "st it first\"). When a technical term is unavoidable, gloss it once on first "
        "use in eight words or fewer, then just use it. Never paste a tool's or subag"
        "ent's output verbatim: read it, then rewrite it as a plain-language conclusi"
        "on — only code, commands, paths, and error messages stay verbatim. No analog"
        "ies. Close with what you did, whether it worked, and what to do next. No dec"
        "orative tables, and no emoji in the body beyond the opening greeting. Don't "
        "recite tool names or narrate calls — but one line of intent before running a"
        " tool is fine. Never invent abbreviations (cfg/impl/req/res) — the tokenizer"
        " splits them the same as the full word, so nothing is saved and the reader s"
        "till has to decode it; use the full word instead. Code, commands, file paths"
        ", and error messages must stay byte-exact, never trimmed or rewritten. Drop "
        "terseness for security warnings, irreversible-action confirmations, and mult"
        "i-step instructions where a fragment or dropped conjunction risks being misr"
        "ead — write those out in full, then resume terse mode after. If the user exp"
        "licitly asks for a detailed walkthrough, step-by-step teaching, or the situa"
        "tion needs full reasoning, follow that instead — don't drop essential inform"
        "ation just to stay terse.)"
    ),
}


def _windows_system_lang() -> str:
    if os.name != "nt":
        return ""
    try:
        import ctypes
        import locale as _locale

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return ""
        lang_id = int(windll.kernel32.GetUserDefaultUILanguage())
        return _locale.windows_locale.get(lang_id, "") or ""
    except Exception:
        return ""


def _detect_lang() -> str:
    # LANG is deliberately not consulted. Git Bash and MSYS inject one (usually
    # en_US.UTF-8) that reflects the shell, not the user, and it silently
    # outranked the system UI language: a zh-TW machine launched from Git Bash
    # got an English UI. This is a Windows-only application, so the shell's
    # LANG has no claim the system setting does not already answer better.
    for key in ("AGENTDECK_LANG", "TT_LANG"):
        value = os.environ.get(key, "").strip()
        if value:
            return _normalize_lang(value)
    return _normalize_lang(_windows_system_lang())


def _normalize_lang(code: str) -> str:
    normalized = code.split(".")[0].split("@")[0].strip().lower().replace("_", "-")
    # Traditional Chinese and English are the only shipped languages: every
    # Chinese variant maps to zh-TW, everything else falls back to English.
    if normalized == "zh" or normalized.startswith("zh-"):
        return "zh-TW"
    return "en"


def _load_instruction(lang: str) -> str:
    try:
        raw = json.loads(PROMPT_SIDECAR.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raw = None
    if isinstance(raw, dict):
        table = raw.get(lang)
        if isinstance(table, dict):
            instruction = table.get("instruction")
            if isinstance(instruction, str) and instruction:
                return instruction
        table = raw.get("en")
        if isinstance(table, dict):
            instruction = table.get("instruction")
            if isinstance(instruction, str) and instruction:
                return instruction
    return _DEFAULT_INSTRUCTION.get(lang, _DEFAULT_INSTRUCTION["en"])


def main() -> int:
    try:
        payload = json.loads(_read_stdin_utf8() or "{}")
    except (OSError, ValueError, TypeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": _load_instruction(_detect_lang()),
        }
    }
    try:
        print(json.dumps(output, ensure_ascii=True))
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
