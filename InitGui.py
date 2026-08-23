"""GUI init: register the toggle command and open the dock once the main
window exists."""

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide6 import QtCore, QtGui
except ImportError:  # pragma: no cover
    from PySide import QtCore, QtGui


class FCCLI_Toggle:
    """Registered with FreeCAD so the shortcut is user-configurable."""

    def GetResources(self):
        return {
            "MenuText": "Command Line",
            "ToolTip": "Show or hide the FreeCAD CLI command line",
            "Accel": "Ctrl+`",
        }

    def IsActive(self):
        return True

    def Activated(self):
        toggle()


def toggle():
    from fccli import dock
    d = dock.instance()
    if d is not None and d.isVisible():
        d.hide()
    else:
        dock.show()


def _add_menu(mw):
    menu = mw.menuBar().addMenu("CLI")
    act = QtGui.QAction("Command Line", mw)
    act.setObjectName("FCCLI_Toggle_Menu")
    act.setShortcut(QtGui.QKeySequence("Ctrl+`"))
    act.setShortcutContext(QtCore.Qt.ApplicationShortcut)
    act.triggered.connect(toggle)
    menu.addAction(act)
    mw.addAction(act)   # keep the shortcut live regardless of menu focus


def _install():
    try:
        Gui.addCommand("FCCLI_Toggle", FCCLI_Toggle())
    except Exception as exc:
        App.Console.PrintWarning(f"[fccli] command registration: {exc}\n")

    mw = Gui.getMainWindow()
    if mw is None:
        App.Console.PrintError("[fccli] no main window; giving up\n")
        return
    try:
        _add_menu(mw)
    except Exception as exc:
        App.Console.PrintWarning(f"[fccli] menu: {exc}\n")

    try:
        from fccli import dock
        dock.show()
        App.Console.PrintMessage("[fccli] command line ready (Ctrl+`)\n")
    except Exception as exc:
        import traceback
        App.Console.PrintError(f"[fccli] dock failed: {exc}\n")
        App.Console.PrintError(traceback.format_exc())


# The main window is not fully built when InitGui runs.
QtCore.QTimer.singleShot(1500, _install)
