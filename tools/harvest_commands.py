# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pass B: the command registry. Needs a GUI, so it runs under Xvfb.

Most of it comes off the QAction: that is the rendered name, translated and
with its placeholders substituted, and the toolbar or menu it was placed in
is where FreeCAD already asserts what belongs with what.

148 commands have no QAction anywhere. They are registered and runnable and
never appear in any bar, so the walk below found nothing for them and they
went into the descriptor carrying only a name -- which then slugged into
verbs like `arch_multimaterial` with a doc that echoed the command name
back. `Gui.Command.get(name).getInfo()` has had their menuText and toolTip
all along; this file previously asserted that no such call existed.

It fills in behind the QAction rather than replacing it, because the two
disagree and the QAction is the better of the two where it exists. getInfo
hands back the raw resource string: Std_About's is "About %1", which would
have named the verb `about_1`.

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


def command_info(name):
    """What FreeCAD's command registry says, for a command with no QAction.

    Returns menuText, toolTip, whatsThis, statusTip, pixmap and shortcut.
    Empty dict rather than raising, so one unreadable command does not cost
    the harvest the other thousand.
    """
    try:
        command = Gui.Command.get(name)
        return (command.getInfo() if command else None) or {}
    except Exception:
        return {}


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
        else:
            info = command_info(name)
            entry.update({
                "label": clean(info.get("menuText")),
                "tooltip": clean(info.get("toolTip")),
                "status": clean(info.get("statusTip")),
                "shortcut": info.get("shortcut") or None,
                "icon": bool(info.get("pixmap")),
                "toolbar": None,
                "menu": None,
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
