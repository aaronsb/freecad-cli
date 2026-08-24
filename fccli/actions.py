# SPDX-License-Identifier: LGPL-2.1-or-later

"""GUI invocations, echoed into the command line.

FreeCAD exposes no command observer -- libFreeCADGui.so has
addDocumentObserver and addWorkbenchManipulator and nothing for commands.
QAction is the hook instead, and it is the better one: toolbar click, menu
pick, and keyboard shortcut all route through the same action, so one
connection covers all three.

Three behaviours, in rising order of risk:

    echo    log the verb into scrollback after the fact
    ghost   pre-fill the input line, uncommitted, editable
    follow  swallow the trigger and open the grammar instead
"""

from . import curation as _curation
from . import frecency as _frecency
from .qt import QtCore, QtGui, QtWidgets

ECHO = "echo"
GHOST = "ghost"
FOLLOW = "follow"
OFF = "off"


class ActionBridge(QtCore.QObject):
    def __init__(self, engine, console, registry, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.console = console
        self.registry = registry
        self.mode = ECHO
        self.disabled_verbs = set()     # per-verb kill switch for follow
        self.cue = True                 # show neighbours for unfamiliar verbs
        self._connected = {}

    # ------------------------------------------------------------ scanning

    def scan(self):
        """(Re)connect to every QAction. Actions appear lazily per workbench."""
        import FreeCADGui as Gui
        mw = Gui.getMainWindow()
        if mw is None:
            return 0
        added = 0
        for act in mw.findChildren(QtGui.QAction):
            name = act.objectName()
            if not name or name in self._connected:
                continue
            act.triggered.connect(
                lambda checked=False, n=name: self._on_trigger(n))
            self._connected[name] = act
            added += 1
        return added

    def install(self):
        import FreeCADGui as Gui
        self.scan()
        mw = Gui.getMainWindow()
        if mw is not None:
            # Workbench switches create new actions; rescan when the
            # workbench selector changes.
            for combo in mw.findChildren(QtWidgets.QComboBox):
                if combo.objectName() == "WbSelector":
                    combo.currentIndexChanged.connect(lambda *_: self.scan())

    # ---------------------------------------------------------------- cue

    # How many times somebody has to run a command before the neighbours
    # stop being news.
    CUE_UNTIL = 5

    def _familiar(self, verb):
        """Whether this operator has used a verb enough to know its corner."""
        session = getattr(self.console, "session", None)
        history = getattr(session, "history", None)
        if history is None:
            return False
        count, _ = history.tally().get(verb.name, (0, 0))
        return count >= self.CUE_UNTIL

    def _suggest(self, verb):
        """What else is on the toolbar this button came from.

        Clicking is how somebody explores, so it is the moment the rest of
        the group is worth naming. It stops once they have used the command
        enough times to have found the group themselves -- a cue that never
        goes away is a status bar, and gets read as furniture.
        """
        if not self.cue or verb is None or self._familiar(verb):
            return
        near = _curation.current().neighbours(self.registry, verb, limit=5)
        if near:
            self.console.write(f"  also here: {', '.join(near)}", "quiet")

    # ------------------------------------------------------------ dispatch

    def _on_trigger(self, command_name):
        if self.mode == OFF:
            return
        verb = self.registry.by_gui_command(command_name)
        label = verb.name if verb else command_name
        alias = f"  ({verb.aliases[0]})" if verb and verb.aliases else ""

        if self.mode == ECHO or verb is None:
            self.console.write(f"> {label}{alias}", "echo")
            self._suggest(verb)
            return
        if self.mode == GHOST:
            self.console.set_input(label + " ")
            self._suggest(verb)
            return
        if self.mode == FOLLOW:
            if verb.name in self.disabled_verbs:
                self.console.write(f"> {label}{alias}", "echo")
                return
            self.engine.submit(verb.name)


def flash(command_name):
    """Reverse direction: highlight the toolbar button a CLI verb maps to."""
    import FreeCADGui as Gui
    mw = Gui.getMainWindow()
    if mw is None or not command_name:
        return
    for act in mw.findChildren(QtGui.QAction):
        if act.objectName() != command_name:
            continue
        for w in act.associatedObjects() if hasattr(act, "associatedObjects") \
                else act.associatedWidgets():
            if not isinstance(w, QtWidgets.QWidget):
                continue
            base = w.styleSheet()
            w.setStyleSheet(base + "\nQToolButton { background: #dcdcaa; }")
            QtCore.QTimer.singleShot(350, lambda w=w, b=base: w.setStyleSheet(b))
        return
