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
        import fccli.verbs  # noqa: F401  -- registers the seed verbs
        self.picker = make_picker("snapper")
        self.engine = Engine(self.bus, REGISTRY, picker=self.picker)
        self.console = Console(self.engine)
        self.bridge = ActionBridge(self.engine, self.console, REGISTRY, self)
        self.keyfilter = KeyFilter(self.console, self.engine, self)

        self.setWidget(self._build(self.console))
        self.bus.subscribe(self._on_message)
        self.console.submitted.connect(self.engine.submit)
        self.console.cancelled.connect(self.engine.cancel)
        self.console.write(BANNER.rstrip(), "info")

    # --------------------------------------------------------------- build

    def _build(self, console):
        body = QtWidgets.QWidget(self)
        lay = QtWidgets.QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(console)
        lay.addWidget(self._strip(body))
        body.setMinimumHeight(140)
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

        self.pick_box = QtWidgets.QComboBox(strip)
        self.pick_box.addItems(["snapper", "raw"])
        self.pick_box.setToolTip("Picking backend")
        self.pick_box.currentTextChanged.connect(self._set_picker)

        self.status = QtWidgets.QLabel("idle", strip)
        self.status.setStyleSheet("color:#808080;")

        row.addWidget(self.usurp_box)
        row.addWidget(QtWidgets.QLabel("gui:", strip))
        row.addWidget(self.mode_box)
        row.addWidget(QtWidgets.QLabel("pick:", strip))
        row.addWidget(self.pick_box)
        row.addStretch(1)
        row.addWidget(self.status)
        return strip

    # ------------------------------------------------------------ settings

    def _set_usurp(self, on):
        self.keyfilter.enabled = bool(on)
        self._paint_focus_state()

    def _set_mode(self, mode):
        self.bridge.mode = mode

    def _set_picker(self, kind):
        self.picker.stop()
        self.picker = make_picker(kind)
        self.engine.picker = self.picker

    # ------------------------------------------------------------ messages

    def _on_message(self, msg):
        if msg.kind == _bus.PROMPT:
            self._on_prompt(msg)
        elif msg.kind == _bus.ECHO:
            self.console.write("  " + msg.text, "echo")
        elif msg.kind == _bus.ERROR:
            self.console.write("  ! " + msg.text, "error")
        elif msg.kind == _bus.INFO:
            self.console.write("  " + msg.text, "info")
        elif msg.kind == _bus.RESULT:
            self.console.write("  = " + msg.text, "result")
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

    # ------------------------------------------------------------ lifecycle

    def activate(self):
        self.keyfilter.install()
        self.bridge.install()
        self.console.setFocus(Qt.OtherFocusReason)

    def closeEvent(self, ev):
        self.keyfilter.remove()
        self.picker.stop()
        super().closeEvent(ev)


def show():
    """Create the dock, or raise it if it already exists."""
    global _INSTANCE
    import FreeCADGui as Gui
    mw = Gui.getMainWindow()
    if mw is None:
        return None
    if _INSTANCE is None:
        _INSTANCE = CliDock(mw)
        mw.addDockWidget(Qt.BottomDockWidgetArea, _INSTANCE)
        _INSTANCE.activate()
    _INSTANCE.show()
    _INSTANCE.raise_()
    _INSTANCE.console.setFocus(Qt.OtherFocusReason)
    return _INSTANCE


def instance():
    return _INSTANCE
