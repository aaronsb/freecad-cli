# SPDX-License-Identifier: LGPL-2.1-or-later

"""FreeCAD's modal dialogs, read on the command line.

A GUI rejects a malformed request by putting a message box in front of
someone. A command line has nobody in front of it, so the box waits for a
click that never comes and the caller waits with it: ``fccli exec
'revolve'`` on a solid hung until the instance was killed, while the same
instance went on answering every other request.

A dialog already says what it is, so nothing here is written per command:

    one button, AcceptRole      a rejection -- text to print, nothing to
                                decide. "Select a shape for revolution."
    several buttons             a question. The ButtonRoles say which
                                answer is which.

Roles, never button text: the text is translated and the roles are not.
DestructiveRole is the answer ``!`` already means -- ``close!`` discards --
so a question is refused unless the line carried the bang, and then the
destructive answer is the one it asked for.

Armed only around a verb's own emit. A dialog someone raised by clicking a
toolbar never passes through here, and stays a dialog.
"""

import contextlib

from .qt import QtCore, QtWidgets


# PySide6 scopes its enums; older bindings expose the short name.
_SHOW = getattr(QtCore.QEvent, "Type", QtCore.QEvent).Show


def _role(name):
    """The role's short name, whatever Qt binding spells it."""
    return str(name).rsplit(".", 1)[-1]


class Caught:
    """What the dialogs raised during one emit said."""

    def __init__(self):
        self.faults = []     # rejections: text meant for the operator
        self.questions = []  # (text, [option names]) we declined to answer

    @property
    def fault(self):
        if self.faults:
            return " -- ".join(self.faults)
        if self.questions:
            text, options, undoable = self.questions[0]
            answer = (f" Re-run with ! for {undoable}." if undoable else "")
            return (f"{text} -- cancelled: FreeCAD wanted one of "
                    f"{', '.join(options)}, and a command line has nobody to "
                    f"ask mid-command.{answer}")
        return None

    def __bool__(self):
        return bool(self.faults or self.questions)


def read(dialog):
    """Everything a dialog says about itself, and the ways out of it."""
    buttons = []
    if isinstance(dialog, QtWidgets.QFileDialog):
        # Scraping a file chooser's labels yields "File name:" and "Files of
        # type:", which tells nobody anything. It has one useful answer.
        return ("this command wants a file chooser, which the command line "
                "cannot answer -- give the path as an argument instead",
                [(dialog, "RejectRole")])
    if isinstance(dialog, QtWidgets.QMessageBox):
        text = dialog.text()
        extra = dialog.informativeText()
        for b in dialog.buttons():
            buttons.append((b, _role(dialog.buttonRole(b))))
    else:
        box = dialog.findChild(QtWidgets.QDialogButtonBox)
        if box is None:
            return None
        labels = [w.text() for w in dialog.findChildren(QtWidgets.QLabel)
                  if w.isVisible() and w.text()]
        text, extra = " ".join(labels[:2]), ""
        for b in box.buttons():
            buttons.append((b, _role(box.buttonRole(b))))
    if not buttons:
        return None
    return _phrase(dialog.windowTitle(), text, extra), buttons


LIMIT = 240


def _phrase(*parts):
    """A dialog's words as one line.

    Qt spreads one sentence over a title, a body and an informative line,
    and repeats itself between them often enough to be worth folding.
    """
    kept = []
    for part in parts:
        part = " ".join((part or "").split())
        if part and not any(part in seen or seen in part for seen in kept):
            kept.append(part)
    line = " -- ".join(kept)
    return line if len(line) <= LIMIT else line[:LIMIT - 1].rstrip() + "\u2026"


def _pick(buttons, force):
    """Which button the command line presses, and why.

    Reject by default: cancelling is the answer that cannot lose anybody's
    work. The bang is what asks for the other one, the same way close! does.
    """
    by_role = {}
    for b, role in buttons:
        by_role.setdefault(role, b)
    if force and "DestructiveRole" in by_role:
        return by_role["DestructiveRole"]
    for role in ("RejectRole", "NoRole", "DestructiveRole", "AcceptRole",
                 "YesRole"):
        if role in by_role:
            return by_role[role]
    return buttons[0][0]


HANDLED = "_fccli_answered"


def _click(widget):
    """Press it, unless it is already gone."""
    try:
        (widget.reject if isinstance(widget, QtWidgets.QFileDialog)
         else widget.click)()
    except RuntimeError:
        pass          # the dialog went away before the loop came back round


class _Filter(QtCore.QObject):
    """Catches a modal as it is shown, reads it, and answers it."""

    def __init__(self, caught, force):
        super().__init__()
        self.caught = caught
        self.force = force

    def eventFilter(self, obj, event):
        if event.type() != _SHOW:
            return False
        if not isinstance(obj, QtWidgets.QDialog) or not obj.isModal():
            return False
        # Marked on the dialog rather than remembered here. A Show event
        # arrives again every time a dialog is hidden and reshown, and a
        # verb whose emit runs another verb installs a second filter --
        # both would answer, and the second click would land on a widget
        # the first one already destroyed. id() cannot carry the mark:
        # CPython reuses an address as soon as the dialog is freed.
        if obj.property(HANDLED):
            return False
        obj.setProperty(HANDLED, True)
        parsed = read(obj)
        if parsed is None:
            return False
        text, buttons = parsed
        roles = [role for _, role in buttons]
        if len(buttons) == 1 and roles[0] in ("AcceptRole", "YesRole"):
            self.caught.faults.append(text)
        else:
            undoable = next(((b.text() or "").replace("&", "")
                             for b, role in buttons
                             if role == "DestructiveRole"), None)
            self.caught.questions.append(
                (text, [(b.text() or "").replace("&", "") for b, _ in buttons],
                 undoable))
        if isinstance(obj, QtWidgets.QFileDialog):
            QtCore.QTimer.singleShot(0, lambda: _click(obj))
            return False
        chosen = _pick(buttons, self.force)
        # Deferred: the dialog is still inside its own show handler, and
        # exec() has not started the loop that a click has to unwind. By
        # the time the timer fires the dialog may have closed on its own,
        # and a bound method of a freed widget raises rather than no-ops.
        QtCore.QTimer.singleShot(0, lambda: _click(chosen))
        return False


@contextlib.contextmanager
def intercepted(force=False):
    """Route modals to the caller for the length of one emit."""
    caught = Caught()
    app = QtWidgets.QApplication.instance()
    if app is None:
        yield caught
        return
    handler = _Filter(caught, force)
    app.installEventFilter(handler)
    try:
        yield caught
    finally:
        app.removeEventFilter(handler)
        # The filter is the only thing referencing itself; PySide collects
        # an unreferenced QObject, and a collected filter catches nothing.
        handler.deleteLater()
