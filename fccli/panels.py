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

import re

from . import bus as _bus
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

    def unit(self):
        """What this field measures, read off what it is showing.

        A rotation reads "0.00\u00b0" and a length "1.00 mm". Without this
        every panel quantity took Step's default of mm, so a bare number at
        a rotation prompt was parsed as a length -- and under an imperial
        schema `25` at an angle became 635.
        """
        text = (self.read() or "").strip()
        if not text:
            return ""
        if "\u00b0" in text or "deg" in text.lower():
            return "deg"
        tail = ""
        for ch in reversed(text):
            if ch.isalpha() or ch == "'" or ch == '"':
                tail = ch + tail
            elif tail:
                break
            elif ch in " \t":
                continue
            else:
                break
        return tail or ""

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

    def _write_quantity(self, w, value):
        """Put a number into a spin box the way nothing else worked.

        Gui::QuantitySpinBox declares rawValue as a Qt property, which
        reaches it through the bare QAbstractSpinBox that PySide hands
        back -- there is no setValue on that, and nothing else moved the
        number:

            setText            the text changed and the value did not, so
                               Part_Primitives showed "4 mm" in its radius
                               box and built a cylinder of 2
            interpretText      protected in Qt; the call did nothing
            focus, then type   the focus-out on panel close segfaulted in
                               ViewProviderDragger::getDraggerPlacement
            Return             deletes the widget -- in a task panel that
                               keystroke means accept the dialog

        rawValue is a plain double in FreeCAD's internal units, so the
        text is read by the same parser the rest of this program uses,
        with the unit the field itself says it measures in. `3/4 in` still
        needs nothing from here.
        """
        from .parsing import parse_quantity
        parsed = parse_quantity(str(value), unit_hint=self.unit() or "mm")
        if not parsed.ok:
            return parsed.error
        try:
            if not w.setProperty("rawValue", float(parsed.value)):
                return (f"{self.name} would not take a value "
                        "-- it is not a quantity box")
            w.lineEdit().editingFinished.emit()
        except RuntimeError:
            return "the panel closed before that could be set"
        return None

    def write(self, value):
        """Type it the way a person does, so the panel's parser runs."""
        w = self.widget
        try:
            if isinstance(w, QtWidgets.QAbstractSpinBox):
                return self._write_quantity(w, value)
            elif isinstance(w, QtWidgets.QComboBox):
                index = w.findText(str(value))
                if index < 0:
                    return f"{value!r} is not one of: {', '.join(self.choices)}"
                w.setCurrentIndex(index)
                # activated is the user-only signal, and it is the one a
                # dialog hangs its page switch on. setCurrentIndex fires
                # currentIndexChanged and not that, so Part_Primitives read
                # Cylinder in its combo while still showing the plane page
                # -- and built a plane.
                w.activated.emit(index)
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
    return True         # the verb is finished


# Not recorded: a line that named its parameters is already complete,
# and `done` inside one was read back as part of the last value --
# "xposition=25 mm done" reached FreeCAD's parser as one length.
DONE = Option("done", "apply what is set and close the panel", _done,
              record=False)


def key_for(name):
    """The word a person types to name this field. `xPositionSpinBox` -> `xposition`."""
    return prompt_for(name).replace(" ", "")


def resolve(token, found):
    """Which field a typed name means, by unique prefix.

    The same rule verbs already follow, so `xpos` reaches x position and
    `x` says what it is torn between rather than guessing.
    """
    wanted = token.strip().lower()
    if not wanted:
        return None, "give a name to set"
    exact = [f for f in found if key_for(f.name).lower() == wanted
             or f.name.lower() == wanted]
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        # key_for is lossy -- AngleQSB, angleSpinBox and Angle all read
        # `angle` -- so two visible fields can answer to one name. Taking
        # the first made the second unaddressable and swallowed every
        # write aimed at either.
        return None, (f"{token!r} names {len(exact)} fields on this panel "
                      f"({', '.join(f.name for f in exact)}) -- "
                      "use the one you mean by its full name")
    hits = [f for f in found if key_for(f.name).lower().startswith(wanted)]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        if not found:
            return None, "the panel has closed"
        names = sorted(key_for(f.name) for f in found)
        shown = ", ".join(names[:6]) + ("..." if len(names) > 6 else "")
        return None, f"{token!r} is not on this panel -- {shown}"
    return None, (f"{token!r} could be "
                  f"{', '.join(sorted(key_for(f.name) for f in hits))}")


ASSIGNMENT = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*=")


def split_assignments(text):
    """`xposition=25 mm zposition=3/4 in` -> two pairs.

    A value can contain spaces -- `3/4 in`, `Center of mass / centroid` --
    so a name=value line cannot be read a whitespace token at a time. Each
    value runs to the next name= or to the end of the line. Splitting on
    whitespace dropped the unit and put 0.75mm where 19.05 belonged, which
    parses, which is the kind that does not announce itself.
    """
    marks = list(ASSIGNMENT.finditer(text or ""))
    if not marks:
        return [], (text or "").strip()
    pairs, leading = [], text[:marks[0].start()].strip()
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        pairs.append((mark.group(1), text[mark.end():end].strip()))
    return pairs, leading


def _assign(engine, step, value, typed=None):
    """Every `name=value` on the line, written where each belongs.

    The value goes in as it was typed. The panel's own parser is the one
    that should read it, which is why `3/4 in` needs nothing from here.
    """
    text = str((typed if typed is not None else value) or "")
    pairs, leftover = split_assignments(text)
    if not pairs:
        return (f"{text.strip()!r} is not an assignment -- "
                "name=value, or `done` to apply")
    if leftover:
        return (f"{leftover!r} is not an assignment -- "
                "name=value, or `done` to apply")
    seen, problems = {}, []
    found = fields()
    for name, wanted in pairs:
        if name.lower() in seen:
            # Last would have won, silently, on a line somebody meant.
            problems.append(f"{name}: given twice")
            continue
        seen[name.lower()] = wanted
        if not wanted:
            # An empty value is not a value. It cleared a text field and
            # unchecked a flag, both without saying so.
            problems.append(f"{name}: give it a value, or leave it out")
            continue
        field, complaint = resolve(name, found)
        if complaint:
            problems.append(complaint)
            continue
        complaint = field.write(wanted)
        if complaint:
            problems.append(f"{name}: {complaint}")
            continue
        # A choice can swap the page under whatever comes after it.
        found = fields()
    # Every pair is attempted and every complaint reported. Returning at
    # the first one left the rest of the line untried while the whole line
    # went into history, so replaying it did more than running it had.
    return "; ".join(problems) if problems else None


def offered(found):
    """The names this panel answers to, as one wide line per row."""
    keys = sorted(key_for(f.name) for f in found)
    width = max((len(k) for k in keys), default=0) + 2
    per_row = max(1, 76 // width)
    rows = []
    for i in range(0, len(keys), per_row):
        rows.append("".join(k.ljust(width) for k in keys[i:i + per_row]).rstrip())
    return rows


def steps_from(found):
    """One step, taken as many times as the operator has answers for.

    A panel offers ten parameters and a command usually means two, so
    asking for each in turn meant four blank Enters to reach the fifth.
    Naming the field instead is shorter, order-independent, and -- the
    part that matters -- replays: `transform xposition=25mm` is a line
    history can hold and Up can recall, where a run of skipped prompts
    recorded a bare value that replayed into whichever field came first.
    """
    return [Step(
        id="set",
        kind=TEXT,
        prompt="name=value",
        repeat=True,
        # One, at least, before Enter can end it. Enter on a panel that
        # has been told nothing used to press OK -- undocumented, and the
        # prompt offers `done` and `cancel` and never mentioned it.
        min_count=1,
        options=[DONE],
        # The whole line, not a token at a time: a value can hold spaces.
        raw=True,
        on_accept=_assign,
    )]


def wait_for_panel(rounds=40):
    """Give the panel time to appear, and stop as soon as it has.

    A task panel is put up from the command's own event handling rather
    than by the call that started it, so how long it takes is FreeCAD's
    business. A fixed number of pumps is a race: Part_Offset built its
    object and showed its panel one round after the reading stopped, so
    the command looked like one that opens nothing.
    """
    for _ in range(rounds):
        if is_open():
            return True
        _pump(2)
    return is_open()


def _open_panel(command):
    """Run the command, and ask whatever panel it opens what it wants.

    Tier 0 runs the command and leaves the panel to a mouse. This reads it
    and offers its parameters on the command line instead. If nothing
    opens, or nothing in what opened is readable, the command has already
    run and there is nothing left to ask.
    """
    def start(engine):
        import FreeCADGui as Gui
        Gui.runCommand(command)
        if not wait_for_panel():
            return None
        found = fields()
        if not found:
            engine.bus.emit(_bus.INFO,
                            "the panel offers nothing this can type into "
                            "-- it is open for the mouse")
            return None
        engine.flags["panel"] = True
        # What it answers to, listed once, the way completion lists verbs.
        # Ten prompts in a row was the alternative, and four of them were
        # blank Enters on the way to the fifth.
        engine.bus.emit(_bus.INFO, f"{len(found)} to set:", role="head")
        for row in offered(found):
            engine.bus.emit(_bus.INFO, f"  {row}", role="quiet")
        engine.bus.emit(_bus.INFO,
                        "name=value sets one · done applies · cancel abandons",
                        role="quiet")
        return steps_from(found)
    return start


def _abort_panel(engine):
    """Cancelling the command cancels the panel, and FreeCAD puts it back.

    A panel applies as each field is written, so by the time somebody
    cancels, the model has already moved. Pressing the panel's own Cancel
    is what undoes it -- which is why this verb opens no transaction.
    """
    if engine.flags.get("panel") and is_open():
        dismiss()


def _emit_panel(v):
    engine = v.get("_engine")
    if not v["_flags"].get("panel"):
        return None             # no panel opened; the command has run
    if not is_open():
        # Somebody pressed the panel's own button while the command line
        # was still asking. Both are ways to finish it, and this one is
        # already done.
        if engine is not None:
            engine.bus.emit(_bus.INFO, "the panel was closed in the panel")
        _refresh_view()
        return None
    # The steps wrote as they were answered; this only finishes it.
    pressed = commit()
    if pressed is None:
        dismiss()
        raise RuntimeError("the panel offered no way to finish -- cancelled")
    if is_open():
        # Part_Primitives creates repeatedly and closes separately.
        press(*DISMISS)
    if engine is not None:
        engine.bus.emit(_bus.INFO, f"{pressed} -- panel closed")
    _refresh_view()
    return None


def _refresh_view():
    """Push the change to the screen now, the way the seed verbs do."""
    try:
        import FreeCADGui as Gui
        if Gui.ActiveDocument is not None:
            Gui.ActiveDocument.update()
        Gui.updateGui()
    except Exception:
        pass
