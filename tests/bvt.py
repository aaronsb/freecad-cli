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
        # engine.driving, not engine.state: _finish resets to IDLE before
        # calling emit, so for the whole of the part that runs a command
        # the engine reads idle -- every escaped modal during emit was
        # filed as FreeCAD's business and could never fail the suite.
        driving = dock is not None and (
            dock.engine.driving or dock.engine.state != "idle")
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
    from fccli import picking as _pick
    from fccli.picking import ensure_snapper
    truthy("the snapper is available", ensure_snapper())

    # That bare call is the hazard the report used to fall into: it settles
    # _SNAPPER_READY, and the report used to live inside the bootstrap, so
    # every later call short-circuited before reaching it. Anyone who had
    # opened Draft before their first pick was in the same position -- and
    # they are the people with grid preferences worth reporting on.
    _was_draw, _was_space, _was_said = (
        _pick._grid_will_draw, _pick._grid_spacing, _pick._GRID_REPORTED)
    try:
        _pick._GRID_REPORTED = False
        _pick._grid_will_draw, _pick._grid_spacing = (lambda: True,
                                                      lambda: 0.0)
        said = []
        ensure_snapper(said.append)
        check("a snapper already up still gets the grid reported",
              len(said), 1)
    finally:
        _pick._grid_will_draw, _pick._grid_spacing = _was_draw, _was_space
        _pick._GRID_REPORTED = _was_said
    snapper = Gui.Snapper
    truthy("Draft owns a track line", snapper.trackLine is not None)

    # The grid is Draft's, configured by whoever owns this FreeCAD. The
    # picker used to switch show_always off on every snap regardless of
    # what alwaysShowGrid said, which held for the rest of the session.
    # setTrackers is where Draft reads those preferences, so compare
    # against what it set rather than against a constant.
    #
    # Reading the preference is what makes this portable and is also its
    # weakness: gridTracker starts both flags False, which is what the old
    # suppression set them to, so on a machine with the preference off both
    # sides agree either way and the check cannot tell the fix from the
    # fault. Say so rather than printing a green line that carries nothing.
    snapper.setTrackers()
    QtWidgets.QApplication.processEvents()
    _prefs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
    _always = _prefs.GetBool("alwaysShowGrid", True)
    _during = _prefs.GetBool("grid", True)
    # Per flag, not on the conjunction: with alwaysShowGrid off and grid on
    # -- an ordinary Draft setup -- two of these three compare False to
    # False and go green with the old suppression fully restored.
    if not _always:
        print("       alwaysShowGrid is off here -- the two show_always "
              "checks below cannot tell the fix from the fault")
    if not _during:
        print("       grid is off here -- the show_during_command check "
              "below cannot tell the fix from the fault")
    if snapper.grid is not None:
        check("the grid shows what alwaysShowGrid asks for",
              bool(snapper.grid.show_always), _always)
        check("  and during a command, what grid asks for",
              bool(snapper.grid.show_during_command), _during)
        # Through the picker, which is where the suppression used to sit:
        # quiet_grid ran on every resolve and every teardown, so a grid
        # switched back on by hand went away again at the next click.
        # start() first -- resolve on an unstarted picker dereferences a
        # None view, which raises instead of failing a check.
        _before = bool(snapper.grid.show_always)
        dock.picker.start(lambda *_: None)
        dock.picker.resolve((400, 300))
        dock.picker.stop()
        QtWidgets.QApplication.processEvents()
        check("  and a pick does not take it away",
              bool(snapper.grid.show_always), _before)

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
    """A task panel, answered by naming its fields.

    Tier 0 ran Std_TransformManip and left the panel to a mouse. This
    reads what it is asking for, lists it, takes name=value, and presses
    the panel's own button.
    """
    print("\n7c. a task panel answers on the command line")
    from fccli import panels

    dock.engine.submit("new panel")
    doc = App.ActiveDocument
    slab = doc.addObject("Part::Box", "Slab")
    slab.Length, slab.Width, slab.Height = 100, 60, 20
    doc.recompute()

    def settle(n=25):
        for _ in range(n):
            QtWidgets.QApplication.processEvents()

    def select():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, "Slab")
        settle(6)

    said = []
    stop = dock.bus.subscribe(
        lambda m: said.append(m.text) if m.kind in ("info", "error") else None)

    select()
    dock.engine.submit("transform")
    settle()

    truthy("the panel opened", panels.is_open())
    check("and the engine is collecting", dock.engine.state, "collecting")
    truthy("it says what it will answer to",
           any("to set:" in ln for ln in said))
    truthy("  listing the names, not the widgets",
           any("xposition" in ln for ln in said))
    truthy("  and how to use them",
           any("name=value" in ln for ln in said))
    step = dock.engine.current_step()
    truthy("one step, taken as often as there are answers",
           step is not None and step.repeat)
    # Tab has to be able to name a field, since naming one is the whole
    # design. It used to offer `done` and nothing else.
    from fccli import completion as _comp
    offered_now = _comp.from_source(dock.engine, "fields")
    truthy("Tab can name a field", any(o.startswith("xposition=")
                                       for o in offered_now))
    truthy("  offering every one the panel has",
           len(offered_now) == len(panels.fields()))
    check("  and the step says where they come from",
          dock.engine.current_step().completes, "fields")

    # The status line counts the steps this invocation has, not the ones
    # the verb declared -- a panel verb declares none and read "step 1/0".
    truthy("the status line counts real steps",
           len(dock.engine.prompt_sequence()) >= 1)


    # Named, so order does not matter and nothing is skipped past.
    dock.engine.submit("zposition=3/4 in")
    settle(10)
    dock.engine.submit("xposition=25 mm")
    settle(10)
    truthy("a panel applies as it is written, before any commit",
           [round(v, 3) for v in slab.Placement.Base] == [25.0, 0.0, 19.05])
    dock.engine.submit("done")
    settle(30)

    check("what was named is what moved",
          [round(v, 3) for v in slab.Placement.Base], [25.0, 0.0, 19.05])
    check("the panel closed itself", panels.is_open(), False)
    check("and the engine is idle", dock.engine.state, "idle")
    no_dialog("nothing is waiting for a click")

    # The line it recorded has to mean the same thing typed again -- the
    # premise the whole project rests on. A run of skipped prompts used to
    # record a bare value that replayed into whichever field came first.
    line = dock.console._history[-1] if dock.console._history else ""
    truthy("history records the names it was given", "xposition=" in line)
    truthy("  and the other one", "zposition=" in line)

    slab.Placement.Base = App.Vector(0, 0, 0)
    doc.recompute()
    select()
    dock.engine.submit(line)
    settle(35)
    check("replaying it lands in the same place",
          [round(v, 3) for v in slab.Placement.Base], [25.0, 0.0, 19.05])
    check("  and closes behind itself", panels.is_open(), False)

    # A whole command on one line, the way `circle 0,0,0 5` is.
    slab.Placement.Base = App.Vector(0, 0, 0)
    doc.recompute()
    select()
    dock.engine.submit("transform yposition=40 mm")
    settle(35)
    check("a line that named its parameters needs no done",
          [round(v, 3) for v in slab.Placement.Base], [0.0, 40.0, 0.0])
    check("  and left nothing open", panels.is_open(), False)

    # An angle is not a length. Every panel quantity used to take Step's
    # default unit of mm, so a bare number at a rotation prompt was read
    # as a distance.
    select()
    dock.engine.submit("transform zrotation=30")
    settle(35)
    truthy("a bare number at a rotation is degrees",
           abs(slab.Placement.Rotation.Angle - 0.5236) < 0.01)
    truthy("  about the axis it was named on",
           abs(abs(slab.Placement.Rotation.Axis.z) - 1.0) < 0.01)

    # Names resolve the way verb names do. Placement reset first: the
    # rotation above turns the panel's local axes, so x stops being x.
    slab.Placement = App.Placement()
    doc.recompute()
    said.clear()
    select()
    dock.engine.submit("transform")
    settle()
    dock.engine.submit("xpos=5 mm")
    settle(10)
    truthy("a unique prefix reaches its field",
           abs(slab.Placement.Base.x - 5.0) < 0.001)
    dock.engine.submit("x=1 mm")
    settle(8)
    truthy("an ambiguous one says what it is torn between",
           any("could be" in ln and "xposition" in ln for ln in said))
    dock.engine.submit("nosuch=1")
    settle(8)
    truthy("  and an unknown one says so",
           any("not on this panel" in ln for ln in said))
    dock.engine.submit("justaword")
    settle(8)
    truthy("something that is not an assignment says that",
           any("is not an assignment" in ln for ln in said))
    dock.engine.cancel()
    settle(25)
    check("cancelling closes the panel", panels.is_open(), False)

    # A line the panel refused is not a line it was answered with. values
    # is what says a command is complete, and _accept recorded the value
    # before asking on_accept whether it was any good -- so a typo'd field
    # name printed its error and then pressed the panel's OK.
    slab.Placement = App.Placement()
    doc.recompute()
    said.clear()
    select()
    dock.engine.submit("transform xpositon=25 mm")
    settle(30)
    truthy("a typo says so", any("not on this panel" in ln for ln in said))
    truthy("  and does not commit the panel", panels.is_open())
    check("  nor move anything",
          [round(v, 3) for v in slab.Placement.Base], [0.0, 0.0, 0.0])

    # A value the parser cannot read is not a value.
    said.clear()
    dock.engine.submit("xposition=oops")
    settle(12)
    truthy("a value that will not parse says so", bool(said))
    check("  and moves nothing",
          [round(v, 3) for v in slab.Placement.Base], [0.0, 0.0, 0.0])

    # An empty one clears a field without meaning to.
    said.clear()
    dock.engine.submit("xposition=")
    settle(12)
    truthy("an empty value is refused",
           any("give it a value" in ln for ln in said))

    # Every pair on the line is attempted, not just those before the first
    # complaint -- the whole line went into history either way, so
    # replaying it used to do more than running it had.
    said.clear()
    dock.engine.submit("xposition=6 mm nosuch=1 zposition=8 mm")
    settle(15)
    truthy("a bad name in the middle is reported",
           any("not on this panel" in ln for ln in said))
    check("  and the pairs around it still land",
          [round(v, 3) for v in slab.Placement.Base], [6.0, 0.0, 8.0])

    dock.engine.cancel()
    settle(25)

    # check runs nothing. open() is where a command runs now, so without a
    # guard `check transform` moved the object, printed "nothing was run",
    # and left a task dialog registered -- which blocks every panel
    # command after it.
    was = [round(v, 3) for v in slab.Placement.Base]
    select()
    dock.engine.submit("check transform")
    settle(25)
    check("check opens no panel", panels.is_open(), False)
    check("  and leaves nothing registered for FreeCAD",
          bool(Gui.Control.activeDialog()), False)
    check("  and moves nothing",
          [round(v, 3) for v in slab.Placement.Base], was)
    check("  and the engine is idle after it", dock.engine.state, "idle")

    stop()
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

    # Std_Placement -- fourteen fields, and a quantity that has to survive
    # the trip through FreeCAD's parser to mean anything.
    select("Slab")
    dock.engine.submit("placement")
    settle()
    truthy("placement opens a panel", panels.is_open())
    names = {panels.key_for(f.name) for f in panels.fields()}
    truthy("  offering more fields than transform does", len(names) >= 12)
    truthy("  named the same way", "xpos" in names or "xposition" in names)
    dock.engine.submit("xpos=30 mm zpos=3/4 in")
    settle(12)
    dock.engine.submit("done")
    settle(35)
    check("both landed, from one line",
          [round(v, 3) for v in slab.Placement.Base], [30.0, 0.0, 19.05])
    check("  and it closed", panels.is_open(), False)

    # A combo is set by naming it, and its choices are what it offers.
    select("Slab")
    dock.engine.submit("placement")
    settle()
    combos = [f for f in panels.fields() if f.kind == "choice"]
    truthy("a panel's combo boxes are readable", bool(combos))
    truthy("  offering what the combo offers", len(combos[0].choices) >= 2)
    dock.engine.cancel()
    settle(20)
    check("cancelling closes it", panels.is_open(), False)

    # FreeCAD shows one task dialog at a time and refuses a second, so a
    # panel we finished but left registered would block every panel
    # command after it.
    check("FreeCAD agrees no dialog is left registered",
          bool(Gui.Control.activeDialog()), False)

    # Part_Primitives -- the one that matters. Its combo swaps a whole
    # QStackedWidget page, so the fields after it are not the fields
    # before it. A step that held its widget would write into a page
    # nobody is looking at.
    Gui.activateWorkbench("PartWorkbench")
    settle(8)
    before = {o.Name for o in doc.Objects}
    Gui.Selection.clearSelection()
    dock.engine.submit("primitive")
    settle()
    truthy("primitive opens a panel", panels.is_open())

    # Buttons by role, never by label. Qt translates a QDialogButtonBox's
    # standard buttons, so pressing "ok" by its text worked in English and
    # nowhere else. This panel is also the one whose accept button reads
    # "Create" rather than "OK", so the label never sufficed anyway.
    roles = panels.by_role()
    truthy("the panel's buttons carry roles", bool(roles))
    truthy("  including one that means yes",
           bool(set(roles) & set(panels.ACCEPTING)))
    truthy("  and one that means no",
           bool(set(roles) & set(panels.REFUSING)))
    accepting = roles.get("AcceptRole")
    truthy("  and yes is Create here, not OK",
           accepting is not None
           and "create" in (accepting.text() or "").replace("&", "").lower())
    truthy("so it can be finished", panels.can_finish())
    first = {panels.key_for(f.name) for f in panels.fields()}
    truthy("  showing the plane page to begin with", "planelength" in first)
    dock.engine.submit("primitivetype=Cylinder")
    settle(20)
    after_choice = {panels.key_for(f.name) for f in panels.fields()}
    truthy("  and the page under it swaps to match",
           any(k.startswith("cylinder") for k in after_choice))

    # The number behind the text, not the text. setText changed what the
    # box showed and left its value where it was, so the panel read 4 mm
    # on screen and built a cylinder of 2 -- an assertion on the built
    # object is the only one that would have caught it.
    dock.engine.submit("cylinderradius=4 mm")
    settle(15)
    dock.engine.submit("done")
    settle(35)
    made = sorted({o.Name for o in doc.Objects} - before)
    check("  builds the one that was chosen", made, ["Cylinder"])
    built = doc.getObject(made[0]) if made else None
    check("  at the size it was given, not the one it displayed",
          round(built.Radius.Value, 3) if built else None, 4.0)
    check("  and closes", panels.is_open(), False)

    dock.engine.submit("close!")


def _errors_from(dock, line):
    """Submit a line and answer what it complained about."""
    said = []
    stop = dock.bus.subscribe(
        lambda m: said.append(m.text) if m.kind == "error" else None)
    try:
        dock.engine.submit(line)
        QtWidgets.QApplication.processEvents()
    finally:
        stop()
    return said


def suite_hazards(dock):
    print("\n7c. what would end the session is refused (GH #61, #73)")
    from fccli import panels as _panels

    # GH #61. FreeCAD sets a checkable command's button state without
    # checking there is a button, and a session that has built no toolbar
    # menu has none for Std_ToggleToolBarLock. The detector has to find it
    # in a real GUI, or the refusal below is passing for the wrong reason.
    armed = "Std_ToggleToolBarLock" in _panels.actionless_toggles()
    truthy("a toggle FreeCAD built no button for is found, at startup", armed)
    if armed:
        # Only with the guard proven armed. Typing this line at a session
        # where it is not is how the instance dies, and a check that takes
        # the harness with it when it fails reports nothing.
        truthy("  and running it is refused, not attempted",
               any("takes FreeCAD down" in text
                   for text in _errors_from(dock, "lock_toolbars")))
        # A bang forces past a refusal; there is nothing behind this one.
        truthy("  a bang does not buy a segfault",
               any("takes FreeCAD down" in text
                   for text in _errors_from(dock, "lock_toolbars!")))
    no_dialog("no dialog appeared")

    # GH #73. Part's filters leave a gate that outlives the document, and
    # select used to report success over the empty selection it made.
    doc = App.ActiveDocument or App.newDocument("gate")
    box = doc.addObject("Part::Box", "GateBox")
    other = doc.addObject("Part::Box", "GateBox2")
    doc.recompute()
    dock.engine.submit("vertex_selection")
    QtWidgets.QApplication.processEvents()
    try:
        said = _errors_from(dock, f"select {box.Name}")
        truthy("a gate that swallows the selection is a fault, not a claim",
               any("no_selection_filters" in text for text in said))
        check("  and nothing is half-selected behind it",
              Gui.Selection.getSelection(), [])
    finally:
        dock.engine.submit("no_selection_filters")
        QtWidgets.QApplication.processEvents()
    dock.engine.submit(f"select {box.Name}")
    QtWidgets.QApplication.processEvents()
    check("with the gate lifted, select holds what it names",
          [o.Name for o in Gui.Selection.getSelection()], [box.Name])

    # An edge filter takes a subelement and refuses the whole object, so
    # a line naming both is where a subelement can vouch for its own
    # parent. It must not: the parent was refused.
    Gui.Selection.clearSelection()
    dock.engine.submit("edge_selection")
    QtWidgets.QApplication.processEvents()
    try:
        truthy("a subelement does not vouch for its own parent",
               any(f"did not take {box.Name}" in text
                   for text in _errors_from(
                       dock, f"select {box.Name}.Edge1, {box.Name}")))
        truthy("  the refused name is the one reported",
               any(f"did not take {other.Name}" in text
                   for text in _errors_from(
                       dock, f"select {box.Name}.Edge1, {other.Name}")))
        truthy("  and the subelement the filter allows is no fault",
               not _errors_from(dock, f"select {box.Name}.Edge1"))
    finally:
        dock.engine.submit("no_selection_filters")
        QtWidgets.QApplication.processEvents()
    dock.engine.submit(f"select {box.Name}.Edge1, {other.Name}")
    QtWidgets.QApplication.processEvents()
    check("ungated, a subelement and another whole object both land",
          sorted((e.ObjectName, tuple(e.SubElementNames))
                 for e in Gui.Selection.getSelectionEx()),
          [(box.Name, ("Edge1",)), (other.Name, ())])
    Gui.Selection.clearSelection()
    doc.removeObject(box.Name)
    doc.removeObject(other.Name)
    doc.recompute()


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
        suite_hazards(dock)
        suite_roundtrip(dock)
        suite_shutdown(dock)
    except Exception:
        failed_early = traceback.format_exc()
        print(failed_early)

    try:
        # A panel still up holds the application open: the run finished,
        # wrote its result, and then sat there. Whatever aborted the suite
        # is reported above; this is only so the process ends.
        from fccli import panels as _panels
        if _panels.is_open():
            ESCAPED.append("a task panel was left open")
            _panels.dismiss()
    except Exception:
        pass

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
