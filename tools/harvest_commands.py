"""Pass B: the command registry. Needs a GUI, so it runs under Xvfb.

Gui.listCommands() returns bare strings -- there is no getCommandInfo and no
Python-visible listToolbars. Everything else comes off the QAction, and the
grouping comes from the toolbar or menu the action was placed in, which is
where FreeCAD already asserts what belongs with what.

    FCCLI_OUT=commands.json xvfb-run -a freecad tools/harvest_commands.py
"""

import json
import os
import re

import FreeCAD as App
import FreeCADGui as Gui

OUT = os.environ.get("FCCLI_OUT", "commands.json")
TAG = re.compile(r"<[^>]+>")


def clean(text):
    if not text:
        return ""
    text = TAG.sub("", text).replace("&amp;", "&").replace("&nbsp;", " ")
    return " ".join(text.split()).strip()


def group_of(act):
    getter = (getattr(act, "associatedObjects", None)
              or getattr(act, "associatedWidgets", None))
    if getter is None:
        return None, None
    toolbar = menu = None
    try:
        owners = list(getter())
    except Exception:
        return None, None
    for w in owners:
        cls = type(w).__name__
        if cls == "QToolBar" and toolbar is None:
            toolbar = w.windowTitle() or None
        elif cls == "QMenu" and menu is None:
            menu = (w.title() or "").replace("&", "") or None
    return toolbar, menu


def run():
    from PySide6 import QtCore, QtGui, QtWidgets

    workbenches, failed = [], {}
    for wb in sorted(Gui.listWorkbenches()):
        try:
            Gui.activateWorkbench(wb)
            workbenches.append(wb)
        except Exception as exc:
            failed[wb] = str(exc)[:90]

    mw = Gui.getMainWindow()
    actions = {}
    for act in mw.findChildren(QtGui.QAction):
        name = act.objectName()
        if name and name not in actions:
            actions[name] = act

    commands = {}
    for name in Gui.listCommands():
        act = actions.get(name)
        entry = {"name": name}
        if act is not None:
            toolbar, menu = group_of(act)
            entry.update({
                "label": clean(act.text()),
                "tooltip": clean(act.toolTip()),
                "status": clean(act.statusTip()),
                "shortcut": act.shortcut().toString() or None,
                "icon": not act.icon().isNull(),
                "toolbar": toolbar,
                "menu": menu,
            })
        commands[name] = entry

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"freecad": ".".join(App.Version()[:3]),
                   "workbenches": workbenches,
                   "workbench_failures": failed,
                   "commands": commands}, fh, indent=1, sort_keys=True)
    App.Console.PrintMessage(
        f"[harvest] {len(commands)} commands, {len(workbenches)} workbenches\n")
    QtCore.QTimer.singleShot(200, QtWidgets.QApplication.quit)


from PySide6 import QtCore  # noqa: E402
QtCore.QTimer.singleShot(9000, run)
