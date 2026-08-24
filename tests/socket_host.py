# SPDX-License-Identifier: LGPL-2.1-or-later

"""Boot FreeCAD and hold it open for the socket test to drive."""

import FreeCAD as App
from PySide6 import QtCore


def announce():
    from fccli import dock as D
    d = D.instance()
    if d is None or d.server is None:
        App.Console.PrintError("[socket-host] no dock or no server\n")
        return
    App.Console.PrintMessage(f"[socket-host] ready on {d.server.path}\n")


QtCore.QTimer.singleShot(9000, announce)
