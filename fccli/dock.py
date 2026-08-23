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

def _load_factory():
    """Generate verbs from the descriptor, if one was shipped."""
    try:
        from .factory import register_all
        return register_all(REGISTRY)
    except Exception as exc:
        import FreeCAD as App
        App.Console.PrintWarning(f"[fccli] factory: {exc}\n")
        return {"error": str(exc)}


BANNER = (
    "FreeCAD CLI spike -- type a verb, or click in the viewport.\n"
    "  verbs: line polyline circle box move point   (Tab completes, "
    "Up recalls, Esc cancels)\n"
)


class CliDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Command Line", parent)
        self.setObjectName("FreeCADCliDock")

        self.bus = _bus.Bus()
        # Hand-written verbs register first so the factory's generated ones
        # never shadow them: tier 0 only claims names nobody has taken.
        import fccli.verbs  # noqa: F401
        self.factory_counts = _load_factory()
        self.picker = make_picker("snap", notify=self._notify)
        self.engine = Engine(self.bus, REGISTRY, picker=self.picker)
        self.console = Console(self.engine)
        self.bridge = ActionBridge(self.engine, self.console, REGISTRY, self)
        self.keyfilter = KeyFilter(self.console, self.engine, self)

        self.setWidget(self._build(self.console))
        self.bus.subscribe(self._on_message)
        self.console.submitted.connect(self.engine.submit)
        self.console.cancelled.connect(self.engine.cancel)
        self.console.write(BANNER.rstrip(), "info")
        c = self.factory_counts or {}
        if c.get("error"):
            self.console.write("  " + c["error"], "info")
        else:
            self.console.write(
                f"  {c.get('total', 0)} verbs   "
                f"{c.get('patched', 0)} patched · "
                f"{c.get('tier1', 0)} generated · "
                f"{c.get('tier0', 0)} commands", "info")

        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetClosable
        )
        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_height)

    # --------------------------------------------------------------- build

    def _build(self, console):
        body = QtWidgets.QWidget(self)
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

        lay.addWidget(console, 1)
        lay.addWidget(strip, 0)
        body.setMinimumHeight(70)
        body.setMaximumHeight(16777215)
        body.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                           QtWidgets.QSizePolicy.Expanding)
        return body

    def _strip(self, parent):
        strip = QtWidgets.QWidget(parent)
        row = QtWidgets.QHBoxLayout(strip)
        row.setContentsMargins(6, 2, 6, 2)

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
            self.console.write("  " + msg.text, "info")
        elif msg.kind == _bus.RESULT:
            self.console.end_live("  " + msg.text, "result")
            self.console.commit_history(msg.data.get("replay", msg.text))
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

    def _paint_focus_state(self):
        border = "#4ec9b0" if self.keyfilter.enabled else "#333"
        self.console.setStyleSheet(
            "QPlainTextEdit { background:#1e1e1e; color:#d4d4d4;"
            " selection-background-color:#264f78;"
            f" border:1px solid {border}; }}"
        )

    # ------------------------------------------------------------- geometry

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "_save_timer", None) is not None:
            self._save_timer.start()

    def _save_height(self):
        try:
            params().SetInt("DockHeight", max(70, self.height()))
        except Exception:
            pass

    def sizeHint(self):
        base = super().sizeHint()
        return QtCore.QSize(base.width(), saved_height())

    # ------------------------------------------------------------ lifecycle

    def activate(self):
        self.keyfilter.install()
        self.bridge.install()
        self.console.setFocus(Qt.OtherFocusReason)

    def closeEvent(self, ev):
        self.keyfilter.remove()
        self.picker.stop()
        super().closeEvent(ev)


DEFAULT_AREA = Qt.TopDockWidgetArea


def show(area=None):
    """Create the dock, or raise it if it already exists.

    Default home is the top dock area: a full-width strip between the
    toolbars and the 3D view, which is where Rhino puts its command line.
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
