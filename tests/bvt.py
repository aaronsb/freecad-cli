# SPDX-License-Identifier: LGPL-2.1-or-later

"""Build verification against a real FreeCAD GUI.

The offscreen suite covers the grammar. It cannot cover the dock, the
application-level key filter, the picker, the factory loading at startup,
undo through real transactions, or the shutdown path -- all of which need a
running GUI.

This drives that GUI entirely through the command line and never touches a
dialog, which is only possible because every document verb takes its
arguments inline: save writes without a file chooser, close! discards
without confirming. So it runs unattended.

    make bvt

A macro cannot set the process exit code, so results are written to JSON and
the runner reads them. A missing file means FreeCAD died, which is a failure
the runner reports rather than a hang.
"""

import json
import os
import tempfile
import time
import traceback

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore, QtGui, QtWidgets

RESULT = os.environ.get("FCCLI_BVT_RESULT",
                        os.path.join(tempfile.gettempdir(), "fccli-bvt.json"))
CHECKS = []


# ------------------------------------------------------- dialog watchdog

ESCAPED = []       # raised while the command line was driving
EXPECTED = []      # raised at any other time, which is FreeCAD being itself
_WATCHDOG = []


def watch_for_dialogs(dock):
    """Catch a modal the command line let through.

    A dialog is only a fault when the command line raised it. FreeCAD puts
    dialogs up all the time and that is what it is for; the claim this
    suite makes is narrower -- that a command typed on the command line is
    answered there. So the test is whether the engine was mid-command.

    Everything is dismissed either way, because a modal with nobody to
    click it blocks the Qt loop: the failure mode was a four-minute wait
    and then a timeout naming nothing. Only what appeared under a command
    is counted as a failure.
    """
    from fccli.modals import HANDLED

    def tick():
        w = QtWidgets.QApplication.activeModalWidget()
        if w is None or w.property(HANDLED):
            return          # nothing up, or the command line is handling it
        seen = "%s %r" % (type(w).__name__, w.windowTitle())
        driving = dock is not None and dock.engine.state != "idle"
        (ESCAPED if driving else EXPECTED).append(seen)
        try:
            w.reject()
        except Exception:
            try:
                w.close()
            except Exception:
                pass

    timer = QtCore.QTimer()
    timer.setInterval(400)
    timer.timeout.connect(tick)
    timer.start()
    # PySide collects an unreferenced QTimer, and a stopped watchdog looks
    # exactly like a run where no dialog ever appeared.
    _WATCHDOG.append(timer)
    return timer


def check(label, got, want):
    ok = got == want
    CHECKS.append({"label": label, "ok": ok,
                   "got": repr(got), "want": repr(want)})
    print(f"  {'ok  ' if ok else 'FAIL'} {label}"
          + ("" if ok else f"   got {got!r} want {want!r}"))
    return ok


def truthy(label, got):
    return check(label, bool(got), True)


def no_dialog(label):
    """Gui.Control.activeDialog() returns False when nothing is open, not None."""
    return check(label, bool(Gui.Control.activeDialog()), False)


# ------------------------------------------------------------------ suites

def suite_dock(dock):
    print("\n1. the dock loads into a real main window")
    mw = Gui.getMainWindow()
    truthy("dock exists", dock is not None)
    check("it is in the top area", mw.dockWidgetArea(dock),
          QtCore.Qt.TopDockWidgetArea)
    truthy("it spans the window", dock.width() > mw.width() * 0.9)
    truthy("View > Panels lists it",
           any(a.text() == "Command Line" for a in mw.createPopupMenu().actions()))
    counts = dock.factory_counts or {}
    truthy("the factory ran at startup", counts.get("total", 0) > 900)
    truthy("  tier 0 covers the command registry", counts.get("tier0", 0) > 900)
    truthy("  tier 1 generated from types", counts.get("tier1", 0) > 150)
    truthy("  patches applied", counts.get("patched", 0) >= 6)


def suite_keys(dock):
    print("\n2. keys reach the command line from the viewport")
    app = QtWidgets.QApplication.instance()
    # There is no 3D view until a document is open.
    dock.engine.submit("new keys")
    app.processEvents()
    view = _view_widget(Gui.getMainWindow())
    if view is None:
        check("a 3D view widget exists", False, True)
        return
    dock.console.set_input("")
    view.setFocus(QtCore.Qt.OtherFocusReason)
    app.processEvents()
    for ch in "box":
        target = app.focusWidget() or view
        app.sendEvent(target, QtGui.QKeyEvent(
            QtCore.QEvent.KeyPress, QtGui.QKeySequence(ch)[0].key(),
            QtCore.Qt.NoModifier, ch))
        app.processEvents()
    check("typing with the viewport focused lands in the console",
          dock.console.input_text(), "box")
    # The claim is that typing keeps working, not that any particular widget
    # reports focus: hasFocus() also needs an active window, which a display
    # with no window manager never has, and the 3D view can take focus back
    # asynchronously once a document opens.
    for ch in "es":
        target = app.focusWidget() or view
        app.sendEvent(target, QtGui.QKeyEvent(
            QtCore.QEvent.KeyPress, QtGui.QKeySequence(ch)[0].key(),
            QtCore.Qt.NoModifier, ch))
        app.processEvents()
    check("and keeps landing, so focus followed",
          dock.console.input_text(), "boxes")

    # A command is a verb and then its arguments, and the thing between
    # them is a space. Space is also FreeCAD's visibility toggle, so it sat
    # in the passthrough allowlist unconditionally and never reached the
    # command line -- typing from the viewport got as far as the first
    # word. `new file` worked because the console still had focus; once a
    # document opened, the 3D view took it back.
    dock.console.set_input("")
    view.setFocus(QtCore.Qt.OtherFocusReason)
    app.processEvents()
    for ch in "circle 0,0,0 5":
        target = app.focusWidget() or view
        key = (QtCore.Qt.Key_Space if ch == " "
               else QtGui.QKeySequence(ch)[0].key())
        app.sendEvent(target, QtGui.QKeyEvent(
            QtCore.QEvent.KeyPress, key, QtCore.Qt.NoModifier, ch))
        app.processEvents()
    check("a space mid-command reaches the command line",
          dock.console.input_text(), "circle 0,0,0 5")

    # Idle with an empty line, it is FreeCAD's key again.
    dock.console.set_input("")
    app.processEvents()
    ev_space = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Space,
                               QtCore.Qt.NoModifier, " ")
    check("idle, space is still FreeCAD's", dock.keyfilter.should_usurp(ev_space), False)
    dock.console.set_input("c")
    check("  and the command line's once a line is started",
          dock.keyfilter.should_usurp(ev_space), True)

    dock.console.set_input("")
    dock.engine.submit("close!")


def suite_geometry(dock):
    print("\n3. commands build real geometry")
    engine = dock.engine
    engine.submit("new bvt")
    doc = App.ActiveDocument
    engine.submit("box 0,0,0 40 30 20")          # hand-written, takes a point
    engine.submit("cylinder 12 40")              # patched from a type
    engine.submit("polyline 0,0,50 40,0,50 40,30,50 close")
    engine.submit("sphere 8")                    # patched
    names = [(o.Name, o.TypeId) for o in doc.Objects]
    check("four objects", len(names), 4)
    truthy("a Part::Box", any(t == "Part::Box" for _, t in names))
    truthy("a Part::Cylinder", any(t == "Part::Cylinder" for _, t in names))
    truthy("a Draft wire", any("Wire" in n for n, _ in names))
    box = doc.getObject("Box")
    check("the hand-written box honoured its corner",
          tuple(box.Placement.Base), (0.0, 0.0, 0.0))
    check("  and its dimensions", (box.Length.Value, box.Width.Value,
                                   box.Height.Value), (40.0, 30.0, 20.0))
    return doc


def suite_undo(dock, doc):
    print("\n4. undo works through real transactions")
    before = len(doc.Objects)
    truthy("the undo stack is labelled with typed commands",
           doc.UndoNames and doc.UndoNames[0].startswith("sphere"))
    dock.engine.submit("undo")
    check("undo removes one command", len(doc.Objects), before - 1)
    dock.engine.submit("redo")
    check("redo restores it", len(doc.Objects), before)


def suite_picker(dock):
    print("\n5. picking arms without opening a second input surface")
    dock.engine.submit("polyline")
    dock.engine.submit("0,0,0")
    QtWidgets.QApplication.processEvents()
    no_dialog("no task dialog appeared")
    check("the picker is the snapping backend", dock.picker.backend, "snap")
    dock.engine.feed_point(App.Vector(30, 0, 0))
    dock.engine.feed_point(App.Vector(30, 30, 0))
    dock.engine.submit("")
    truthy("a picked polyline replayed as text",
           any(h.startswith("polyline 0,0,0 30") for h in dock.console._history))
    dock.engine.cancel()


def suite_selection(dock):
    print("\n4h. a verb that acts on a selection takes the live one")
    doc = App.ActiveDocument or App.newDocument("sel")
    sphere = doc.addObject("Part::Sphere", "Ball")
    doc.recompute()
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, sphere.Name)

    dock.engine.submit("move")
    QtWidgets.QApplication.processEvents()
    step = dock.engine.current_step()
    truthy("having selected, it does not ask again",
           step is not None and step.kind == "point")
    check("  it went straight to the first point", step.id, "frm")
    check("  and the selection is what it holds",
          [o.Name for o in dock.engine.values.get("objects", [])], ["Ball"])
    check("nothing is offered as an anchor by a selection",
          dock.picker._last, None)

    dock.engine.feed_point(App.Vector(0, 0, 0))
    QtWidgets.QApplication.processEvents()
    check("a real point becomes the anchor Draft draws from",
          tuple(dock.picker._last), (0.0, 0.0, 0.0))
    dock.engine.feed_point(App.Vector(50, 20, 0))
    QtWidgets.QApplication.processEvents()
    check("the move landed", tuple(sphere.Placement.Base), (50.0, 20.0, 0.0))
    no_dialog("no dialog appeared")

    # With nothing selected, it says so rather than sitting silently.
    Gui.Selection.clearSelection()
    errors = []
    stop = dock.bus.subscribe(
        lambda m: errors.append(m.text) if m.kind == "error" else None)
    dock.engine.submit("move")
    QtWidgets.QApplication.processEvents()
    dock.engine.submit("")
    QtWidgets.QApplication.processEvents()
    truthy("with nothing selected, Enter explains itself",
           any("nothing selected" in e for e in errors))
    stop()
    dock.engine.cancel()
    doc.removeObject(sphere.Name)
    doc.recompute()


def suite_tracker(dock):
    print("\n5a. Draft's own track line is the rubber band")
    # Not our line. Passing lastpoint to Gui.Snapper.snap makes Draft light
    # its lineTracker from there to the cursor. It never appeared before
    # because lastpoint was arriving as a document object for any verb with
    # a selection step, so Draft raised inside p1() before reaching on().
    from fccli.picking import ensure_snapper
    truthy("the snapper is available", ensure_snapper())
    snapper = Gui.Snapper
    truthy("Draft owns a track line", snapper.trackLine is not None)

    snapper.off()
    QtWidgets.QApplication.processEvents()
    check("it is dark to begin with", snapper.trackLine.Visible, False)

    snapper.snap((400, 300), lastpoint=App.Vector(0, 0, 0))
    QtWidgets.QApplication.processEvents()
    truthy("a snap with a last point lights it", snapper.trackLine.Visible)
    check("  anchored at the point given",
          tuple(snapper.trackLine.p1()), (0.0, 0.0, 0.0))
    truthy("  and running to where the cursor snapped",
           tuple(snapper.trackLine.p2()) != (0.0, 0.0, 0.0))

    snapper.snap((400, 300))
    QtWidgets.QApplication.processEvents()
    check("no last point, no line", snapper.trackLine.Visible, False)

    snapper.off()
    QtWidgets.QApplication.processEvents()
    check("Snapper.off puts it away, which is what teardown calls",
          snapper.trackLine.Visible, False)

    # And the engine feeds it a point, never anything else.
    dock.engine.submit("line")
    QtWidgets.QApplication.processEvents()
    check("the first point has no anchor to offer", dock.picker._last, None)
    dock.engine.feed_point(App.Vector(3, 4, 0))
    QtWidgets.QApplication.processEvents()
    check("the second is anchored on the first",
          tuple(dock.picker._last), (3.0, 4.0, 0.0))
    dock.engine.cancel()
    QtWidgets.QApplication.processEvents()


def suite_dock_geometry(dock):
    print("\n5b. the dock resizes, docked and floating")
    from fccli import dock as D
    mw = Gui.getMainWindow()

    dock.persist = True            # the suite is testing persistence itself
    mw.resizeDocks([dock], [380], QtCore.Qt.Vertical)
    QtWidgets.QApplication.processEvents()
    check("docked, it takes the height it is dragged to", dock.height(), 380)
    dock._save_geometry()
    check("  and remembers it", D.saved_height(), 380)

    dock.setFloating(True)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    truthy("floating, it is a window", dock.isFloating())
    dock.resize(880, 520)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    check("floating, width follows", dock.width(), 880)
    check("floating, height follows", dock.height(), 520)

    # The control strip must not set the floor for the whole window.
    dock.resize(340, 150)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    truthy("it shrinks past the width of the control strip", dock.width() <= 360)
    dock._save_geometry()
    check("the floating size is remembered apart from the docked one",
          list(D.saved_float_size()), [dock.width(), dock.height()])

    dock.setFloating(False)
    for _ in range(3):
        QtWidgets.QApplication.processEvents()
    check("re-docked, the docked height comes back, not the floating one",
          D.saved_height(), 380)

    # A drag below MIN_FLOAT is deliberate -- minimumSizeHint allows it so a
    # floating command line can be tucked into a corner -- and it now
    # survives a re-float rather than snapping back to 320. Only a value
    # small enough to leave a window nobody can find is clamped.
    from fccli.dock import params as _params
    _params().SetInt("FloatWidth", 200)
    _params().SetInt("FloatHeight", 90)
    check("a size dragged below MIN_FLOAT is kept",
          list(D.saved_float_size()), [200, 90])
    _params().SetInt("FloatWidth", 10)
    _params().SetInt("FloatHeight", 10)
    check("a stored size under the floor is clamped up",
          list(D.saved_float_size()), list(D.FLOOR_FLOAT))
    _params().SetInt("FloatWidth", 900)
    _params().SetInt("FloatHeight", 600)
    check("a stored size above it is taken as given",
          list(D.saved_float_size()), [900, 600])
    _params().SetInt("DockHeight", 10)
    check("the docked height has a floor too", D.saved_height(), 70)
    _params().SetInt("DockHeight", 380)
    dock.persist = False


def suite_units(dock):
    print("\n6. units follow the schema")
    from fccli import units as U
    entry = U.current_name()
    results = []
    stop = dock.bus.subscribe(
        lambda m: results.append(m.text) if m.kind == "result" else None)
    U.set_schema("Internal")
    dock.engine.submit("cylinder 12 40")
    check("internal renders mm", results[-1], "cylinder 12.00mm 40.00mm")
    U.set_schema("ImperialBuilding")
    dock.engine.submit("cylinder 12 40")
    check("a bare number takes the schema's unit", results[-1], "cylinder 1' 3'4\"")
    U.set_schema(entry)
    stop()


def suite_check(dock, doc):
    print("\n7. check validates without running")
    before = len(doc.Objects)
    infos = []
    stop = dock.bus.subscribe(
        lambda m: infos.append(m.text) if m.kind == "info" else None)
    dock.engine.submit("check cylinder 12 40")
    truthy("it says what would be created",
           any("Part::Cylinder" in i for i in infos))
    dock.engine.submit("check box 0,0,0 40 zz 20")
    truthy("it names a bad token", any("'zz'" in i for i in infos))
    check("nothing was created", len(doc.Objects), before)
    stop()


def suite_modals(dock):
    """A command that rejects the request must say so, not wait for a click.

    Over the socket this hung the caller outright: the dialog waited for a
    click nobody was there to make, while the same instance went on
    answering everything else, so it did not even look broken.

    Driven through engine.submit rather than modals.intercepted, so it
    asserts what the operator sees -- an error on the bus, no object, and
    the transaction rolled back -- rather than only what the filter caught.
    """
    print("\n7b. a rejected request answers on the command line")
    from fccli import modals

    errors, infos = [], []
    stop = dock.bus.subscribe(
        lambda m: errors.append(m.text) if m.kind == "error"
        else (infos.append(m.text) if m.kind == "info" else None))

    dock.engine.submit("new modals")
    doc = App.ActiveDocument
    doc.addObject("Part::Box", "Slab")
    doc.recompute()
    before, undo_before = len(doc.Objects), len(doc.UndoNames)

    # PartDesign_Revolution wants an active body and says so in a modal.
    dock.engine.submit("revolve")
    for _ in range(30):
        QtWidgets.QApplication.processEvents()

    truthy("the refusal reaches the bus as an error", bool(errors))
    truthy("  naming the verb that was typed",
           any(e.startswith("revolve") for e in errors))
    truthy("  and carrying what FreeCAD said",
           any("body" in e.lower() or "select" in e.lower() for e in errors))
    check("nothing was created", len(doc.Objects), before)
    check("no undo step was left behind", len(doc.UndoNames), undo_before)
    check("no modal is left waiting",
          QtWidgets.QApplication.activeModalWidget(), None)
    check("the engine is idle again", dock.engine.state, "idle")

    # A notice is the command reporting that it worked. Reading every
    # one-button box as a rejection rolled the transaction back and called
    # a success a failure.
    errors.clear()
    with modals.intercepted() as caught:
        box = QtWidgets.QMessageBox(Gui.getMainWindow())
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.setWindowTitle("Mesh check")
        box.setText("No errors found in the mesh.")
        box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        QtCore.QTimer.singleShot(0, box.exec)
        for _ in range(30):
            QtWidgets.QApplication.processEvents()
    truthy("an informational box is caught", bool(caught.notices))
    check("  and does not fail the command", bool(caught), False)
    check("  nor is it left on screen",
          QtWidgets.QApplication.activeModalWidget(), None)

    # Nobody clicked anything above: the filter's own deferred press is
    # what dismissed both, which the hand-clicked version never exercised.
    truthy("the filter dismissed them itself",
           QtWidgets.QApplication.activeModalWidget() is None)

    stop()
    dock.engine.submit("close!")


def suite_panel(dock):
    """A task panel, offered as steps and finished from the command line.

    Tier 0 runs Std_TransformManip and leaves the panel to a mouse. This
    reads what it is asking for, offers it as prompts, writes the answers
    back and presses the panel's own button. Nothing is written per
    command: the panel names its own fields.
    """
    print("\n7c. a task panel answers on the command line")
    from fccli import panels

    dock.engine.submit("new panel")
    doc = App.ActiveDocument
    slab = doc.addObject("Part::Box", "Slab")
    slab.Length, slab.Width, slab.Height = 100, 60, 20
    doc.recompute()

    def select():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, "Slab")
        for _ in range(6):
            QtWidgets.QApplication.processEvents()

    def settle(n=25):
        for _ in range(n):
            QtWidgets.QApplication.processEvents()

    def skip_to(target):
        for _ in range(14):
            step = dock.engine.current_step()
            if step is None or step.id == target:
                return step
            dock.engine.submit("")
            settle(4)
        return dock.engine.current_step()

    select()
    dock.engine.submit("transform")
    settle()

    truthy("the panel opened", panels.is_open())
    check("and the engine is collecting", dock.engine.state, "collecting")
    ids = [s.id for s in dock.engine.prompt_sequence()]
    truthy("its fields became steps", len(ids) >= 8)
    truthy("  named as the panel names them", "xPositionSpinBox" in ids)
    truthy("  read in the order it reads",
           ids.index("xPositionSpinBox") < ids.index("zRotationSpinBox"))
    step = dock.engine.current_step()
    truthy("a prompt carries the panel's own value",
           step is not None and "[" in step.prompt)

    # Answering is typing into the panel, so FreeCAD's parser runs -- which
    # is why a fraction of an inch needs nothing from this module.
    skip_to("xPositionSpinBox")
    dock.engine.submit("25 mm")
    settle(8)
    skip_to("zPositionSpinBox")
    dock.engine.submit("3/4 in")
    settle(8)
    dock.engine.submit("done")
    settle(30)

    check("what was typed is what moved",
          [round(v, 3) for v in slab.Placement.Base], [25.0, 0.0, 19.05])
    check("the panel closed itself", panels.is_open(), False)
    check("and the engine is idle", dock.engine.state, "idle")
    no_dialog("nothing is waiting for a click")

    # Cancelling cancels the panel, and FreeCAD puts back what it applied.
    was = [round(v, 3) for v in slab.Placement.Base]
    select()
    dock.engine.submit("transform")
    settle()
    truthy("it opens again", panels.is_open())
    skip_to("yPositionSpinBox")
    dock.engine.submit("40 mm")
    settle(10)
    truthy("a panel applies as it is written, before any commit",
           round(slab.Placement.Base.y, 3) == 40.0)
    dock.engine.cancel()
    settle(30)
    check("cancelling puts it back",
          [round(v, 3) for v in slab.Placement.Base], was)
    check("  and takes the panel with it", panels.is_open(), False)
    check("  leaving the engine idle", dock.engine.state, "idle")

    dock.engine.submit("close!")


def suite_panels_generic(dock):
    """Panels nobody wrote code for.

    transform proves the mechanism; these prove it is a mechanism. Same
    three callables, a different command each time -- a panel names its
    own fields, so there is nothing per command to write.
    """
    print("\n7d. the same machinery, on panels nobody wrote for")
    from fccli import panels

    dock.engine.submit("new panels")
    doc = App.ActiveDocument
    slab = doc.addObject("Part::Box", "Slab")
    slab.Length, slab.Width, slab.Height = 100, 60, 20
    doc.recompute()

    def settle(n=30):
        for _ in range(n):
            QtWidgets.QApplication.processEvents()

    def select(*names):
        Gui.Selection.clearSelection()
        for n in names:
            Gui.Selection.addSelection(doc.Name, n)
        settle(6)

    def answer(pairs):
        """Skip to each field by name, answer it, then finish."""
        for target, value in pairs:
            for _ in range(18):
                step = dock.engine.current_step()
                if step is None or step.id == target:
                    break
                dock.engine.submit("")
                settle(4)
            step = dock.engine.current_step()
            if step is None or step.id != target:
                return f"never reached {target}"
            dock.engine.submit(value)
            settle(8)
        dock.engine.submit("done")
        settle(35)
        return None

    # Std_Placement -- fourteen fields, and a quantity that has to survive
    # the trip through FreeCAD's parser to mean anything.
    select("Slab")
    dock.engine.submit("placement")
    settle()
    truthy("placement opens a panel", panels.is_open())
    truthy("  offering more fields than transform does",
           len(dock.engine.prompt_sequence()) >= 12)
    check("answering it", answer([("xPos", "30 mm"), ("zPos", "3/4 in")]), None)
    check("  moves the object it was aimed at",
          [round(v, 3) for v in slab.Placement.Base], [30.0, 0.0, 19.05])
    check("  and closes", panels.is_open(), False)

    # A choice among the steps, answered as a choice. Std_Placement's
    # rotation input switches between an axis-and-angle and Euler angles,
    # and swaps the fields under it either way.
    kinds = {st.kind for st in dock.engine.prompt_sequence()}
    select("Slab")
    dock.engine.submit("placement")
    settle()
    kinds = {st.kind for st in dock.engine.prompt_sequence()}
    truthy("a panel's combo box becomes a choice step", "choice" in kinds)
    combo = next((st for st in dock.engine.prompt_sequence()
                  if st.kind == "choice"), None)
    truthy("  offering what the combo offers",
           combo is not None and len(combo.choices) >= 2)
    dock.engine.cancel()
    settle(20)
    check("cancelling closes it", panels.is_open(), False)

    # FreeCAD shows one task dialog at a time and refuses a second, so a
    # panel we finished but left registered would block every panel
    # command after it.
    check("FreeCAD agrees no dialog is left registered",
          bool(Gui.Control.activeDialog()), False)

    Gui.activateWorkbench("PartWorkbench")
    settle(8)
    before = {o.Name for o in doc.Objects}

    # Part_Primitives -- the one that matters. Its combo swaps a whole
    # QStackedWidget page, so the fields after it are not the fields
    # before it. A step that held its widget would write into a page
    # nobody is looking at.
    before = {o.Name for o in doc.Objects}
    Gui.Selection.clearSelection()
    dock.engine.submit("primitive")
    settle()
    truthy("primitive opens a panel", panels.is_open())
    first = [f.name for f in panels.fields()]
    truthy("  showing the plane page to begin with", "planeLength" in first)
    check("choosing a different primitive",
          answer([("PrimitiveTypeCB", "Cylinder")]), None)
    made = sorted({o.Name for o in doc.Objects} - before)
    check("  builds the one that was chosen", made, ["Cylinder"])
    check("  and closes", panels.is_open(), False)

    dock.engine.submit("close!")


def suite_roundtrip(dock):
    print("\n8. save, close and reopen, with no dialogs")
    path = os.path.join(tempfile.gettempdir(), "fccli-bvt-doc.FCStd")
    os.path.exists(path) and os.remove(path)
    dock.engine.submit(f"save {path}")
    truthy("the file was written without a chooser", os.path.exists(path))
    no_dialog("no dialog opened")
    before = [o.Name for o in App.ActiveDocument.Objects]
    dock.engine.submit("close")
    check("a saved document closes without asking", App.listDocuments(), {})
    dock.engine.submit(f"open {path}")
    check("it reopens with its contents",
          [o.Name for o in App.ActiveDocument.Objects], before)
    os.path.exists(path) and os.remove(path)


def suite_shutdown(dock):
    print("\n9. everything closes without a confirmation")
    dock.engine.submit("box 0,0,0 5 5 5")        # make it dirty on purpose
    dock.engine.submit("close")
    truthy("a dirty document refuses to close quietly",
           App.ActiveDocument is not None)
    dock.engine.submit("close!")
    guard = 0
    while App.listDocuments() and guard < 20:
        dock.engine.submit("close!")
        guard += 1
    check("no documents remain", App.listDocuments(), {})
    no_dialog("and no dialog is waiting")


def _view_widget(mw):
    for child in mw.findChildren(QtWidgets.QWidget):
        if "View3DInventor" in child.metaObject().className() and child.isVisible():
            return child
    return None


# -------------------------------------------------------------------- run

GEOMETRY_KEYS = ("DockHeight", "FloatWidth", "FloatHeight")


def geometry_prefs():
    """Read the dock geometry settings, so the run can put them back.

    Showing the dock fires a resize, and the dock saves what it is resized
    to. Under Xvfb that is the Xvfb window's shape, so without this a test
    run silently replaces whatever height somebody had dragged to. The unit
    schema is captured for the same reason a few suites down.
    """
    from fccli.dock import params
    have = {}
    for key in GEOMETRY_KEYS:
        value = params().GetInt(key, -1)
        if value >= 0:
            have[key] = value
    return have


def restore_geometry(saved, dock=None):
    """Put the geometry settings back exactly as they were found.

    The dock saves on a debounce, so its pending timer has to be stopped
    first -- otherwise it fires after the restore and writes the test's
    window shape back over the real setting.
    """
    if dock is not None and getattr(dock, "_save_timer", None) is not None:
        dock._save_timer.stop()
    from fccli.dock import params
    for key in GEOMETRY_KEYS:
        if key in saved:
            params().SetInt(key, saved[key])
        else:
            try:
                params().RemInt(key)     # it was not set before this run
            except Exception:
                pass


def run():
    started = time.perf_counter()
    failed_early = None
    entry_geometry = geometry_prefs()
    try:
        from fccli import dock as D
        dock = D.instance()
        watch_for_dialogs(dock)
        if dock is not None:
            dock.persist = False       # this window's shape is not a setting
        suite_dock(dock)
        suite_keys(dock)
        doc = suite_geometry(dock)
        suite_undo(dock, doc)
        suite_selection(dock)
        suite_picker(dock)
        suite_tracker(dock)
        suite_dock_geometry(dock)
        suite_units(dock)
        suite_check(dock, doc)
        suite_modals(dock)
        suite_panel(dock)
        suite_panels_generic(dock)
        suite_roundtrip(dock)
        suite_shutdown(dock)
    except Exception:
        failed_early = traceback.format_exc()
        print(failed_early)

    try:
        from fccli import dock as _D
        restore_geometry(entry_geometry, _D.instance())
    except Exception:
        restore_geometry(entry_geometry)   # the tests must not move a setting

    check("no dialog escaped a command", ESCAPED, [])
    if EXPECTED:
        print(f"  note  {len(EXPECTED)} dialog(s) outside any command, "
              f"which is FreeCAD's business: {EXPECTED[:3]}")

    passed = sum(1 for c in CHECKS if c["ok"])
    payload = {
        "passed": passed,
        "failed": len(CHECKS) - passed,
        "seconds": round(time.perf_counter() - started, 1),
        "checks": CHECKS,
        "exception": failed_early,
    }
    with open(RESULT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"\n{passed} passed, {len(CHECKS) - passed} failed "
          f"in {payload['seconds']}s")
    QtCore.QTimer.singleShot(300, QtWidgets.QApplication.quit)


QtCore.QTimer.singleShot(9000, run)
