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

__version__ = "1.0"


def _read_stdin_utf8() -> str:
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        return sys.stdin.read()
    return cast(bytes, buffer.read()).decode("utf-8", "replace")


PROMPT_SIDECAR = Path(os.path.expanduser("~/.claude/agentdeck-terse-prompt.json"))

_DEFAULT_INSTRUCTION: dict[str, str] = {
    "zh-TW": (
        "（這個對話已開啟「精簡模式」：請在這次對話第一則回覆的最前面提一下這件事——如果"
        "你同時收到其他要打招呼的指示（例如進度交接），就把「精簡模式已開啟」自然併入那句"
        "招呼裡就好，不要另外多開一句；如果沒有其他招呼可以搭，就自己說一行「🐾 已開啟精簡"
        "模式，回覆會盡量簡短，繼續吧！」。從現在起，直到這個對話結束為止，每一則回覆都要"
        "遵守這條規則——不會因為對話變長、話題變多就淡忘或恢復正常語氣。允許用短句、片語"
        "甚至不成句的斷句表達，不必湊成完整句子；去掉虛詞贅字、客套語、重複鋪陳與不必要的"
        "過渡句；用詞挑簡短的（例如「修」不要「針對這個問題實作解決方案」）。不用裝飾性"
        "表格或表情符號，也不要旁白工具呼叫的過程。不要自創縮寫（例如「設定」別縮成「設」、"
        "「函式」別縮成「函」）——這類縮寫斷詞長度跟完整詞一樣，省不到字數，反而讓讀者要"
        "多想一下，直接用完整詞更省事也更清楚。程式碼、指令、檔案路徑、錯誤訊息一個字都"
        "不能省略或改寫。遇到安全警示、不可逆操作的確認、或多步驟中省略連接詞會有誤讀風險"
        "的情況，這幾種要先恢復完整、講清楚，講完再切回精簡語氣。如果使用者明確要求詳細"
        "解說、逐步教學，或情境需要完整推理，仍以使用者當下的要求為準，不要因為這個模式而"
        "省略關鍵資訊。）"
    ),
    "en": (
        "(Terse mode is on for this entire conversation. Mention this at the very "
        "start of your first reply — if you're already leading with another greeting "
        "(e.g. a resume handoff), fold \"terse mode is on\" into that same line instead "
        "of adding a separate one; if there's no other greeting to fold into, say your "
        "own line: \"🐾 Terse mode is on — keeping replies short, let's go!\" This "
        "applies starting now and lasting until the conversation ends — apply it to "
        "every single reply, no matter how long the conversation gets; don't let it "
        "fade or drift back to normal verbosity partway through. Drop articles "
        "(a/an/the), filler (just/really/basically/actually), pleasantries (sure/"
        "certainly/happy to), and hedging. Fragments are fine. Prefer short synonyms "
        "(big, not extensive; fix, not \"implement a solution for\"). No decorative "
        "tables, emoji, or tool-call narration. Never invent abbreviations (cfg/impl/"
        "req/res) — the tokenizer splits them the same as the full word, so nothing "
        "is saved and the reader still has to decode it; use the full word instead. "
        "Code, commands, file paths, and error messages must stay byte-exact, never "
        "trimmed or rewritten. Drop terseness for security warnings, irreversible-"
        "action confirmations, and multi-step instructions where a fragment or dropped "
        "conjunction risks being misread — write those out in full, then resume terse "
        "mode after. If the user explicitly asks for a detailed walkthrough, step-by-"
        "step teaching, or the situation needs full reasoning, follow that instead — "
        "don't drop essential information just to stay terse.)"
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
    normalized = code.split(".")[0].strip().lower().replace("_", "-")
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
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
