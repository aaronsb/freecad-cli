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
        if dock is not None:
            dock.persist = False       # this window's shape is not a setting
        suite_dock(dock)
        suite_keys(dock)
        doc = suite_geometry(dock)
        suite_undo(dock, doc)
        suite_picker(dock)
        suite_dock_geometry(dock)
        suite_units(dock)
        suite_check(dock, doc)
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
