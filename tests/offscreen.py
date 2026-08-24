# SPDX-License-Identifier: LGPL-2.1-or-later

"""Everything checkable without a FreeCAD GUI.

    QT_QPA_PLATFORM=offscreen python3 tests/offscreen.py

The grammar, the engine, the factory, completion, units, colouring,
curation and the history ring, with a real Qt application but no main
window. What needs a window is in bvt.py; what needs a second process is
in socket_host.py.

It was called test_spike.py while there was a spike. The sections are
numbered in the order they were written rather than renumbered each time,
so a failure keeps the same name from run to run.
"""

import os
import subprocess as _sh
import sys
import tempfile
import time

sys.path[:0] = [
    "/usr/lib/freecad/lib",
    "/usr/lib/freecad/Mod/Draft",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Run against a scratch XDG root. The suite builds a real Session, which
# means a real History at the real path, and one of the checks below is
# "history clear empties the ring" -- so without this, running the tests
# truncated the operator's own command history. Set before fccli is
# imported: the paths are module-level constants.
_XDG = tempfile.mkdtemp(prefix="fccli-tests-")
os.environ["XDG_STATE_HOME"] = os.path.join(_XDG, "state")
os.environ["XDG_DATA_HOME"] = os.path.join(_XDG, "data")

import FreeCAD as App  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from fccli.bus import Bus, ERROR, LIVE, RESULT  # noqa: E402
from fccli.engine import Engine  # noqa: E402
from fccli.completion import candidates as _complete  # noqa: E402
from fccli import __version__ as _fccli_version  # noqa: E402
from fccli.grammar import REGISTRY  # noqa: E402
from fccli.session import History as _History  # noqa: E402
from fccli.keyfilter import KeyFilter  # noqa: E402
from fccli.widget import Console  # noqa: E402
import fccli.verbs  # noqa: E402,F401

PASS, FAIL = [], []


def check(label, got, want):
    (PASS if got == want else FAIL).append(label)
    mark = "ok  " if got == want else "FAIL"
    extra = "" if got == want else f"   got {got!r} want {want!r}"
    print(f"  {mark} {label}{extra}")


def press(widget, text, key=None, mods=QtCore.Qt.NoModifier):
    key = key if key is not None else QtGui.QKeySequence(text)[0].key()
    ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, mods, text)
    QtWidgets.QApplication.sendEvent(widget, ev)


def type_into(app, s):
    """Send each key to whatever currently holds focus, as Qt really does.

    The filter only fires on the first keystroke: it moves focus to the
    console, and subsequent keys reach the console natively.
    """
    for ch in s:
        press(app.focusWidget(), ch, QtGui.QKeySequence(ch)[0].key())
        app.processEvents()


def main():
    app = QtWidgets.QApplication(sys.argv)
    App.newDocument("spike")

    bus = Bus()
    errors, results = [], []
    bus.subscribe(lambda m: errors.append(m.text) if m.kind == ERROR else None)
    bus.subscribe(lambda m: results.append(m.data.get("replay"))
                  if m.kind == RESULT else None)
    live = []
    bus.subscribe(lambda m: live.append(m.text) if m.kind == LIVE else None)
    engine = Engine(bus, REGISTRY, picker=None)
    from fccli import dirty, units as _units
    dirty.install()
    entry_schema = _units.current_name()   # restored before returning

    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)
    viewport = QtWidgets.QWidget(window)        # stands in for the 3D view
    viewport.setFocusPolicy(QtCore.Qt.StrongFocus)
    from fccli.session import Session
    session = Session(engine, bus)
    console = Console(engine, window, session=session)
    console.submitted.connect(session.submit)
    editor = QtWidgets.QLineEdit(window)        # stands in for Python console
    for w in (viewport, console, editor):
        layout.addWidget(w)
    window.show()

    console.cancelled.connect(engine.cancel)
    kf = KeyFilter(console, engine)
    kf.install()

    print("\n1. keys reach the command line while the viewport has focus")
    viewport.setFocus()
    app.processEvents()
    check("viewport starts with focus", app.focusWidget() is viewport, True)
    type_into(app, "line")
    check("typed text landed in the console", console.input_text(), "line")
    check("focus moved to the console", app.focusWidget() is console, True)
    check("filter fired once, then focus carried it", kf.stats["usurped"], 1)

    # A viewport click steals focus back; the next keystroke must be caught
    # again. This is the ping-pong the design depends on.
    console.set_input("")
    viewport.setFocus()
    app.processEvents()
    type_into(app, "pl")
    check("keys recaptured after a viewport click", console.input_text(), "pl")

    print("\n2. real editors keep their keys")
    console.set_input("")
    editor.setFocus()
    app.processEvents()
    type_into(app, "abc")
    check("editor kept its own text", editor.text(), "abc")
    check("console stayed empty", console.input_text(), "")

    print("\n3. digits route by step")
    viewport.setFocus()
    app.processEvents()
    ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_1,
                         QtCore.Qt.NoModifier, "1")
    check("idle: digit passes through to FreeCAD", kf.should_usurp(ev), False)
    engine.submit("circle")
    check("point step: digit is usurped", kf.should_usurp(ev), True)
    engine.cancel()
    check("after cancel: passes through again", kf.should_usurp(ev), False)

    print("\n4. typed values and picks share one state machine")
    live.clear()
    engine.submit("polyline")
    engine.submit("0,0,0")
    engine.feed_point(App.Vector(25, 0, 0))
    engine.submit("@0,25,0")
    engine.feed_point(App.Vector(0, 25, 0))
    engine.submit("")
    check("command completed", len(results), 1)
    check("mouse picks replay as text, canonicalized",
          results[-1], "polyline 0,0,0 25,0,0 25,25,0 0,25,0")
    check("the command built up on one accumulating line", live, [
        "polyline",
        "polyline 0,0,0",
        "polyline 0,0,0 25,0,0",
        "polyline 0,0,0 25,0,0 25,25,0",
        "polyline 0,0,0 25,0,0 25,25,0 0,25,0",
    ])

    print("\n4b. typed values echo back in canonical form")
    _units.set_schema("Internal")   # pin it next to the assertion
    live.clear()
    for line in ["box", "0,0,0", "10", "3/8in", "2.5cm"]:
        engine.submit(line)
    check("units normalized on input", results[-1],
          "box 0,0,0 10.00mm 9.525mm 25.00mm")

    print("\n4c. shell builtins run without dialogs")
    import os
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "fccli_spike.FCStd")
    if os.path.exists(tmp):
        os.remove(tmp)
    engine.submit("new spikedoc")
    check("zero-step verb runs on Enter", App.ActiveDocument.Name, "spikedoc")
    engine.submit("box 0,0,0 10 10 10")
    engine.submit(f"save {tmp}")
    check("save took the path instead of a dialog", os.path.exists(tmp), True)
    engine.submit("close")
    engine.submit(f"open {tmp}")
    check("reopened with its contents",
          [o.Name for o in App.ActiveDocument.Objects], ["Box"])
    errors.clear()
    engine.submit("man polyline")
    check("free-text step does not trigger a restart", errors, [])

    engine.submit("new dirtydoc")
    engine.submit("box 0,0,0 5 5 5")
    errors.clear()
    engine.submit("close")
    check("close refuses to discard unsaved work", len(errors), 1)
    engine.submit("close!")
    check("the ! suffix forces it through",
          "dirtydoc" not in App.listDocuments(), True)
    os.remove(tmp)

    print("\n5. terminal conventions")
    console.set_input("")
    console.append_history("polyline 0,0,0 10,0,0")
    console._history_step(-1)
    check("Up recalls the parameterized form",
          console.input_text(), "polyline 0,0,0 10,0,0")
    console.set_input("poly")
    console._refresh_suggestion()
    check("ghost suggestion from history",
          console._suggestion, "line 0,0,0 10,0,0")
    console.set_input("po")
    console._complete()
    first = console.input_text()
    console._complete()
    second = console.input_text()
    check("Tab completes to a real verb", first in ("point", "polyline"), True)
    check("Tab cycles through the candidates", first != second, True)
    check("cycling reaches polyline", {first, second}, {"point", "polyline"})

    print("\n5b. history replay reproduces the geometry")
    engine.submit("new replaydoc")
    # Drive through the console so history is written the way typing does.
    def enter(text):
        console.set_input(text)
        console._submit()
    enter("polyline")
    enter("0,0,0")
    engine.feed_point(App.Vector(30, 0, 0))
    engine.feed_point(App.Vector(30, 40, 0))
    enter("close")
    first = App.ActiveDocument.Objects[-1]
    recalled = [h for h in console._history if h.startswith("polyline")][-1]
    check("the mouse-driven command is in history as text",
          recalled, "polyline 0,0,0 30,0,0 30,40,0 close")
    enter(recalled)
    second = App.ActiveDocument.Objects[-1]
    check("replaying it makes a second object", second.Name != first.Name, True)
    check("with identical points",
          [tuple(p) for p in second.Points],
          [tuple(p) for p in first.Points])

    print("\n4d. dirty tracking sees changes from anywhere")
    engine.submit("new observed")
    check("a fresh document is clean", dirty.is_dirty(), False)
    # A change made without the command line, as a toolbar click would be.
    obj = App.ActiveDocument.addObject("Part::Box", "Outside")
    obj.Length = 30
    App.ActiveDocument.recompute()
    check("an outside change marks it dirty", dirty.is_dirty(), True)
    outside = os.path.join(os.environ.get("TMPDIR", "/tmp"), "fccli_outside.FCStd")
    engine.submit(f"save {outside}")
    check("saving clears it", dirty.is_dirty(), False)
    obj.Width = 12
    App.ActiveDocument.recompute()
    check("editing again re-dirties it", dirty.is_dirty(), True)
    engine.submit("close!")
    os.path.exists(outside) and os.remove(outside)

    print("\n4e. undo is one step per typed line")
    engine.submit("new undodoc")
    doc = App.ActiveDocument
    engine.submit("box 0,0,0 10 10 10")
    engine.submit("circle 0,0,0 5")
    check("both objects exist", len(doc.Objects), 2)
    check("the undo stack is labelled with the command",
          doc.UndoNames[0].startswith("circle"), True)
    engine.submit("undo")
    check("undo removes one command's worth", len(doc.Objects), 1)
    engine.submit("redo")
    check("redo puts it back", len(doc.Objects), 2)
    engine.submit("close!")

    print("\n4f. units follow FreeCAD's schema")
    from fccli import units as U
    before = U.current_name()
    engine.submit("new unitdoc")
    results.clear()
    U.set_schema("Internal")
    engine.submit("circle 0,0,0 9.525")
    check("internal renders mm", results[-1], "circle 0,0,0 9.525mm")
    check("a bare number means mm", U.preferred(), "mm")
    U.set_schema("ImperialBuilding")
    check("a bare number now means in", U.preferred(), "in")
    # An explicit unit is honoured whatever the schema, and rendered in it.
    engine.submit("circle 0,0,0 9.525mm")
    check("imperial building renders fractions",
          results[-1], 'circle 0,0,0 3/8"')
    engine.submit("box 0,0,0 3/8in 1ft 25.4mm")
    check("mixed input unifies on output",
          results[-1], 'box 0,0,0 3/8" 1\' 1"')
    # A bare number takes the schema's unit rather than internal mm, so the
    # number someone types means what their readings mean.
    engine.submit("circle 0,0,0 12")
    check("a bare number is read in the schema's unit",
          results[-1], "circle 0,0,0 1'")
    # Every rendering must survive being read back, since the echo is what
    # Up recalls.
    from FreeCAD import Units as _U
    lossy = []
    for token, want in (('3/8"', 9.525), ("1'", 304.8), ('1"', 25.4)):
        try:
            if abs(_U.Quantity(token).Value - want) > 1e-7:
                lossy.append(token)
        except Exception:
            lossy.append(token)
    check("every rendered token round-trips exactly", lossy, [])
    engine.submit("close!")
    U.set_schema(entry_schema)

    print("\n4g. check validates without running")
    _units.set_schema("Internal")
    engine.submit("new checkdoc")
    infos_c = []
    stop = bus.subscribe(lambda m: infos_c.append(m.text)
                         if m.kind == "info" else None)
    before_count = len(App.ActiveDocument.Objects)

    engine.submit("check box 0,0,0 40 30 20")
    joined = " | ".join(infos_c)
    check("a valid command reports what would run",
          "would run:  box 0,0,0 40.00mm 30.00mm 20.00mm" in joined, True)
    check("  and what it would create", "Part::Box" in joined, True)
    check("  without creating anything",
          len(App.ActiveDocument.Objects), before_count)

    infos_c.clear()
    engine.submit("check box 0,0,0 40 zz 20")
    check("a bad token is named",
          any("'zz' is not a number" in i for i in infos_c), True)

    infos_c.clear()
    engine.submit("check polylne 0,0,0")
    check("a typo suggests its fix",
          any("did you mean" in i and "polyline" in i for i in infos_c), True)

    infos_c.clear()
    engine.submit("check box 0,0,0 40 30")
    check("an incomplete command says what is missing",
          any("still wants" in i for i in infos_c), True)

    check("check never touched the document",
          len(App.ActiveDocument.Objects), before_count)
    stop()
    engine.submit("close!")

    print("\n5c. the factory: generated and patched verbs")
    from fccli.factory import load_descriptor, register_all
    from fccli.patches import PatchSet
    from fccli.grammar import Registry as _Registry
    desc = load_descriptor()
    check("a descriptor is shipped", desc is not None, True)
    if desc:
        fresh = _Registry()
        counts = register_all(fresh, tier0=True, patches=PatchSet())
        check("tier 0 covers the command registry", counts["tier0"] > 900, True)
        check("tier 1 generates from types", counts["tier1"] > 150, True)
        check("patches applied", counts["patched"] >= 7, True)
        box = fresh.get("box")
        check("a patch orders the steps",
              [s.id for s in box.steps], ["Length", "Width", "Height"])
        cyl = fresh.get("cylinder")
        check("a patch promotes a property to an inline option",
              [o.name for st in cyl.steps for o in st.options], ["Angle"])
        pad = fresh.get("pad")
        check("an unpatched type is still a usable verb",
              pad is not None and len(pad.steps) > 3, True)
        check("enumerations become choices",
              any(st.choices for st in pad.steps), True)
        # A patch must not shadow a hand-written verb.
        check("hand-written verbs survive the factory",
              REGISTRY.get("polyline").emit.__name__, "_emit_polyline")
        # box is the sharp case: the factory generates one from Part::Box.
        import fccli.verbs as _v
        register_all(REGISTRY, tier0=False)
        check("  including where a generated verb wants the same name",
              [st.id for st in REGISTRY.get("box").steps],
              ["corner", "length", "width", "height"])
        check("  and the generated one stays reachable",
              REGISTRY.get("part_box") is not None, True)

    errors.clear()
    infos = []
    bus.subscribe(lambda m: infos.append(m.text)
                  if m.kind == "info" else None)
    engine.submit("man circle")
    check("man renders a page", any("NAME" in i for i in infos), True)
    check("  with units on quantity steps",
          any("quantity in mm" in i for i in infos), True)
    check("  and the inline options",
          any("option Diameter" in i for i in infos), True)
    infos.clear()
    engine.submit("help")
    check("help is man, and bare it lists",
          any("hand-written commands" in i for i in infos), True)
    engine.submit("man nosuchthing")
    check("man refuses an unknown topic", len(errors), 1)

    engine.submit("alias tb box")
    check("alias defines one", REGISTRY.get("tb").name, "box"
          if REGISTRY.get("box") else None)
    engine.submit("unalias tb")
    check("unalias stops it resolving", REGISTRY.get("tb"), None)

    print("\n5d. completion: verbs first, then arguments")
    from fccli.completion import candidates as _cand
    _units.set_schema("Internal")
    engine.submit("new compdoc")
    App.ActiveDocument.addObject("Part::Box", "Bracket")
    session.history.entries[:] = ["circle 0,0,0 20"]

    def hits(text):
        return _cand(engine, text, history=session.history)[2]

    check("a first token completes verbs", "circle" in hits("circ"), True)
    check("an argument does not complete verbs",
          any(h in REGISTRY.names() for h in hits("circle 0")), False)
    check("  it completes the coordinate instead", hits("circle 0"), ["0,0,0"])
    check("a bare number takes the schema's unit",
          hits("circle 0,0,0 2"), ["2mm"])
    check("a step that holds a command says so",
          "polyline" in hits("man pol"), True)
    check("  including check", "polyline" in hits("check pol"), True)
    check("a selection step completes document objects",
          hits("move Brac"), ["Bracket"])
    check("the schema step completes schemas",
          all("imperial" in h for h in hits("units imp")), True)

    # Tab walks a remembered command out one argument at a time, for any
    # verb -- nothing here is named or special-cased.
    session.history.entries[:] = ["polyline 0,0,0 40,0,0 close"]
    walked, line = [], "polyline"
    for _ in range(4):
        got = hits(line)
        if not got:
            break
        head = line.rpartition(" ")[0]
        line = (head + " " + got[0]) if head else got[0]
        walked.append(line)
    session.history.entries[:] = []
    check("a choice step lists its choices on the space",
          hits("zoom ")[:3], ["all", "extents", "in"])
    check("  and narrows as you type", hits("zoom ex"), ["extents"])
    check("  including the named views", hits("zoom f"), ["front"])
    session.history.entries[:] = ["polyline 0,0,0 40,0,0 close"]

    check("Tab walks a remembered command out",
          walked[-1] if walked else None, "polyline 0,0,0 40,0,0 close")
    engine.submit("close!")

    print("\n5e. families: one verb for a spread-out group")
    from fccli.families import families as _families, split_command
    fresh2 = _Registry()
    counts2 = register_all(fresh2, tier0=True, patches=PatchSet())
    check("families were registered", counts2.get("families", 0) > 20, True)
    check("  and none displaced a name already taken",
          counts2.get("family_shadowed", 0) > 0, True)

    constrain = fresh2.get("constrain")
    check("a family verb exists", constrain is not None, True)
    if constrain:
        choices = constrain.steps[0].choices
        check("  with the members as choices",
              all(c in choices for c in
                  ("coincident", "parallel", "perpendicular")), True)

    # Nothing here names a command: the grouping is read off the registry.
    fam = _families(load_descriptor()["commands"])
    check("the grouping is derived, not listed",
          "view" in fam and "snap" in fam, True)
    check("an acronym is not mistaken for a family", "b" in fam, False)
    check("FreeCAD's own UI prefixes are not families",
          "comp" in fam, False)
    check("Module_CamelCase splits into head and rest",
          split_command("Sketcher_ConstrainCoincident"),
          ("Sketcher", ["Constrain", "Coincident"]))

    print("\n5f. syntax colouring carries meaning")
    from fccli.parsing import parse_point as _pp, parse_quantity as _pq
    _units.set_schema("Internal")

    spans = _pp("10,20,30", App.Vector(0, 0, 0)).spans
    check("a coordinate is coloured by axis",
          [sp.role for sp in spans], ["axis_x", "axis_y", "axis_z"])
    check("  and a bad component still reads as an error",
          [sp.role for sp in _pp("10,20,zz", App.Vector(0, 0, 0)).spans][-1],
          "bad")
    polar = _pp("100<45", App.Vector(0, 0, 0)).spans
    check("polar distance and angle are told apart",
          sorted({sp.role for sp in polar}),
          ["dim_angle", "dim_length", "sep"])
    check("a dimension is named by FreeCAD, not a table here",
          _pq("10mm^2").spans[0].role, "dim_area")
    check("  angles too", _pq("45deg").spans[0].role, "dim_angle")
    check("  and a dimensionless number is scalar",
          _pq("3", unit_hint="").spans[0].role, "scalar")

    # Italic says the command line supplied it, not the person.
    check("a bare number is marked as having an implied unit",
          _pq("12", unit_hint="mm").spans[0].implicit, True)
    check("  a stated one is not", _pq("12mm", unit_hint="mm").spans[0].implicit,
          False)

    from fccli.highlight import PALETTE
    check("every span role has a colour",
          [sp.role for sp in spans if sp.role not in PALETTE], [])

    print("\n5g. screenshot reports where it wrote")
    from fccli.shell import _shot_path
    target = os.path.join(os.environ.get("TMPDIR", "/tmp"), "fccli-shot-test")
    check("a path without a suffix gets one",
          _shot_path(target).endswith(".png"), True)
    check("  an explicit suffix is kept",
          _shot_path(target + ".jpg").endswith(".jpg"), True)
    auto = _shot_path(None)
    check("  and an absent path is numbered under the document",
          auto.endswith(".png") and "shots" in auto, True)

    print("\n5h. place, recall, place again")
    _units.set_schema("Internal")
    engine.submit("new placedoc")
    session.history.entries[:] = []
    session.history.typed.clear()

    # Everything typeable first; the pick is what commits the command.
    engine.submit("circle diameter 10")
    check("a point is asked for last", engine.current_step().kind, "point")
    engine.feed_point(App.Vector(15, 30, 0))
    check("the click completed it", len(App.ActiveDocument.Objects), 1)
    line = session.history.entries[-1]
    check("history holds the whole line", line, "circle diameter 10.00mm 15,30,0")
    check("  and knows what the keyboard contributed",
          session.history.recall(line), "circle diameter 10.00mm")

    console.set_input("")
    console._history_step(-1)
    check("Up shows the whole command", console.input_text(), line)
    check("  with the clicked tail marked", console.picked_from(), 23)
    console._submit()
    check("Enter re-arms it for a click", engine.current_step().kind, "point")
    engine.feed_point(App.Vector(-40, 5, 0))
    placed = [tuple(o.Placement.Base) for o in App.ActiveDocument.Objects]
    check("the second lands where the second click was",
          placed, [(15.0, 30.0, 0.0), (-40.0, 5.0, 0.0)])

    # Editing a recalled line makes it yours again.
    console._history_step(-1)
    console.set_input(console.input_text() + " ")
    check("an edited line is no longer up for grabs",
          console.picked_from(), None)

    print("\n5i. arguments find their step by kind")
    engine.submit("circle 0,0,0 20")
    check("the old order still works",
          [round(c) for c in App.ActiveDocument.Objects[-1].Placement.Base],
          [0, 0, 0])
    engine.submit("circle 20 5,5,0")
    check("  and so does the new one",
          [round(c) for c in App.ActiveDocument.Objects[-1].Placement.Base],
          [5, 5, 0])
    engine.submit("box 0,0,0 40 30 20")
    box = App.ActiveDocument.Objects[-1]
    check("same-kind arguments stay positional",
          (box.Length.Value, box.Width.Value, box.Height.Value),
          (40.0, 30.0, 20.0))
    engine.submit("close!")

    print("\n5j. Enter on an empty prompt repeats; Tab shows recent")
    from fccli.completion import candidates as _c2
    _units.set_schema("Internal")
    engine.submit("new repeatdoc")
    session.history.entries[:] = []
    session.history.typed.clear()

    empty = _c2(engine, "", history=session.history)[2]
    check("Tab on an empty line is not the whole registry", len(empty) < 40,
          True)

    engine.submit("circle diameter 10")
    engine.feed_point(App.Vector(15, 30, 0))
    recent = _c2(engine, "", history=session.history)[2]
    check("Tab then offers what was just run",
          recent[0], "circle diameter 10.00mm")

    # Enter with nothing typed repeats -- the CAD convention, and with
    # points asked for last it is the placement loop.
    engine.submit("")
    check("it repeats the typed half", engine.verb.name, "circle")
    check("  and waits for a click", engine.current_step().kind, "point")
    engine.feed_point(App.Vector(-40, 5, 0))
    check("so a second lands where the second click was",
          [tuple(o.Placement.Base) for o in App.ActiveDocument.Objects],
          [(15.0, 30.0, 0.0), (-40.0, 5.0, 0.0)])

    # A fully typed command repeats verbatim; there is nothing to place.
    engine.submit("box 0,0,0 40 30 20")
    before = len(App.ActiveDocument.Objects)
    engine.submit("")
    check("a fully typed command repeats as it was",
          len(App.ActiveDocument.Objects), before + 1)
    engine.submit("close!")

    print("\n5k. scoping, and managing the ring")
    from fccli.completion import candidates as _c3, domains as _domains
    engine.submit("new scopedoc")
    # Scoping only matters once the thousand launchers are present.
    register_all(REGISTRY, tier0=True, patches=PatchSet())

    def count(text):
        return len(_c3(engine, text, history=session.history,
                       scope=session.scope)[2])

    wide = count("c")
    check("unscoped, a letter offers a lot", wide > 100, True)
    engine.submit("use sketcher")
    check("scoping narrows it", count("c") < wide // 3, True)
    scoped = _c3(engine, "c", history=session.history,
                 scope=session.scope)[2]
    check("  hand-written verbs are never hidden by a scope",
          all(v in scoped for v in ("check", "circle", "clear")), True)
    engine.submit("use off")
    check("clearing restores it", count("c"), wide)

    found = _domains(REGISTRY)
    check("domains are read off the verbs, not tagged",
          found.get("Sketcher", 0) > 50 and found.get("Part", 0) > 10, True)

    session.history.entries[:] = ["circle 0,0,0 20"]
    engine.submit("history clear")
    check("history clear empties the ring", session.history.entries, [])
    engine.submit("close!")

    print("\n5l. curation -- FreeCAD's own ranking")
    from fccli import curation as _cur
    from fccli.factory import load_descriptor as _load_desc
    _desc = _load_desc()
    curated = _cur.load(_desc)
    census = curated.census()
    check("every command lands in exactly one rank",
          sum(census.values()), len(_desc["commands"]))
    check("a toolbar command outranks a registry-only one",
          curated.rank("Part_Box") < curated.rank("Std_TestQuestion"), True)
    check("placement is read off the descriptor",
          curated.placement("Part_Box")[0], "Solids")
    check("adjacency is the rest of the toolbar",
          sorted(curated.adjacent("Part_Box")),
          ["Part_Cone", "Part_Cylinder", "Part_Sphere", "Part_Torus",
           "Part_Tube"])
    check("a command is never adjacent to itself",
          "Part_Box" in curated.adjacent("Part_Box"), False)

    _ranked = curated.order(REGISTRY, ["sketcher_bsplinedegree", "box"])
    check("order puts the promoted verb first", _ranked[0], "box")
    check("order keeps everything reachable", len(_ranked), 2)
    check("a hand-written verb outranks anything generated",
          curated.rank_of(REGISTRY.get("box"))
          < curated.rank_of(REGISTRY.get("sketcher_bsplinedegree")), True)
    check("a family ranks as its best member",
          curated.rank_of(REGISTRY.get("view")), _cur.PROMOTED)
    check("an accented label slugs to a typeable name",
          REGISTRY.get("bezier_curve") is not None, True)

    _groups = curated.choice_groups("view")
    check("a family's choices group by FreeCAD's own menus",
          len(_groups) > 4, True)
    check("  the biggest group leads",
          _groups[0][0], "Standard Views")
    check("  what FreeCAD filed nowhere comes last",
          _groups[-1][0], None)
    check("  and every member lands in exactly one group",
          sum(len(g[1]) for g in _groups),
          len(REGISTRY.get("view").steps[0].choices))
    check("a family whose members fill their toolbar falls back to siblings",
          bool(curated.neighbours(REGISTRY, REGISTRY.get("view"))), True)
    check("a two-member step is not worth grouping",
          curated.choice_groups("nonexistent_family"), [])

    print("\n5m. paths follow XDG, and still find the old files")
    from fccli import paths as _paths
    _saved = {k: os.environ.get(k) for k in ("XDG_STATE_HOME", "XDG_DATA_HOME")}
    os.environ["XDG_STATE_HOME"] = "/tmp/fccli-state"
    os.environ["XDG_DATA_HOME"] = "/tmp/fccli-data"
    check("history is state, not data",
          _paths.state("history"), "/tmp/fccli-state/fccli/history")
    check("aliases are data", _paths.data("aliases"),
          "/tmp/fccli-data/fccli/aliases")
    for k, v in _saved.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    _fresh = os.path.join(tempfile.mkdtemp(), "history")
    check("an absent new path falls back to the old one",
          _paths.readable(_fresh, "history"), _paths.legacy("history")
          if os.path.exists(_paths.legacy("history")) else _fresh)

    print("\n5n. frecency -- ranking by what somebody does")
    from fccli import frecency as _frec
    _now = 1_700_000_000
    check("today weighs most", _frec.recency_weight(_now, _now), 16)
    check("a year ago weighs least",
          _frec.recency_weight(_now, _now - 400 * 86400), 1)
    check("no timestamp degrades to frequency, not to zero",
          _frec.score(5, 0, _now), 5)
    check("recent beats frequent-but-stale",
          _frec.score(2, _now, _now) > _frec.score(6, _now - 90 * 86400, _now),
          True)
    _stats = {"wall": (6, _now)}
    check("an unused name keeps the order it arrived in",
          _frec.partition(["zoom", "wall", "box"],
                          lambda n: _stats.get(n, (0, 0)), _now),
          ["wall", "zoom", "box"])
    check("nothing is dropped by ranking",
          len(_frec.partition(["a", "b"], lambda n: (0, 0), _now)), 2)

    print("\n5o. history persists with timestamps")
    _hp = os.path.join(tempfile.mkdtemp(), "history")
    _h = _History(path=_hp)
    _h.add("box 0,0,0 10mm", when=_now)
    check("it round-trips through the file",
          _History(path=_hp).entries, ["box 0,0,0 10mm"])
    check("  keeping when it happened",
          _History(path=_hp).stamps.get("box 0,0,0 10mm"), _now)
    _old = os.path.join(tempfile.mkdtemp(), "history")
    with open(_old, "w", encoding="utf-8") as fh:
        fh.write("circle 0,0,0 5mm\n")
    check("a file written before timestamps still reads",
          _History(path=_old).entries, ["circle 0,0,0 5mm"])
    check("  with an epoch frecency treats as unknown",
          _History(path=_old).usage(), [("circle 0,0,0 5mm", 0)])

    print("\n5p. a habit outranks FreeCAD's own ordering")
    _hab = _History(path=os.path.join(tempfile.mkdtemp(), "history"))
    _cold = _complete(engine, "b", history=None)[2]
    check("cold, equal ranks fall back to alphabetical",
          _cold.index("b_spline") < _cold.index("box"), True)
    for _ in range(6):
        _hab.add("boolean 1,1,1", when=int(time.time()))
        _hab.add("box 0,0,0 1mm", when=int(time.time()))
    _warm = _complete(engine, "b", history=_hab)[2]
    check("a used verb overtakes an unused one that outsorts it",
          _warm.index("box") < _warm.index("b_spline"), True)
    check("  and both are still offered",
          {"box", "b_spline"} <= set(_warm), True)
    check("the two used verbs take the front",
          set(_warm[:2]), {"box", "boolean"})

    print("\n5q. the click cue fades as the habit forms")
    from fccli.actions import ActionBridge

    class _Cue:
        session = type("S", (), {"history": _History(
            path=os.path.join(tempfile.mkdtemp(), "history"))})()
        def __init__(self): self.lines = []
        def write(self, text, role=None): self.lines.append(text)
        def set_input(self, text): pass

    _con = _Cue()
    _bridge = ActionBridge(engine, _con, REGISTRY)
    _bridge._suggest(REGISTRY.get("box"))
    check("an unfamiliar verb names its neighbours",
          any("cylinder" in ln for ln in _con.lines), True)
    for _ in range(6):
        _Cue.session.history.add(f"box 0,0,{_} 1mm", when=int(time.time()))
    _con.lines.clear()
    _bridge._suggest(REGISTRY.get("box"))
    check("a familiar one says nothing", _con.lines, [])
    _bridge.cue = False
    _con2 = _Cue()
    _bridge.console = _con2
    _bridge._suggest(REGISTRY.get("box"))
    check("the cue can be turned off outright", _con2.lines, [])

    print("\n5q2. a full ring keeps learning")
    _ring = _History(path=os.path.join(tempfile.mkdtemp(), "history"), limit=5)
    for i in range(5):
        _ring.add(f"box 0,0,{i} 1mm", when=_now)
    _full = _ring.revision
    check("the ring is at its limit", len(_ring.entries), 5)
    _ring.add("circle 0,0,0 2mm", when=_now)
    check("  adding past it does not change the length",
          len(_ring.entries), 5)
    check("  but the revision moves, so a cache keyed on it rebuilds",
          _ring.revision > _full, True)
    check("  the oldest line is gone", "box 0,0,0 1mm" in _ring.entries, False)
    check("  and its timestamp went with it",
          "box 0,0,0 1mm" in _ring.stamps, False)
    check("  the tally reflects what is left",
          _frec.tally(_ring.usage()).get("circle"), (1, _now))

    print("\n5r. the version banner reports where the code came from")
    from fccli import build_info as _bi
    _bi._CACHE = None
    check("in a checkout, live git wins over a release stamp",
          _bi.info().get("source"), "git")
    check("  and the commit is this one",
          _bi.info().get("commit", "").split("-")[0],
          _sh.check_output(["git", "rev-parse", "--short", "HEAD"],
                           text=True).strip())
    check("describe carries version, commit and date",
          _bi.describe().startswith(_fccli_version + "+"), True)
    _bi._CACHE = None

    print("\n5s. edges the happy path does not reach")
    from fccli.factory import _label as _factory_label
    from fccli.shell import _columns as _cols
    # Frecency bucket boundaries: each edge belongs to the bucket below it.
    for _days, _want in ((0, 16), (7, 8), (8, 4), (30, 4),
                         (31, 2), (180, 2), (181, 1)):
        check(f"  {_days}d weighs {_want}",
              _frec.recency_weight(_now, _now - _days * 86400), _want)
    check("a timestamp in the future is not trusted",
          _frec.recency_weight(_now, _now + 86400), 1)
    check("a zero count scores zero however recent",
          _frec.score(0, _now, _now), 0)
    check("partition of nothing is nothing", _frec.partition([], dict, _now), [])
    check("all-unused keeps the incoming order exactly",
          _frec.partition(["c", "a", "b"], lambda n: (0, 0), _now),
          ["c", "a", "b"])

    # Curation with nothing to read -- the state before a descriptor loads.
    _bare = _cur.Curation({})
    check("an empty curation ranks everything registry",
          _bare.rank("Part_Box"), _cur.REGISTRY)
    check("  and offers no neighbours", _bare.adjacent("Part_Box"), [])
    check("  and orders without dropping anything",
          _bare.order(REGISTRY, ["box", "circle"]), ["box", "circle"])
    check("an unknown command has no placement",
          curated.placement("No_Such_Command"), (None, None))

    # Column layout.
    check("no items, no rows", _cols([]), [])
    check("one item is one row", _cols(["only"]), ["only"])
    check("an item wider than the width still gets a row",
          len(_cols(["x" * 200])), 1)

    # The XDG fallback must stop applying once the new file exists.
    _dir = tempfile.mkdtemp()
    _new = os.path.join(_dir, "history")
    check("with nothing at the new path, the old one answers",
          _paths.readable(_new, "history") != _new,
          os.path.exists(_paths.legacy("history")))
    open(_new, "w", encoding="utf-8").close()
    check("once the new path exists it wins, empty or not",
          _paths.readable(_new, "history"), _new)

    # A history file with both formats in it.
    _mixed = os.path.join(tempfile.mkdtemp(), "history")
    with open(_mixed, "w", encoding="utf-8") as fh:
        fh.write("box 1,1,1\n%d\tcircle 0,0,0 5mm\n" % _now)
    _mh = _History(path=_mixed)
    check("old and new format lines read together",
          _mh.entries, ["box 1,1,1", "circle 0,0,0 5mm"])
    check("  each keeping its own epoch",
          [w for _, w in _mh.usage()], [0, _now])
    check("a repeated line counts twice but stamps once",
          (lambda h: (h.add("a", when=_now), h.add("b", when=_now),
                      h.add("a", when=_now + 5),
                      _frec.tally(h.usage())["a"]))(
              _History(path=os.path.join(tempfile.mkdtemp(), "h")))[-1],
          (2, _now + 5))

    check("mnemonic markers are stripped from a label",
          _factory_label("&Box Zoom"), "Box Zoom")

    print("\n5t. describe reads an object out as text")
    from fccli import describe as _desc
    from fccli.properties import is_noise as _is_noise
    _ddoc = App.newDocument("describe")
    _dbox = _ddoc.addObject("Part::Box", "Slab")
    _dbox.Length, _dbox.Width, _dbox.Height = 1219.2, 610, 19
    _ddoc.recompute()

    _out = []
    _stop = bus.subscribe(
        lambda m: _out.append(m.text) if m.kind == "info" else None)
    engine.submit("describe Slab")
    _text = "\n".join(_out)
    check("it names the object", "Slab" in _text, True)
    check("  and its type", "Part::Box" in _text, True)
    check("  and the verb that would build another", "made by" in _text, True)
    check("it reports placement", "position" in _text, True)
    check("it reports the parametric properties",
          all(p in _text for p in ("Length", "Width", "Height")), True)
    check("it reports what the shape measures",
          "bounding box" in _text and "volume" in _text, True)
    check("the filter is the one generated verbs use -- no plumbing",
          any(p in _text for p in ("AttachmentOffset", "MapReversed",
                                   "ExpressionEngine")), False)

    _by_heading = dict((h, dict(rows)) for h, rows in _desc.sections(_dbox))
    check("properties are exactly the useful ones",
          sorted(_by_heading["PROPERTIES"]),
          sorted(p for p in _dbox.PropertiesList if not _is_noise(_dbox, p)))

    _out.clear()
    engine.submit("describe")
    check("bare, it lists what the document holds",
          any("objects" in ln for ln in _out), True)
    check("  with one line each", any("Slab" in ln for ln in _out), True)

    _errs = []
    _stoperr = bus.subscribe(
        lambda m: _errs.append(m.text) if m.kind == ERROR else None)
    engine.submit("describe Slabb")
    check("a near miss is suggested, not just refused",
          any("did you mean" in e and "Slab" in e for e in _errs), True)
    _stoperr()

    # Derived numbers use FreeCAD's own rendering: they are read, never
    # typed back, so they are not held to the round-trip that a typed
    # value is. Held to it, a volume prints twelve significant digits.
    _entry_schema = _units.current_name()
    _units.set_schema("Internal")
    _shape = dict((h, dict(r)) for h, r in _desc.sections(_dbox))["SHAPE"]
    check("a volume renders to the Decimals preference",
          _shape["volume"], "14.13 l")
    _units.set_schema("ImperialBuilding")
    _shape = dict((h, dict(r)) for h, r in _desc.sections(_dbox))["SHAPE"]
    check("  and a bounding box follows the schema",
          _shape["bounding box"], "4\' x 2\' x 3/4\"")
    _units.set_schema(_entry_schema)
    _stop()
    App.closeDocument("describe")

    print("\n5u. a declared choice is input, not a new command")
    # _is_restart guarded TEXT, POINT and QUANTITY steps and forgot CHOICE,
    # so any choice sharing a name with a verb cancelled its own command.
    _restart = []
    _stopr = bus.subscribe(
        lambda m: _restart.append(m.text) if m.kind == "info" else None)
    engine.submit("check view sketch")
    check("a choice that is also a verb fills the step",
          any("41 commands" in ln for ln in _restart), True)
    check("  and does not cancel the command",
          any("cancelled" in ln for ln in _restart), False)
    _stopr()
    _hijacked = 0
    for _name in REGISTRY.names():
        for _st in REGISTRY.get(_name).steps:
            if _st.kind == "choice" and _st.choices:
                _hijacked += sum(
                    1 for c in _st.choices
                    if len(REGISTRY.resolve_prefix(c.lower())) == 1)
    check("the pairs that would have been hijacked are many",
          _hijacked > 100, True)

    print("\n5v. FreeCAD's key chords, offered as aliases")
    from fccli import shortcuts as _short
    check("a two-key chord becomes a word", _short.chord_to_alias("A, X"), "ax")
    check("a three-key chord too", _short.chord_to_alias("G, P, 3"), "gp3")
    check("a modified shortcut is left alone",
          _short.chord_to_alias("Ctrl+S"), None)
    check("a single key is a keystroke, not a word",
          _short.chord_to_alias("C"), None)
    for _key in ("Esc", "Del", "Space", "F10", "Home"):
        check(f"  {_key} stays a key", _short.chord_to_alias(_key), None)

    _accepted, _rejected = _short.proposals(
        REGISTRY, _load_desc(), {"ax": "circle"})
    check("an alias the operator already owns is not taken",
          "ax" in _accepted, False)
    check("  and the reason says whose it is",
          "you alias" in _rejected.get("ax", ""), True)
    _accepted2, _rejected2 = _short.proposals(REGISTRY, _load_desc(), {})
    check("a chord never shadows a command",
          [a for a in _accepted2 if REGISTRY.get(a) is not None], [])
    check("every accepted chord names a real verb",
          all(REGISTRY.get(v) is not None for v in _accepted2.values()), True)
    check("there are chords worth importing", len(_accepted2) > 100, True)

    _out2 = []
    _stop2 = bus.subscribe(
        lambda m: _out2.append(m.text) if m.kind == "info" else None)
    engine.submit("shortcuts import")
    check("import gives ax to the axis verb",
          REGISTRY.resolve_prefix("ax"), ["axis"])
    engine.submit("shortcuts drop")
    check("drop takes it back again",
          "ax" in REGISTRY.get("axis").aliases, False)
    check("  without disturbing a hand-written alias",
          REGISTRY.resolve_prefix("ci"), ["circle"])
    _stop2()

    print("\n5w. a selection is not a point")
    from fccli.grammar import SELECTION as _SEL, POINT as _PT
    _mv = REGISTRY.get("move")
    check("move asks for a selection first",
          [s.kind for s in _mv.steps][0], _SEL)
    _probe = Engine(Bus(), REGISTRY, picker=None)
    _probe.verb = _mv
    _probe.state = "collecting"
    _probe.values = {"objects": ["not a vector", "nor is this"]}
    check("a filled selection step is not read back as a point",
          _probe.last_point(), None)
    _probe.values["frm"] = App.Vector(1, 2, 3)
    check("  the point step is", tuple(_probe.last_point()), (1.0, 2.0, 3.0))
    _probe.values["to"] = App.Vector(4, 5, 6)
    check("  and the latest one wins", tuple(_probe.last_point()),
          (4.0, 5.0, 6.0))

    print("\n5x. a dialog's own buttons say what the command line should do")
    from fccli import modals as _modals
    from fccli.qt import QtWidgets as _QW

    def _box(icon, text, buttons):
        b = _QW.QMessageBox()
        b.setIcon(icon)
        b.setWindowTitle("Revolve")
        b.setText(text)
        b.setStandardButtons(buttons)
        return b

    _reject = _box(_QW.QMessageBox.Critical, "Select a shape for revolution.",
                   _QW.QMessageBox.Ok)
    _text, _buttons = _modals.read(_reject)
    check("a lone OK is read as one button", len(_buttons), 1)
    check("  and its role is what marks it a rejection",
          _buttons[0][1], "AcceptRole")
    check("the words come through", "revolution" in _text, True)
    check("  with the title folded in", _text.startswith("Revolve"), True)

    _ask = _box(_QW.QMessageBox.Question, "Save changes before closing?",
                _QW.QMessageBox.Save | _QW.QMessageBox.Discard
                | _QW.QMessageBox.Cancel)
    _text2, _buttons2 = _modals.read(_ask)
    _roles = sorted(role for _, role in _buttons2)
    check("a question offers three ways out", len(_buttons2), 3)
    check("  and Discard is the destructive one", _roles,
          ["AcceptRole", "DestructiveRole", "RejectRole"])

    # Reject by default. Cancelling is the answer that cannot lose work.
    check("without the bang, a question is cancelled",
          _modals._pick(_buttons2, force=False).text().replace("&", ""),
          "Cancel")
    check("the bang asks for the destructive answer instead",
          _modals._pick(_buttons2, force=True).text().replace("&", ""),
          "Discard")
    check("the bang changes nothing when there is nothing to discard",
          _modals._pick(_buttons, force=True).text().replace("&", ""), "OK")

    # Titles that merely repeat the body are folded, not printed twice.
    _dupe = _box(_QW.QMessageBox.Warning, "Revolve", _QW.QMessageBox.Ok)
    check("a title the body repeats appears once",
          _modals.read(_dupe)[0], "Revolve")

    _long = _box(_QW.QMessageBox.Critical, "x " * 400, _QW.QMessageBox.Ok)
    check("a wall of text is capped",
          len(_modals.read(_long)[0]) <= _modals.LIMIT, True)

    for _b in (_reject, _ask, _dupe, _long):
        _b.deleteLater()

    print("\n6. filter overhead")
    check("no key was dropped", kf.stats["seen"],
          kf.stats["usurped"] + kf.stats["passed"])
    print(f"       seen={kf.stats['seen']} usurped={kf.stats['usurped']} "
          f"passed={kf.stats['passed']}")

    kf.remove()
    _units.set_schema(entry_schema)   # the tests must not move a real setting
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed: " + ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
