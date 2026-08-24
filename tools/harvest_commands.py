# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pass B: the command registry. Needs a GUI, so it runs under Xvfb.

Gui.listCommands() returns bare strings -- there is no getCommandInfo and no
Python-visible listToolbars. Everything else comes off the QAction, and the
grouping comes from the toolbar or menu the action was placed in, which is
where FreeCAD already asserts what belongs with what.

    FCCLI_OUT=commands.json QT_QPA_PLATFORM=xcb \
        xvfb-run -a freecad tools/harvest_commands.py

Qt6 picks its platform from XDG_SESSION_TYPE, so on a Wayland session
xvfb-run's display goes unused and this opens on the operator's screen.
tools/generate_descriptor.py pins it; a hand run has to as well.
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

    # Which workbench brings which command. A workbench registers its own
    # commands the first time it is activated, so a running FreeCAD that
    # has never opened BIM does not have Arch_Grid -- and the descriptor,
    # harvested with everything activated, does. Without this the command
    # line could say a command was not loaded and not say what would load
    # it, which is advice nobody can act on.
    workbenches, failed, owner = [], {}, {}
    known = set(Gui.listCommands())      # always there, before any workbench
    for wb in sorted(Gui.listWorkbenches()):
        try:
            Gui.activateWorkbench(wb)
            workbenches.append(wb)
        except Exception as exc:
            failed[wb] = str(exc)[:90]
            continue
        now = set(Gui.listCommands())
        for name in now - known:
            owner[name] = wb
        known = now

    # A command is credited to whichever workbench happened to be
    # activated first, and BIM sorts before Draft while bringing Draft's
    # commands along -- so Draft_Line was attributed to BIM, which is true
    # and is not what anybody would say. Where a workbench is named after
    # the command's own stem, that is the one to name.
    by_name = {w.lower(): w for w in workbenches}
    for name in list(owner):
        stem = name.split("_", 1)[0].lower()
        better = by_name.get(stem + "workbench") or by_name.get(stem)
        if better:
            owner[name] = better

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
        if name in owner:
            entry["workbench"] = owner[name]
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
