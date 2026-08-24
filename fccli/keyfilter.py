# SPDX-License-Identifier: LGPL-2.1-or-later

"""Application-level key usurping.

195 of FreeCAD's 940 default shortcuts are unmodified keys, so claiming bare
printables collides on purpose. Three rules keep the collision survivable:
a focus guard so real editors keep their keys, step-aware digit routing so
1-6 stay the standard views while nothing is running, and a passthrough
allowlist for the rest.
"""

from .qt import Qt, QtCore, QtGui, QtWidgets

EDITORS = (
    QtWidgets.QLineEdit,
    QtWidgets.QTextEdit,
    QtWidgets.QPlainTextEdit,
    QtWidgets.QAbstractSpinBox,   # covers Gui::QuantitySpinBox in Task panels
    QtWidgets.QComboBox,
)

NAV_KEYS = {
    Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
    Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown,
}

EDIT_KEYS = {Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Tab, Qt.Key_Backtab}

COMMIT_KEYS = {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape}

MODIFIER_ONLY = {
    Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta,
    Qt.Key_AltGr, Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock,
}

# Bare keys that keep native FreeCAD behaviour even while usurping is on.
DEFAULT_PASSTHROUGH = {Qt.Key_Space}

READLINE = {
    Qt.Key_A, Qt.Key_E, Qt.Key_K, Qt.Key_U, Qt.Key_W, Qt.Key_R,
}


class KeyFilter(QtCore.QObject):
    def __init__(self, target, engine, parent=None) -> None:
        super().__init__(parent)
        self.target = target          # the CLI input widget
        self.engine = engine
        self.enabled = True
        self.claim_readline = False   # Ctrl+A is Select All in FreeCAD
        self.passthrough = set(DEFAULT_PASSTHROUGH)
        self._forwarding = False
        self.stats = {"seen": 0, "usurped": 0, "passed": 0}

    # ------------------------------------------------------------ decision

    def _blocked(self) -> bool:
        app = QtWidgets.QApplication.instance()
        if app.activeModalWidget() or app.activePopupWidget():
            return True
        fw = app.focusWidget()
        if fw is self.target:
            return True                      # widget handles its own keys
        if isinstance(fw, EDITORS):
            return True                      # Python console, expression editor,
        return False                         # spreadsheet, property editor, ...

    def should_usurp(self, ev) -> bool:
        key, mods = ev.key(), ev.modifiers()

        if key in MODIFIER_ONLY:
            return False
        if mods & (Qt.AltModifier | Qt.MetaModifier):
            return False
        if Qt.Key_F1 <= key <= Qt.Key_F35:
            return False
        if key in self.passthrough and not (mods & Qt.ControlModifier):
            return False

        if mods & Qt.ControlModifier:
            return self.claim_readline and key in READLINE

        if Qt.Key_0 <= key <= Qt.Key_9:
            # Idle digits belong to FreeCAD: 0-6 are the standard views, and
            # no verb name starts with a digit.
            return self.engine.wants_numeric() or bool(self._pending_text())

        if key in COMMIT_KEYS:
            return self.engine.state != "idle" or bool(self._pending_text())
        if key in NAV_KEYS or key in EDIT_KEYS:
            return self.engine.state != "idle" or bool(self._pending_text())

        text = ev.text()
        return bool(text) and text.isprintable()

    def _pending_text(self) -> str:
        getter = getattr(self.target, "input_text", None)
        return getter() if callable(getter) else ""

    # -------------------------------------------------------------- filter

    def eventFilter(self, obj, ev):
        if self._forwarding:
            return False
        if ev.type() != QtCore.QEvent.KeyPress:
            return False
        if not self.enabled or self._blocked():
            return False

        self.stats["seen"] += 1
        if not self.should_usurp(ev):
            self.stats["passed"] += 1
            return False

        self.stats["usurped"] += 1
        self._forwarding = True
        try:
            if not self.target.hasFocus():
                self.target.setFocus(Qt.OtherFocusReason)
            fwd = QtGui.QKeyEvent(
                QtCore.QEvent.KeyPress, ev.key(), ev.modifiers(),
                ev.text(), ev.isAutoRepeat(), ev.count(),
            )
            QtWidgets.QApplication.sendEvent(self.target, fwd)
        finally:
            self._forwarding = False
        return True

    # -------------------------------------------------------------- wiring

    def install(self) -> None:
        QtWidgets.QApplication.instance().installEventFilter(self)

    def remove(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app:
            app.removeEventFilter(self)
