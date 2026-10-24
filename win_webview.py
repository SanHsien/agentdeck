# SPDX-License-Identifier: AGPL-3.0-only

"""Where the Windows panel's WebView2 profile lives."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Abnormal exits reuse one dir; pywebview private mode wipes it on clean exit,
# so keep a dedicated subdir rather than ~/.agentdeck itself.
WEBVIEW_STORAGE_DIR = Path.home() / ".agentdeck" / "webview"


def start_options() -> dict[str, Any]:
    """Keyword arguments for ``webview.start``."""
    return {
        "gui": "edgechromium",
        "debug": os.environ.get("AGENTDECK_DEBUG") == "1",
        "storage_path": str(WEBVIEW_STORAGE_DIR),
    }
