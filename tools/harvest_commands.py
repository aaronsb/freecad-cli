# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pass B: the command registry. Needs a GUI, so it runs under Xvfb.

Two sources, and neither answers everything.

A command's QAction is what the button says: rendered, with placeholders
substituted. `Gui.Command.get(name).getInfo()` is the registry's own
record -- the raw resource strings, and the only source at all for the 147
commands that have no QAction anywhere. Those are registered and runnable
and appear in no toolbar and no menu, which was measured rather than
assumed: none of the 147 is in any workbench's getToolbarItems() or in any
menu. They used to reach the descriptor carrying only a name, which slugged
into verbs like `arch_multimaterial` documented as "Arch_MultiMaterial".

So the choice is made per field rather than per source, because asking
"is there a QAction" in place of "does this field have a value" is what
went wrong twice:

    label       the action, else getInfo. getInfo's is the raw string and
                Std_About's is "About %1", which names a verb `about_1`.
                The action's text can be empty while getInfo has one --
                Std_WindowsMenu is "Activate Window" -- and gating the
                whole entry on the action left it bare.
    tooltip     getInfo, else the action's statusTip. act.toolTip() is
                rich text in three blocks, and clean() drops the tags with
                nothing between them, so 909 of these read
                "CubeCreates a solid cubePart_Box". That string is what
                build_command_verb hands to `man`.
    toolbar,    the action only. Placement is what it alone knows, and the
    menu, icon  icon question it alone can answer: getInfo carries a
                pixmap name, and a name being present is not the same as
                an icon resolving -- they disagree for 62 commands, all
                groups that declare no pixmap and inherit one from their
                first child when the UI is built.

whatsThis is harvested by getInfo and dropped: for all 147 it is the
command name again.

This file used to assert that getInfo did not exist, and that there was no
Python-visible listToolbars. Both were wrong. listToolbars, getToolbarItems
and listMenus are all there; group_of still reads placement off the action
because that covers every command that has any.

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


def unglue(text, name):
    """Take the command's own name back off the end of its rich tooltip.

    Only the last resort reaches here: nine BIM_Nudge commands carry no
    getInfo toolTip and no statusTip, so the rich-text action tooltip is
    all there is, and clean() runs its three blocks together --
    "Nudge Down (Ctrl+Down)BIM_Nudge_Down". Nothing should hand a reader
    documentation that ends in the thing it is documenting.
    """
    return text[:-len(name)].strip() if name and text.endswith(name) else text


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
        info = command_info(name)
        # Per field, not per action. "Has a QAction" was standing in for
        # "has a usable value" and the two are not the same: Std_WindowsMenu
        # has an action whose text() is empty and a getInfo menuText of
        # "Activate Window", so it stayed bare one branch over from the fix.
        #
        # The label comes off the action, which is what the button says --
        # rendered, with placeholders substituted. getInfo hands back the
        # raw resource string, and Std_About's is "About %1".
        #
        # The tooltip comes off getInfo, which is the plain sentence.
        # act.toolTip() is rich text -- title, sentence, command name in
        # three <p> blocks -- and clean() strips the tags without putting
        # anything between them, so 909 of these read
        # "CubeCreates a solid cubePart_Box". That string is what
        # build_command_verb hands to `man`.
        entry.update({
            "label": clean(act.text() if act else "")
                     or clean(info.get("menuText")),
            "tooltip": clean(info.get("toolTip"))
                       or clean(act.statusTip() if act else "")
                       or unglue(clean(act.toolTip() if act else ""), name),
            "status": clean(info.get("statusTip"))
                      or clean(act.statusTip() if act else ""),
            "shortcut": (act.shortcut().toString() if act else "")
                        or info.get("shortcut") or None,
        })
        if act is not None:
            toolbar, menu = group_of(act)
            # Whether an icon resolved, which only the action can answer.
            # getInfo carries a pixmap name, and a name being present is a
            # different question -- the two disagree for 62 commands, all
            # of them groups that declare no pixmap and inherit one from
            # their first child when the UI is built. Left absent rather
            # than answered wrongly.
            entry.update({"icon": not act.icon().isNull(),
                          "toolbar": toolbar, "menu": menu})
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
