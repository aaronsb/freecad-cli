# SPDX-License-Identifier: LGPL-2.1-or-later

"""GUI init.

The dock registers itself with the main window, so FreeCAD's
View -> Panels menu picks it up automatically -- that menu is built from
``QMainWindow::createPopupMenu()``, which enumerates dock widgets. No custom
menu is needed.
"""

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6 import QtCore
except ImportError:  # pragma: no cover
    from PySide import QtCore


def _install():
    mw = Gui.getMainWindow()
    if mw is None:
        App.Console.PrintError("[fccli] no main window; giving up\n")
        return
    try:
        from fccli.command import register
        register()
    except Exception as exc:
        App.Console.PrintWarning(f"[fccli] command registration: {exc}\n")
    try:
        from fccli import dock
        d = dock.show()
        state = "shown" if d is not None else "failed"
        App.Console.PrintMessage(
            f"[fccli] command line {state} -- View > Panels > Command Line\n")
    except Exception as exc:
        import traceback
        App.Console.PrintError(f"[fccli] dock failed: {exc}\n")
        App.Console.PrintError(traceback.format_exc())


# The main window is not fully built when InitGui runs.
QtCore.QTimer.singleShot(1500, _install)
