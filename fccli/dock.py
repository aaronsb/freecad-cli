# SPDX-License-Identifier: LGPL-2.1-or-later

"""Assembly: dock widget, wiring, and the spike's control strip."""

from . import bus as _bus
from .actions import ActionBridge, ECHO, FOLLOW, GHOST, OFF, flash
from .engine import Engine
from .grammar import REGISTRY
from .keyfilter import KeyFilter
from .picking import make_picker
from .qt import Qt, QtCore, QtGui, QtWidgets
from .widget import Console

_INSTANCE = None

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/fccli"
DEFAULT_HEIGHT = 140

# Floating, the dock is a window and both axes are the user's to set. Docked,
# only height is -- width belongs to the dock row. The two are remembered
# separately: dragging a floating window tall should not leave a 600px strip
# across the top of FreeCAD the next time it is docked.
DEFAULT_FLOAT = (760, 340)
MIN_FLOAT = (320, 120)

FULL = "full"
PARTIAL = "partial"

# Full width gives the dock row the window corners, so it spans edge to edge.
# Partial hands the corners back to the left and right docks, leaving the row
# bounded by them and free to be shared with other docks dragged alongside.
CORNERS = {
    Qt.TopDockWidgetArea: (
        (Qt.TopLeftCorner, Qt.TopRightCorner),
        (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea),
    ),
    Qt.BottomDockWidgetArea: (
        (Qt.BottomLeftCorner, Qt.BottomRightCorner),
        (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea),
    ),
}


def saved_width_mode():
    try:
        return params().GetString("WidthMode", FULL) or FULL
    except Exception:
        return FULL


def params():
    import FreeCAD as App
    return App.ParamGet(PARAM_PATH)


def saved_height():
    try:
        return max(70, params().GetInt("DockHeight", DEFAULT_HEIGHT))
    except Exception:
        return DEFAULT_HEIGHT


def saved_float_size():
    try:
        return (max(MIN_FLOAT[0], params().GetInt("FloatWidth", DEFAULT_FLOAT[0])),
                max(MIN_FLOAT[1], params().GetInt("FloatHeight", DEFAULT_FLOAT[1])))
    except Exception:
        return DEFAULT_FLOAT

def _load_factory():
    """Generate verbs from the descriptor, if one was shipped."""
    try:
        from .factory import register_all
        return register_all(REGISTRY)
    except Exception as exc:
        import FreeCAD as App
        App.Console.PrintWarning(f"[fccli] factory: {exc}\n")
        return {"error": str(exc)}


def _banner(counts):
    from .build_info import describe
    n = (counts or {}).get("total", 0)
    return (f"FreeCAD CLI {describe()} -- {n} commands. "
            "Type man for the list, or click in the viewport.")




class _Squeezable(QtWidgets.QWidget):
    """A widget that reports no minimum width of its own.

    A layout makes its widget at least as wide as the sum of its children,
    and Qt reads that back through minimumSizeHint no matter what
    constraint the layout is set to. That floor propagates to the dock, so
    the row of combo boxes decides how narrow a floating command line may
    be. Reporting zero hands the decision back to the dock, which clips the
    row rather than refusing to shrink.
    """

    def minimumSizeHint(self):
        return QtCore.QSize(0, super().minimumSizeHint().height())


class CliDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Command Line", parent)
        self.setObjectName("FreeCADCliDock")

        self.bus = _bus.Bus()
        # Hand-written verbs register first so the factory's generated ones
        # never shadow them: tier 0 only claims names nobody has taken.
        import fccli.verbs  # noqa: F401
        from .dirty import install as install_dirty
        install_dirty()
        from .shell import load_aliases
        self.alias_count = load_aliases()
        self.server = None
        self._applying_remote = False
        self.factory_counts = _load_factory()
        self.picker = make_picker("snap", notify=self._notify)
        self.engine = Engine(self.bus, REGISTRY, picker=self.picker)
        from .session import Session
        self.session = Session(self.engine, self.bus)
        self.console = Console(self.engine, session=self.session)
        self.bridge = ActionBridge(self.engine, self.console, REGISTRY, self)
        self.keyfilter = KeyFilter(self.console, self.engine, self)

        self.setWidget(self._build(self.console))
        self.bus.subscribe(self._on_message)
        self.console.submitted.connect(self.session.submit)
        self.console.inputEdited.connect(self._push_buffer)
        self.console.cancelled.connect(self.engine.cancel)
        self.console.write(_banner(self.factory_counts), "info")
        if (self.factory_counts or {}).get("error"):
            self.console.write("  " + self.factory_counts["error"], "info")

        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetClosable
        )
        self.persist = True             # write geometry back to preferences
        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_geometry)
        self.topLevelChanged.connect(self._on_float_changed)

    # --------------------------------------------------------------- build

    def _build(self, console):
        body = _Squeezable(self)
        lay = QtWidgets.QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # The scrollback absorbs every pixel the user drags in; the control
        # strip keeps its own height.
        console.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                              QtWidgets.QSizePolicy.Expanding)
        console.setMinimumHeight(40)
        strip = self._strip(body)
        strip.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                            QtWidgets.QSizePolicy.Fixed)

        # Without this the row of combo boxes sets a floor for the whole
        # dock, and a floating window cannot be dragged narrower than the
        # strip is wide. Clipping the strip is the better trade: the
        # scrollback is what somebody is resizing to see.
        lay.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)
        strip.setMinimumWidth(0)

        lay.addWidget(console, 1)
        lay.addWidget(strip, 0)
        body.setMinimumHeight(70)
        body.setMaximumHeight(16777215)
        body.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                           QtWidgets.QSizePolicy.Expanding)
        return body

    def _strip(self, parent):
        strip = _Squeezable(parent)
        row = QtWidgets.QHBoxLayout(strip)
        row.setContentsMargins(6, 2, 6, 2)
        # A layout normally makes its widget at least as wide as the sum of
        # its children, and that floor propagates all the way up to the
        # dock: a floating command line could not be dragged narrower than
        # this row of combo boxes. Releasing it lets the row clip from the
        # right -- the stretch goes first, then the status label -- while
        # the scrollback keeps whatever width is left.
        row.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)

        self.usurp_box = QtWidgets.QCheckBox("usurp keys", strip)
        self.usurp_box.setChecked(True)
        self.usurp_box.setToolTip(
            "Route bare printable keys to the command line. Digits stay with "
            "FreeCAD while no getter is open."
        )
        self.usurp_box.toggled.connect(self._set_usurp)

        self.mode_box = QtWidgets.QComboBox(strip)
        self.mode_box.addItems([ECHO, GHOST, FOLLOW, OFF])
        self.mode_box.setToolTip("What a toolbar click does to the command line")
        self.mode_box.currentTextChanged.connect(self._set_mode)

        self.width_box = QtWidgets.QComboBox(strip)
        self.width_box.addItems([FULL, PARTIAL])
        self.width_box.setCurrentText(saved_width_mode())
        self.width_box.setToolTip(
            "full: the row spans the window.\n"
            "partial: the left and right docks keep the corners, so other "
            "docks can share the row."
        )
        self.width_box.currentTextChanged.connect(self._set_width_mode)

        self.pick_box = QtWidgets.QComboBox(strip)
        self.pick_box.addItems(["snap", "getpoint", "raw"])
        self.pick_box.setToolTip("Picking backend")
        self.pick_box.currentTextChanged.connect(self._set_picker)

        self.status = QtWidgets.QLabel("idle", strip)
        self.status.setStyleSheet("color:#808080;")

        row.addWidget(self.usurp_box)
        row.addWidget(QtWidgets.QLabel("gui:", strip))
        row.addWidget(self.mode_box)
        row.addWidget(QtWidgets.QLabel("pick:", strip))
        row.addWidget(self.pick_box)
        row.addWidget(QtWidgets.QLabel("width:", strip))
        row.addWidget(self.width_box)
        row.addStretch(1)
        row.addWidget(self.status)
        return strip

    # ------------------------------------------------------------ settings

    def _set_usurp(self, on):
        self.keyfilter.enabled = bool(on)
        self._paint_focus_state()

    def _set_mode(self, mode):
        self.bridge.mode = mode

    def _set_width_mode(self, mode):
        import FreeCADGui as Gui
        mw = Gui.getMainWindow()
        if mw is None:
            return
        area = mw.dockWidgetArea(self)
        if area not in CORNERS:
            area = DEFAULT_AREA
        apply_width_mode(mw, area, mode)
        try:
            params().SetString("WidthMode", mode)
        except Exception:
            pass
        # Nudge the layout so the corner change takes effect now.
        mw.addDockWidget(area, self, Qt.Vertical)
        self.show()
        QtCore.QTimer.singleShot(0, lambda: _resize(mw, self))

    def _push_buffer(self, text=None):
        """Tell the session what is being typed here.

        Only a person editing the input line reaches this. Rendering a
        client's command is not typing, and claiming the floor for it would
        lock every other client out of a session nobody is using.
        """
        if self._applying_remote:
            return
        from .session import DOCK
        self.session.set_buffer(
            DOCK, self.console.input_text() if text is None else text)

    def _on_buffer(self, msg):
        """Somebody else is typing. Show it, and stop taking keys."""
        from .session import DOCK
        if msg.data.get("who") == DOCK:
            return
        self._applying_remote = True
        try:
            self.console.set_input(msg.text)
        finally:
            self._applying_remote = False
        self._paint_focus_state()

    def _notify(self, text):
        self.bus.emit(_bus.INFO, text)

    def _set_picker(self, kind):
        self.picker.stop()
        self.picker = make_picker(kind, notify=self._notify)
        self.engine.picker = self.picker

    # ------------------------------------------------------------ messages

    def _on_message(self, msg):
        if msg.kind == _bus.PROMPT:
            self._on_prompt(msg)
        elif msg.kind == _bus.BUFFER:
            self._on_buffer(msg)
        elif msg.kind == _bus.CLEAR:
            self.console.clear_scrollback()
        elif msg.kind == _bus.LIVE:
            self.console.write_live("  " + msg.text, "echo")
        elif msg.kind == _bus.ECHO:
            self.console.write("  " + msg.text, "echo")
        elif msg.kind == _bus.ERROR:
            self.console.write("  ! " + msg.text, "error")
        elif msg.kind == _bus.INFO:
            self.console.end_live()
            if msg.text.startswith("@@history@@"):
                tail = msg.text[len("@@history@@"):]
                self._show_history(int(tail) if tail.isdigit() else 40)
            else:
                self.console.write("  " + msg.text,
                                   msg.data.get("role", "info"))
        elif msg.kind == _bus.RESULT:
            self.console.end_live("  " + msg.text, "result")
            verb = REGISTRY.get(msg.data.get("verb", ""))
            if verb and verb.gui_command:
                flash(verb.gui_command)

    def _on_prompt(self, msg):
        if msg.data.get("idle"):
            self.console.set_prompt("> ")
            self.status.setText("idle")
        else:
            opts = msg.data.get("options") or []
            tail = f" [{'/'.join(opts)}]" if opts else ""
            self.console.set_prompt(f"{msg.text}{tail}: ")
            self.status.setText(
                f"{self.engine.verb.name} · step "
                f"{self.engine.step_index + 1}/{len(self.engine.verb.steps)}"
            )
        self._paint_focus_state()

    def _show_history(self, limit=40):
        ring = self.session.history.tail(limit)
        if not ring:
            self.console.write("  (no history yet)", "info")
            return
        start = len(self.console._history) - len(ring) + 1
        for i, line in enumerate(ring, start):
            self.console.write(f"  {i:>4}  {line}", "info")

    # Where typed keys would land right now. The socket adds "observing";
    # the rest exist today.
    STATE_STYLE = {
        "usurping":     ("#4ec9b0", "#d4d4d4", ""),
        "click to type": ("#3a3a3a", "#8a8a8a", "click to type"),
        "blocked":      ("#5a4a2a", "#7a7060", "blocked"),
        "observing":    ("#3a3a3a", "#7a7a7a", "observing"),
    }

    def input_state(self):
        """Whether keys typed anywhere would reach this widget."""
        from .session import DOCK
        app = QtWidgets.QApplication.instance()
        if app is not None and app.activeModalWidget():
            return "blocked", self._dialog_name()
        holder = self.session.floor.holder
        if holder is not None and holder != DOCK:
            return "observing", holder
        if self.keyfilter.enabled:
            return "usurping", ""
        if self.console.hasFocus():
            return "usurping", ""
        return "click to type", ""

    def _dialog_name(self):
        try:
            import FreeCADGui as Gui
            dialog = Gui.Control.activeDialog()
        except Exception:
            dialog = None
        return "task panel" if dialog else "dialog"

    def _paint_focus_state(self):
        state, detail = self.input_state()
        border, text, label = self.STATE_STYLE.get(
            state, self.STATE_STYLE["usurping"])
        self.console.setStyleSheet(
            f"QPlainTextEdit {{ background:#1e1e1e; color:{text};"
            " selection-background-color:#264f78;"
            f" border:1px solid {border}; }}"
        )
        if label:
            shown = f"{label}: {detail}" if detail else label
            self.status.setText(shown)
            self.status.setStyleSheet("color:#8a8a8a;")
        elif self.engine.state == "idle":
            self.status.setText("idle")
            self.status.setStyleSheet("color:#808080;")

    # ------------------------------------------------------------- geometry

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "_save_timer", None) is not None:
            self._save_timer.start()

    def _save_geometry(self):
        """Remember the size, under the key for the state it was set in.

        `persist` is the off switch. A test run shows a real dock in a
        window whose shape it did not choose, and saving that would replace
        a height somebody had dragged to. Stopping the debounce timer is
        not enough -- a later relayout restarts it.
        """
        if not self.persist:
            return
        try:
            if self.isFloating():
                params().SetInt("FloatWidth", max(MIN_FLOAT[0], self.width()))
                params().SetInt("FloatHeight", max(MIN_FLOAT[1], self.height()))
            else:
                params().SetInt("DockHeight", max(70, self.height()))
        except Exception:
            pass

    def _on_float_changed(self, floating):
        """Restore whichever size belongs to the state just entered.

        Qt hands a newly floated dock whatever size it had in the row, which
        for a full-width strip is the width of the window and 140 pixels of
        height -- a shape nobody wants as a window. Re-docking has the
        mirror problem.
        """
        if floating:
            width, height = saved_float_size()
            self.resize(width, height)
            return
        import FreeCADGui as Gui
        mw = Gui.getMainWindow()
        if mw is not None:
            QtCore.QTimer.singleShot(0, lambda: _resize(mw, self))

    def sizeHint(self):
        base = super().sizeHint()
        if self.isFloating():
            return QtCore.QSize(*saved_float_size())
        return QtCore.QSize(base.width(), saved_height())

    def minimumSizeHint(self):
        """Let a floating window be dragged genuinely small.

        The control strip is a row of labelled combo boxes, and its own
        minimum would otherwise be the floor for the whole dock -- wide
        enough that a floating command line could not be tucked into a
        corner of the screen.
        """
        base = super().minimumSizeHint()
        if self.isFloating():
            return QtCore.QSize(min(base.width(), MIN_FLOAT[0]),
                                min(base.height(), MIN_FLOAT[1]))
        return base

    # ------------------------------------------------------------ lifecycle

    def activate(self):
        self.keyfilter.install()
        self.bridge.install()
        self._serve()
        app = QtWidgets.QApplication.instance()
        self._focus_hook = None
        if app is not None:
            self._focus_hook = lambda *_: self._paint_focus_state()
            app.focusChanged.connect(self._focus_hook)
        self.console.setFocus(Qt.OtherFocusReason)
        self._paint_focus_state()

    def _serve(self):
        """Open the socket, so a terminal can reach this same session."""
        try:
            from .server import Server
            self.server = Server(self.session, self)
            path = self.server.start()
            if path:
                import FreeCAD as App
                App.Console.PrintMessage(f"[fccli] listening on {path}\n")
        except Exception as exc:
            import FreeCAD as App
            App.Console.PrintWarning(f"[fccli] socket: {exc}\n")
            self.server = None
        self._applying_remote = False

    def closeEvent(self, ev):
        self.keyfilter.remove()
        self.picker.stop()
        # This handler is on the QApplication and holds the dock, so every
        # open/close cycle used to leave another one behind, painting a
        # window that had gone away.
        if getattr(self, "_focus_hook", None) is not None:
            try:
                QtWidgets.QApplication.instance().focusChanged.disconnect(
                    self._focus_hook)
            except (RuntimeError, TypeError):
                pass
            self._focus_hook = None
        if self.server is not None:
            self.server.stop()
        super().closeEvent(ev)


DEFAULT_AREA = Qt.TopDockWidgetArea


def show(area=None):
    """Create the dock, or raise it if it already exists.

    Default home is the top dock area: a full-width strip between the
    toolbars and the 3D view.
    The bottom area is shared with the Report View and the Python console,
    so a dock added there gets a narrow column rather than a strip.
    """
    global _INSTANCE
    import FreeCADGui as Gui
    mw = Gui.getMainWindow()
    if mw is None:
        return None
    if _INSTANCE is None:
        _INSTANCE = CliDock(mw)
        _INSTANCE.setAllowedAreas(
            Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        _place(mw, _INSTANCE, area or DEFAULT_AREA)
        _INSTANCE.activate()
    _INSTANCE.show()
    _INSTANCE.raise_()
    _INSTANCE.console.setFocus(Qt.OtherFocusReason)
    return _INSTANCE


def _place(mw, dock, area, mode=None):
    apply_width_mode(mw, area, mode or saved_width_mode())
    # Qt.Vertical stacks the dock in its own row rather than splitting the
    # row that Report View already occupies.
    mw.addDockWidget(area, dock, Qt.Vertical)
    QtCore.QTimer.singleShot(0, lambda: _resize(mw, dock))


def apply_width_mode(mw, area, mode):
    corners, neighbours = CORNERS[area]
    for corner, neighbour in zip(corners, neighbours):
        mw.setCorner(corner, area if mode == FULL else neighbour)


def _resize(mw, dock):
    """Restore the height the user last dragged to."""
    try:
        mw.resizeDocks([dock], [saved_height()], Qt.Vertical)
    except Exception:
        pass


def move_to(area):
    """Relocate an existing dock between the top and bottom edges."""
    import FreeCADGui as Gui
    if _INSTANCE is None:
        return
    mw = Gui.getMainWindow()
    if mw is not None:
        _place(mw, _INSTANCE, area)
        _INSTANCE.show()


def instance():
    return _INSTANCE
