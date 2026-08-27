# SPDX-License-Identifier: LGPL-2.1-or-later

"""FreeCAD's modal dialogs, read on the command line.

A GUI rejects a malformed request by putting a message box in front of
someone. A command line has nobody in front of it, so the box waits for a
click that never comes and the caller waits with it: ``fccli exec
'revolve'`` on a solid hung until the instance was killed, while the same
instance went on answering every other request.

A dialog already says what it is, so nothing here is written per command:

    Information                 a notice. Say it and carry on -- the
                                command worked. "No errors found."
    one button, otherwise       a rejection. Say it and fail.
                                "Select a shape for revolution."
    several buttons             a question. The ButtonRoles say which
                                answer is which.
    a file chooser              a request for something a socket cannot
                                give. Refused, with the reason.

Icon and roles, never button text: the text is translated and neither of
the others is. DestructiveRole is the answer ``!`` already means --
``close!`` discards -- so a question is refused unless the line carried the
bang, and then the destructive answer is the one it asked for.

Which is one contract with two halves, and they have to agree (GH #16):

    with the bang        the destructive button is pressed, and the
                         question is *answered*. The command commits, and
                         a notice says which button went down.
    without it           nothing that proceeds or destroys is pressed. A
                         button whose role declines is, and where the
                         dialog offers none the dialog is closed unpressed.
                         The command fails, and the fault says what to
                         re-run with ``!`` to get.

Pressing Discard and then reporting "Re-run with ! for Discard" was the
two halves disagreeing on one screen.

One filter for the process, refcounted, answering the innermost armed
block. Installing one per block let a nested arm claim a dialog its outer
neighbour raised, and the outer one then committed a command it should
have failed.

Armed for the dock as much as for the socket, decided rather than
overlooked. A verb that spins the event loop leaves a window in which the
operator can raise a dialog of their own -- File > Open, during a task
panel -- and it would be caught and blamed on the verb they typed. The
answer to a command typed on the command line belongs on the command
line, at both ends of it; the narrow case where somebody interjects is
worth that. Whoever narrows this later should know it was weighed.
"""

import contextlib

from .qt import QtCore, QtWidgets

# PySide6 scopes its enums; older bindings expose the short name.
_SHOW = getattr(QtCore.QEvent, "Type", QtCore.QEvent).Show
HANDLED = "_fccli_answered"
LIMIT = 240

# Answers that mean "no". A lone one of these is the whole dialog saying no.
_REFUSING = ("AcceptRole", "YesRole")


def _role(name):
    """The role's short name, whatever Qt binding spells it."""
    return str(name).rsplit(".", 1)[-1]


def _icon(box):
    return str(box.icon()).rsplit(".", 1)[-1]


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
    return line if len(line) <= LIMIT else line[:LIMIT - 1].rstrip() + "…"


class Caught:
    """What the dialogs raised during one emit said."""

    def __init__(self):
        self.faults = []     # rejections: the command did not happen
        self.notices = []    # the command happened, and had something to say
        self.questions = []  # (text, [option names], destructive option)

    @property
    def fault(self):
        if self.faults:
            return " -- ".join(self.faults)
        if self.questions:
            text, options, undoable = self.questions[0]
            answer = f" Re-run with ! for {undoable}." if undoable else ""
            return (f"{text} -- cancelled: FreeCAD wanted one of "
                    f"{', '.join(options)}, and a command line has nobody to "
                    f"ask mid-command.{answer}")
        return None

    def __bool__(self):
        """Whether the command failed. A notice on its own is not a failure."""
        return bool(self.faults or self.questions)


def read(dialog):
    """What kind of dialog this is, its words, and the ways out of it.

    Returns (kind, text, buttons). A file chooser has no buttons worth
    reading -- scraping its labels yields "File name:" and "Files of type:"
    -- and calling .text() on one raised out of the event filter, which
    left the chooser up and the caller hanging, which is the whole bug.
    """
    if isinstance(dialog, QtWidgets.QFileDialog):
        return ("chooser",
                "this command wants a file chooser, which the command line "
                "cannot answer -- give the path as an argument instead", [])

    buttons = []
    if isinstance(dialog, QtWidgets.QMessageBox):
        text = _phrase(dialog.windowTitle(), dialog.text(),
                       dialog.informativeText())
        for b in dialog.buttons():
            buttons.append((b, _role(dialog.buttonRole(b))))
        kind = "notice" if _icon(dialog) == "Information" else "message"
    else:
        box = dialog.findChild(QtWidgets.QDialogButtonBox)
        if box is None:
            return None
        labels = [w.text() for w in dialog.findChildren(QtWidgets.QLabel)
                  if w.isVisible() and w.text()]
        text = _phrase(dialog.windowTitle(), *labels[:2])
        for b in box.buttons():
            buttons.append((b, _role(box.buttonRole(b))))
        kind = "message"
    if not buttons:
        return None
    if len(buttons) > 1:
        kind = "question"
    elif kind == "message":
        kind = "rejection" if buttons[0][1] in _REFUSING else "question"
    return kind, text, buttons


# Roles that decline. A command line with nobody in front of it answers a
# question with one of these or with none at all.
_DECLINING = ("RejectRole", "NoRole")


def _pick(buttons, force, question=True):
    """Which button the command line presses, or None to press none.

    A notice or a rejection has one way out, and pressing it answers
    nothing anybody asked -- it dismisses a message. So it is pressed.

    A question is where the choice is real, and the command line declines
    it: cancelling is the answer that cannot lose anybody's work. It
    declines with a button whose *role* says no, never with one that
    proceeds and never with one that destroys. Where the dialog offers
    neither, nothing is pressed and the dialog is closed instead -- the
    fallback order used to run on through DestructiveRole to AcceptRole,
    so a Save/Discard box with no Cancel had Discard pressed by a line
    that had not asked for it and was about to report a failure (GH #16).

    The bang is the one thing that asks for the destructive answer, the
    same way `close!` does. Then it is an answer, and `_catch` records it
    as one rather than as a question nobody could answer.
    """
    by_role = {}
    for b, role in buttons:
        by_role.setdefault(role, b)
    if not question:
        return buttons[0][0]
    if force and "DestructiveRole" in by_role:
        return by_role["DestructiveRole"]
    for role in _DECLINING:
        if role in by_role:
            return by_role[role]
    return None


def _click(widget):
    """Press it, unless it is already gone."""
    try:
        widget.click()
    except RuntimeError:
        pass          # the dialog went away before the loop came back round


def _dismiss(dialog):
    """Close it without pressing anything.

    `reject()` is what Escape does, and it is the only way out of a dialog
    that is not an answer to it. FreeCAD reads the result as its cancel
    branch, which is where a question the command line refused belongs.
    """
    try:
        dialog.reject()
    except RuntimeError:
        pass


class _Filter(QtCore.QObject):
    """The one filter. Answers whichever block is innermost right now."""

    def __init__(self):
        super().__init__()
        self.targets = []       # a stack of Caught, innermost last
        self.forced = []        # whether each of those carried the bang

    def eventFilter(self, obj, event):
        try:
            return self._catch(obj, event)
        except Exception:
            # This filter is on the QApplication, so it is called during
            # exception unwinding too -- and calling into PySide with a
            # Python exception already set raises SystemError on top of it.
            # `grid` on a FreeCAD where Arch_Grid is not registered showed
            # FreeCADError, then this filter's own SystemError under it,
            # which is a confusing way to be told a command does not exist.
            return False

    def _catch(self, obj, event):
        if event.type() != _SHOW or not self.targets:
            return False
        if not isinstance(obj, QtWidgets.QDialog) or not obj.isModal():
            return False
        # Marked on the dialog, not remembered here: a Show event arrives
        # again every time a dialog is hidden and reshown, and id() cannot
        # carry the mark because CPython reuses a freed address.
        if obj.property(HANDLED):
            return False
        parsed = read(obj)
        if parsed is None:
            return False
        kind, text, buttons = parsed
        obj.setProperty(HANDLED, True)
        caught = self.targets[-1]

        forced = self.forced[-1]

        if kind == "chooser":
            caught.faults.append(text)
            QtCore.QTimer.singleShot(0, lambda: _dismiss(obj))
            return False
        if kind == "notice":
            # "No errors found in the mesh." is the command reporting that
            # it worked. Treating every one-button box as a rejection rolled
            # the transaction back and called a success a failure.
            caught.notices.append(text)
        elif kind == "rejection":
            caught.faults.append(text)
        else:
            undoable = next(((b.text() or "").replace("&", "")
                             for b, role in buttons
                             if role == "DestructiveRole"), None)
            if forced and undoable is not None:
                # The bang already asked for this answer, so pressing it is
                # answering the question, not failing to. Recording it as a
                # question instead had `revolve!` press Discard and report
                # "Re-run with ! for Discard" over the top -- one line
                # contradicting the other, and the transaction rolled back
                # around a button that had been pressed (GH #16).
                #
                # It is said out loud rather than passed over: pressing the
                # destructive answer is what was asked for, and which
                # button that was is not something to leave unsaid.
                caught.notices.append(
                    f"{text} -- pressed {undoable}, which is what ! asked for")
            else:
                caught.questions.append(
                    (text,
                     [(b.text() or "").replace("&", "") for b, _ in buttons],
                     undoable))
        chosen = _pick(buttons, forced, kind == "question")
        # Deferred: the dialog is still inside its own show handler, and
        # exec() has not started the loop that a click has to unwind.
        QtCore.QTimer.singleShot(
            0, lambda: _click(chosen) if chosen is not None else _dismiss(obj))
        return False


_FILTER = None


@contextlib.contextmanager
def intercepted(force=False):
    """Route modals to the caller for the length of one emit."""
    global _FILTER
    caught = Caught()
    app = QtWidgets.QApplication.instance()
    if app is None:
        yield caught
        return
    if _FILTER is None:
        _FILTER = _Filter()
        app.installEventFilter(_FILTER)
    _FILTER.targets.append(caught)
    _FILTER.forced.append(bool(force))
    try:
        yield caught
    finally:
        _FILTER.targets.pop()
        _FILTER.forced.pop()
