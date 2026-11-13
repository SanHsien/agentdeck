# SPDX-License-Identifier: AGPL-3.0-only
"""Report Windows settings failures through the existing controller UI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import _t

if TYPE_CHECKING:
    from wintray import _WindowsTrayController

logger = logging.getLogger(__name__)


def toggle_login(controller: _WindowsTrayController) -> None:
    import win_login_item

    try:
        win_login_item.disable() if win_login_item.is_enabled() else win_login_item.enable()
    except OSError as exc:
        controller._message_box(_t(controller.language, "launch_at_login_failed", error=str(exc)))


def toggle_statusline(controller: _WindowsTrayController) -> None:
    from statusline_settings import _toggle_statusline_settings

    try:
        _, exit_code = _toggle_statusline_settings()
    except Exception as exc:
        logger.warning("statusLine settings toggle failed", exc_info=True)
        controller._report_action_result(
            _t(controller.language, "statusline_action_failed"), detail=str(exc), failed=True
        )
    else:
        if exit_code != 0:
            controller._report_action_result(
                _t(controller.language, "statusline_action_failed"), failed=True
            )
    controller.refresh()
