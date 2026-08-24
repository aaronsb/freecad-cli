# SPDX-License-Identifier: LGPL-2.1-or-later

"""A FreeCAD task panel, read as a parameter list.

Tier 0 runs a command and abandons whoever typed it to the panel that
opens. That is the whole of what `transform` does today: one call to
`Gui.runCommand("Std_TransformManip")`, and then a mouse is the only way
on. A command line that can read the panel can finish the job.

Nothing here is written per command, because a panel already says what it
is. Its input widgets carry the names its .ui file gave them --
`xPositionSpinBox`, `planeLength`, `AngleQSB` -- which are the same in
every language FreeCAD ships, unlike the labels beside them.

Three things the shape of a panel forces:

    it is a stack, not a widget      Part_Primitives puts
                                     PartGui__DlgPrimitives and
                                     PartGui__Location side by side as
                                     siblings, so reading "the" root reads
                                     half the command's parameters.

    the field set is live            A combo box swaps a QStackedWidget
                                     page, and the fields change with it.
                                     Read before each prompt; never cache.

    order comes from the screen      Tab order lists Transform's eight
                                     hidden checkboxes first and its x/y/z
                                     positions last. Geometry reads right.

Values are typed in rather than set, so FreeCAD's own parser runs and its
own validation with it -- which is why "3/4 in" lands as 19.05mm without
this module knowing what an inch is. `Gui::QuantitySpinBox` reaches
PySide as a bare `QAbstractSpinBox` with no `setValue`, so the text is the
only door as well as the better one.
"""

from .grammar import CHOICE, QUANTITY, TEXT, Option, Step
from .qt import QtCore, QtWidgets

# Names Qt gives its own internals, which mean nothing to a caller.
GENERIC = {"qt_spinbox_lineedit", "qt_scrollarea_viewport", ""}

# The buttons a panel finishes with, in the order we would rather press
# them. Read off the panel rather than assumed: Part_Primitives creates
# repeatedly and closes separately, Part_Boolean applies.
COMMIT = ("ok", "create", "apply")
DISMISS = ("cancel", "close")


def _pump(times=12):
    """Let the panel build itself before reading it."""
    try:
        import FreeCADGui as Gui
        for _ in range(times):
            Gui.updateGui()
    except Exception:
        pass


def _main_window():
    try:
        import FreeCADGui as Gui
        return Gui.getMainWindow()
    except Exception:
        return None


def roots():
    """Every task box on show, top of the panel first.

    A box names itself: the objectName is its C++ class with :: mangled to
    __, so Gui::TaskTransformDialog arrives as Gui__TaskTransformDialog.
    That is the one stable identifier a panel carries -- Gui.Control
    .activeDialog() answers True and hands over nothing.
    """
    mw = _main_window()
    if mw is None:
        return []
    named = [w for w in mw.findChildren(QtWidgets.QWidget)
             if "__" in w.objectName() and w.isVisible()
             and w.parentWidget() is not None]
    outer = [w for w in named
             if not any(o is not w and o.isAncestorOf(w) for o in named)]
    outer.sort(key=lambda w: (w.mapTo(mw, w.rect().topLeft()).y(),
                              w.mapTo(mw, w.rect().topLeft()).x()))
    return outer


def is_open():
    return bool(roots())


class Field:
    """One input on a panel, and how to read and write it."""

    def __init__(self, widget, box, order):
        self.widget = widget
        self.box = box
        self.order = order
        self.name = widget.objectName()

    @property
    def kind(self):
        w = self.widget
        if isinstance(w, QtWidgets.QAbstractSpinBox):
            return "quantity"
        if isinstance(w, QtWidgets.QComboBox):
            return "choice"
        if isinstance(w, QtWidgets.QCheckBox):
            return "flag"
        return "text"

    @property
    def choices(self):
        w = self.widget
        if isinstance(w, QtWidgets.QComboBox):
            return [w.itemText(i) for i in range(w.count())]
        return []

    def read(self):
        w = self.widget
        try:
            if isinstance(w, QtWidgets.QAbstractSpinBox):
                return w.lineEdit().text()
            if isinstance(w, QtWidgets.QComboBox):
                return w.currentText()
            if isinstance(w, QtWidgets.QCheckBox):
                return w.isChecked()
            return w.text()
        except RuntimeError:
            return None         # the panel closed under us

    def write(self, value):
        """Type it the way a person does, so the panel's parser runs."""
        w = self.widget
        try:
            if isinstance(w, QtWidgets.QAbstractSpinBox):
                line = w.lineEdit()
                line.setFocus()
                line.selectAll()
                line.setText(str(value))
                line.editingFinished.emit()
            elif isinstance(w, QtWidgets.QComboBox):
                index = w.findText(str(value))
                if index < 0:
                    return f"{value!r} is not one of: {', '.join(self.choices)}"
                w.setCurrentIndex(index)
            elif isinstance(w, QtWidgets.QCheckBox):
                w.setChecked(_truthy(value))
            else:
                w.setText(str(value))
        except RuntimeError:
            return "the panel closed before that could be set"
        _pump(4)
        return None

    def __repr__(self):
        return f"<Field {self.name} {self.kind}={self.read()!r}>"


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "yes", "y", "true", "on")


def fields():
    """Every named input the panel is offering right now, in reading order.

    Visible and enabled only: Transform carries twenty and shows ten, the
    rest belonging to modes not currently selected. Which ten depends on a
    combo box, so this is asked again rather than remembered.
    """
    found = []
    for box in roots():
        for w in box.findChildren(QtWidgets.QWidget):
            name = w.objectName()
            if name in GENERIC or not w.isVisible() or not w.isEnabled():
                continue
            if isinstance(w, QtWidgets.QLineEdit) and isinstance(
                    w.parentWidget(), QtWidgets.QAbstractSpinBox):
                continue        # the spin box itself is the field
            if not isinstance(w, (QtWidgets.QAbstractSpinBox,
                                  QtWidgets.QComboBox, QtWidgets.QCheckBox,
                                  QtWidgets.QLineEdit)):
                continue
            corner = w.mapTo(box, w.rect().topLeft())
            found.append(Field(w, box.objectName(),
                               (round(corner.y() / 8), corner.x())))
    found.sort(key=lambda f: f.order)
    return found


def buttons():
    """The panel's own buttons, by lowercased label.

    Scoped to the dock it lives in. Searching the main window swept in the
    Start page's "open first start setup" and the status bar's dimension
    readout, and one of these clicks is what commits.
    """
    found = roots()
    if not found:
        return {}
    scope, walk = found[0], found[0]
    while walk is not None:
        if isinstance(walk, QtWidgets.QDockWidget):
            scope = walk
            break
        walk = walk.parentWidget()
    out = {}
    for b in scope.findChildren(QtWidgets.QPushButton):
        if not b.isVisible():
            continue
        label = (b.text() or "").replace("&", "").strip().lower()
        if label and label not in out:
            out[label] = b
    return out


def press(*labels):
    """Press the first of these the panel offers. Returns which, or None."""
    available = buttons()
    for label in labels:
        button = available.get(label)
        if button is None:
            continue
        try:
            button.click()
        except RuntimeError:
            return None
        _pump(16)
        return label
    return None


def commit():
    """Finish the panel the way its own button does."""
    return press(*COMMIT)


def dismiss():
    """Abandon it, and let FreeCAD undo whatever was applied on the way.

    A panel applies as each field is written -- the model moves before OK
    is pressed -- so cancelling is what puts it back. FreeCAD owns that,
    which is why this verb keeps no transaction of its own.
    """
    pressed = press(*DISMISS)
    try:
        import FreeCADGui as Gui
        Gui.Control.closeDialog()
    except Exception:
        pass
    _pump(10)
    return pressed


# ------------------------------------------------------------------ steps

# What a .ui file calls a widget, minus what it calls the widget kind.
SUFFIXES = ("spinbox", "combobox", "checkbox", "lineedit", "qsb", "edit",
            "box", "cb", "field")
# And what it calls the widget kind up front, which .ui files do just as
# often: chkSymmetric, txtAxisLink, spinLenFwd.
PREFIXES = ("chk", "txt", "spin", "btn", "cmb", "lbl", "le", "ed")


def prompt_for(name):
    """`xPositionSpinBox` -> `x position`.

    The label beside a field would read better and cannot be had: two of
    Transform's eleven inputs resolve one through QFormLayout or a buddy,
    the rest sitting in grids with nothing tying them to their text. The
    objectName is always there, and always in English.
    """
    trimmed = name
    lowered = name.lower()
    for suffix in SUFFIXES:
        if lowered.endswith(suffix) and len(trimmed) > len(suffix):
            trimmed = trimmed[:-len(suffix)]
            break
    for prefix in PREFIXES:
        rest = trimmed[len(prefix):]
        # Only when what follows starts a word of its own, so `spinOffset`
        # loses its prefix and `position` keeps all of itself.
        if (lowered.startswith(prefix) and rest
                and (rest[0].isupper() or rest[0] == "_")):
            trimmed = rest
            break
    words, current = [], ""
    for i, ch in enumerate(trimmed):
        after = trimmed[i + 1:i + 2]
        # A capital starts a word when the character before it was not one
        # -- xPosition -- and also when the one after it is lower, which is
        # what tells XDirection from an acronym.
        starts = ch.isupper() and current and (
            not current[-1].isupper() or (after and after.islower()))
        if ch in "_-":
            if current:
                words.append(current)
            current = ""
        elif starts:
            words.append(current)
            current = ch
        else:
            current += ch
    if current:
        words.append(current)
    spelled = " ".join(w.lower() for w in words if w).strip()
    return spelled or name


def _done(engine):
    engine.flags["panel_done"] = True
    return True         # the verb is finished


DONE = Option("done", "apply what is set and close the panel", _done)


def _writer(name):
    """Put the answer into the panel as soon as it is given.

    A panel applies as each field is written -- the model moves before any
    button is pressed -- and that is what makes cancelling it mean
    something. Holding the answers until the end would give up both.

    Looked up by name at the time rather than captured: a combo box swaps
    a whole page of fields, and the widget found when the command started
    may no longer be the one on show.
    """
    def write(engine, step, value):
        for field in fields():
            if field.name == name:
                return field.write(value)
        return f"{prompt_for(name)} is no longer on the panel"
    return write


def steps_from(found):
    """One step per field the panel is showing, in reading order.

    Every one optional: a panel offers ten parameters and a command
    usually means two, so bare Enter passes over a field and leaves the
    panel's own value standing. `done` stops asking and commits.
    """
    steps = []
    for index, field in enumerate(found):
        kind, choices = QUANTITY, []
        if field.kind == "choice":
            kind, choices = CHOICE, list(field.choices)
        elif field.kind == "flag":
            kind, choices = CHOICE, ["yes", "no"]
        elif field.kind == "text":
            kind = TEXT
        current = field.read()
        shown = "yes" if current is True else "no" if current is False else current
        steps.append(Step(
            id=field.name,
            kind=kind,
            prompt=f"{prompt_for(field.name)} [{shown}]",
            choices=choices,
            options=[DONE],
            optional=True,
            prompt_order=index,
            on_accept=_writer(field.name),
        ))
    return steps
