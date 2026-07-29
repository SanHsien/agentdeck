# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""Panel helpers shared by the tray UI.

This package used to own the macOS panel registry (``all_panels`` and the
``HTMLPanel`` instances behind it), which existed only to drive the PyObjC
popover. Windows declares its panels in ``wintray.WINDOWS_PANELS`` instead, so
with macOS support removed only the platform-neutral helpers remain:
``panels.payload`` and ``panels.dynamic_height``.
"""

from __future__ import annotations
