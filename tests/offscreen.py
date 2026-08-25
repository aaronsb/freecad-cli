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
from fccli import paths as _paths_mod  # noqa: E402

# Every History built here names a fresh temp path, and readable() falls
# back to the pre-XDG location when that path does not exist yet -- so the
# suite has been loading the operator's real history into test rings all
# along, silently, making anything that ranks by habit depend on whose
# machine it ran on. 0252fba stopped the suites writing there; this is the
# reading half.
_paths_mod.LEGACY = tempfile.mkdtemp(prefix="fccli-no-legacy-")

# 5v drives `shortcuts import` through the engine, which writes every
# accepted chord to ALIAS_PATH -- the operator's real alias file, since
# make test sets no XDG_DATA_HOME. It ends by dropping them again, so the
# file survived by luck; a failure between the two left 161 aliases behind.
from fccli import shell as _shell_mod  # noqa: E402
_shell_mod.ALIAS_PATH = os.path.join(
    tempfile.mkdtemp(prefix="fccli-aliases-"), "aliases")
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


def _run():
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

    # A stored Quantity is a value somebody typed, so describe has to print
    # it readable-back. Its UserString is not: under this schema 100 mm
    # reads as 3" + 7/8", a syntax error, and 1234.5 mm reads as 4' 5/8",
    # which parses 0.575 mm off -- the quiet one.
    for _mm in (100.0, 250.0, 999.9, 1234.5, 19.05, 0.0):
        _q = App.Units.Quantity(_mm, "mm")
        _shown = U.format_typed(_q)
        check(f"{_mm}mm prints as something that parses",
              abs(App.Units.Quantity(_shown).Value - _mm) < 1e-6, True)
    check("and 1234.5mm is exact, not 0.575mm off",
          abs(App.Units.Quantity(U.format_typed(
              App.Units.Quantity(1234.5, "mm"))).Value - 1234.5) < 1e-9, True)
    _bad = App.Units.Quantity(1234.5, "mm").UserString
    check("  which its UserString was not",
          _bad != U.format_typed(App.Units.Quantity(1234.5, "mm")), True)

    # An angle takes the same ladder, and has no schema conversion to do.
    _ang = U.format_typed(App.Units.Quantity(30.0, "deg"))
    check("an angle round-trips too",
          abs(App.Units.Quantity(_ang).Value - 30.0) < 1e-6, True)
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

    # Named a family rather than assumed: `constrain` used to be one, and
    # stopped when the harvest started reading real labels. Sketcher's own
    # CompConstrainTools carries the label "Constrain", it is registered as
    # a command before families are built, and a command verb takes the
    # name. Whether a family should outrank a generated command verb is a
    # real question -- it would move about thirty names, several of them
    # to families not worth having (`free` is four CAD donation links) --
    # and it is not this change's to answer. So the check asks the
    # property of whatever family actually won.
    fams = [fresh2.get(n) for n in fresh2.names()
            if fresh2.get(n).family == n]
    check("families own their names", len(fams) > 20, True)
    check("  and every one offers its members as choices",
          all(f.steps and len(f.steps[0].choices) >= 3 for f in fams), True)
    check("  constrain is a command verb now, not a family",
          fresh2.get("constrain").gui_command, "Sketcher_CompConstrainTools")
    check("  and the constraints are still individually reachable",
          all(fresh2.by_gui_command(c) is not None for c in
              ("Sketcher_ConstrainCoincident", "Sketcher_ConstrainParallel",
               "Sketcher_ConstrainPerpendicular")), True)

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
    from fccli.factory import load_dictionary as _ld_cur
    curated = _cur.load(_desc, _ld_cur())
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

    # A hand-written verb whose name a family also claims. The family table
    # holds every family in the descriptor, including the ones register_all
    # refused because a verb already owned the name, so asking it by name
    # answered for the wrong command: `man point` listed TechDraw's
    # annotation toolbar for a Draft point, and `move`, `save` and `close`
    # got nothing at all.
    _point = REGISTRY.get("point")
    check("the colliding name is still a family in the table",
          "point" in curated._families, True)
    check("  but the verb does not claim it",
          getattr(_point, "family", None), None)
    _near = curated.neighbours(REGISTRY, _point)
    check("a verb's own command decides its neighbours", bool(_near), True)
    check("  not a family that merely shares its name",
          any(n.endswith("annotation") or "leader" in n for n in _near), False)
    check("  and they come off its own toolbar",
          "circle" in _near or "arc" in _near, True)
    for _name in ("move", "save", "close"):
        check(f"{_name} has neighbours again",
              bool(curated.neighbours(REGISTRY, REGISTRY.get(_name))), True)
    check("a real family verb still answers from its family",
          bool(curated.neighbours(REGISTRY, REGISTRY.get("view"))), True)
    check("choices are not offered for a name a verb does not own",
          curated.choice_groups("close", REGISTRY.get("close")), [])

    # `made by` used to take the first claimant in registry order, so every
    # Draft line was reported as made by point -- both are hand-written and
    # both build a Part::FeaturePython, and nothing about the type says
    # which. A verb somebody wrote answers over one the factory generated
    # for the same type; where that still leaves several, it says nothing.
    check("a hand-written verb is recognised as authored",
          _cur.authored(REGISTRY.get("box")), True)
    check("  and a generated one is not",
          _cur.authored(REGISTRY.get("sketcher_bsplinedegree")), False)
    from fccli.shell import _verb_for_type as _made_by
    check("an unambiguous type names its verb",
          _made_by("Part::Box"), "box")
    _shared = [n for n in REGISTRY.names()
               if REGISTRY.get(n).creates == "Part::FeaturePython"
               and _cur.authored(REGISTRY.get(n))]
    check("more than one hand-written verb builds Part::FeaturePython",
          len(_shared) > 1, True)
    check("  so the type does not name one", _made_by("Part::FeaturePython"),
          None)
    check("an unknown type names nothing", _made_by("No::Such"), None)
    check("and neither does no type at all", _made_by(None), None)

    # An addon's own verb. Patches are imported by path under a synthetic
    # module name, so the old test for one -- "patches" in the module --
    # matched nothing the loader has ever produced, and a verb an addon
    # author wrote by hand ranked below every generated launcher.
    from fccli.grammar import Verb as _Verb

    # Authorship is stated, not inferred. It used to be read off
    # verb.emit.__module__, which stopped answering once every generated
    # command verb came to share one emit with the hand-written panel
    # verbs -- hand-written `transform` then read as generated, lost
    # promoted rank, and `use <domain>` hid it.
    _declared = _Verb(name="whatever", steps=[], emit=lambda v: None)
    check("a verb an addon wrote ranks promoted",
          curated.rank_of(_declared), _cur.PROMOTED)
    check("  above anything the factory generated",
          curated.rank_of(_declared)
          < curated.rank_of(REGISTRY.get("sketcher_bsplinedegree")), True)
    _generated = _Verb(name="whatever2", steps=[], emit=lambda v: None,
                       generated=True)
    check("a generated verb is not promoted", curated.rank_of(_generated)
          > _cur.PROMOTED, True)
    check("  whatever module its emit came from",
          _cur.authored(_generated), False)
    check("transform is hand-written and says so",
          _cur.authored(REGISTRY.get("transform")), True)
    check("  and ranks promoted like the rest of them",
          curated.rank_of(REGISTRY.get("transform")), _cur.PROMOTED)

    # Undo grouping is not a tier's business. Declaring every command verb
    # non-transactional so that a panel would not nest its own undo inside
    # ours took one-line-one-undo away from the 970 of them that open no
    # panel. The transaction is skipped when a panel opened, which is a
    # fact about the invocation rather than the verb.
    _loose = [n for n in REGISTRY.names()
              if REGISTRY.get(n).generated and not REGISTRY.get(n).transactional]
    check("a generated verb still gets its own undo step", _loose, [])
    _session_verbs = [n for n in REGISTRY.names()
                      if not REGISTRY.get(n).transactional]
    check("only the session verbs opt out", len(_session_verbs) < 40, True)
    from fccli.engine import _open_transaction as _txn
    check("and a panel is what skips it, not a tier",
          _txn(REGISTRY.get("box"), "box", panel=True), None)
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
    # This used to compute its expectation with the same os.path.exists the
    # implementation branches on, so it passed either way.
    _dir = tempfile.mkdtemp()
    _fresh = os.path.join(_dir, "absent")
    _present = os.path.join(_dir, "present")
    open(_present, "w", encoding="utf-8").close()
    check("a new path that exists wins outright",
          _paths.readable(_present, "history"), _present)
    check("an absent one defers to whatever legacy says",
          _paths.readable(_fresh, "history") in
          (_fresh, _paths.legacy("history")), True)

    # The move to XDG must not strand what came before it. Appending one
    # line to the new path made readable() prefer a file holding that one
    # line, and everything typed before the move went unreachable on the
    # next start -- with the frecency ranking this release adds left
    # nothing to rank.
    _mig = os.path.join(tempfile.mkdtemp(), "history")
    _ring = _History(path=_mig)
    _ring.entries = ["box 0,0,0 10", "circle 0,0,0 5", "line 0,0,0 1,1,1"]
    _ring.stamps = {"box 0,0,0 10": 111, "circle 0,0,0 5": 222,
                    "line 0,0,0 1,1,1": 333}
    _ring._write("cylinder 12 40")
    check("the first write carries the whole ring across",
          _History(path=_mig).entries,
          ["box 0,0,0 10", "circle 0,0,0 5", "line 0,0,0 1,1,1",
           "cylinder 12 40"])
    check("  with the stamps that came with it",
          _History(path=_mig).stamps.get("circle 0,0,0 5"), 222)
    _ring._write("sphere 8")
    check("a later write only appends",
          len(_History(path=_mig).entries), 5)

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
    # This used to weigh 1 -- the stalest possible -- on the grounds that a
    # future stamp is not to be trusted. The cost of that distrust is worse
    # than the thing it guards: a clock that ran fast and was then corrected
    # backwards buried everything typed in between at weight 1 permanently,
    # because stamps are written once and never revisited. A stamp ahead of
    # now is the most recent thing in the ring, so it weighs most.
    check("a timestamp in the future is the newest thing there is",
          _frec.recency_weight(_now, _now + 86400), 16)
    check("  and one far in the future is still just the newest",
          _frec.recency_weight(_now, _now + 400 * 86400), 16)

    # One tally, shared. completion cached it privately, so the toolbar's
    # familiarity cue rebuilt the whole thing -- every line in the ring,
    # every verb in the dict -- to read one count, on every click.
    _th = _History(path=os.path.join(tempfile.mkdtemp(), "history"))
    # Interleaved: add refuses a line identical to the one before it, so
    # three in a row would be one entry.
    for _ in range(3):
        _th.add("box 0,0,0 1 1 1", when=_now)
        _th.add("circle 0,0,0 5", when=_now)
    _first = _th.tally()
    check("the tally counts what was run", _first.get("box")[0], 3)
    check("  and is not rebuilt while the ring is unchanged",
          _th.tally() is _first, True)
    _th.add("sphere 3", when=_now)
    check("  but is once it changes", _th.tally() is _first, False)
    check("  with the new entry in it", _th.tally().get("sphere")[0], 1)
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
          any("36 commands" in ln for ln in _restart), True)
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

    # SELECTION was the other one it forgot, and FreeCAD's default labels
    # are the verb names: Box, Cylinder, Sphere, Cone, Line, Circle, Point.
    # Typing `Box` at move's selection step cancelled move and started the
    # box verb asking for a Length, which made _resolve_names unreachable
    # for exactly the labels FreeCAD hands out.
    _seldoc = App.newDocument("restartsel")
    _seldoc.addObject("Part::Box", "Box")
    _seldoc.recompute()
    _sel = []
    _stops = bus.subscribe(
        lambda m: _sel.append(m.text) if m.kind == "info" else None)
    engine.cancel()
    engine.submit("move")
    engine.submit("Box")
    check("an object's own label fills the selection step",
          engine.state, "collecting")
    check("  the command is still move", engine.verb.name, "move")
    check("  and the object landed",
          [o.Name for o in engine.values.get("objects", [])], ["Box"])
    check("  nothing was cancelled",
          any("cancelled" in ln for ln in _sel), False)

    # A verb name that is not an object in the document still restarts.
    _sel.clear()
    engine.submit("cancel") if False else engine.cancel()
    _sel.clear()
    engine.submit("move")
    engine.submit("cylinder")
    check("a name no object answers to still restarts",
          any("cancelled" in ln for ln in _sel), True)
    check("  and the new verb is the one that started",
          engine.verb.name, "cylinder")
    engine.cancel()
    _stops()
    App.closeDocument(_seldoc.Name)

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

    # drop used to decide what to remove by asking whether an alias looked
    # like a key chord. Every alias of two or more letters does, so it
    # deleted the operator's own -- with nothing ever imported. The file
    # records who wrote each one instead.
    from fccli import shell as _shell
    _alias_saved = _shell.ALIAS_PATH
    _shell.ALIAS_PATH = os.path.join(tempfile.mkdtemp(), "aliases")
    try:
        _shell._save_aliases({"sq": "box", "zzz": "circle", "ax": "circle"},
                             imported={"ax"})
        _pairs, _imported = _shell._read_aliases()
        check("what import wrote is marked", _imported, {"ax"})
        check("  and what the operator wrote is not",
              sorted(set(_pairs) - _imported), ["sq", "zzz"])
        check("every alias still reads back",
              sorted(_pairs), ["ax", "sq", "zzz"])
        check("the mark never leaks into the command",
              _pairs["ax"], "circle")
        # A chord the operator redefines by hand becomes theirs.
        _shell._save_aliases(_pairs, _imported - {"ax"})
        check("redefining one by hand clears its mark",
              _shell._read_aliases()[1], set())
    finally:
        _shell.ALIAS_PATH = _alias_saved

    _out2 = []
    _stop2 = bus.subscribe(
        lambda m: _out2.append(m.text) if m.kind == "info" else None)
    # A hand-written alias, in the file drop reads -- `ci` is declared on
    # the circle verb in fccli/verbs.py, so it never reaches the alias file
    # and drop never considered it. The check passed either way.
    engine.submit("alias sq box")
    check("a hand-written alias resolves", REGISTRY.resolve_prefix("sq"),
          ["box"])
    engine.submit("shortcuts import")
    check("import gives ax to the axis verb",
          REGISTRY.resolve_prefix("ax"), ["axis"])
    check("  and marks it as its own",
          "ax" in _shell_mod._read_aliases()[1], True)
    check("  leaving the hand-written one unmarked",
          "sq" in _shell_mod._read_aliases()[1], False)
    engine.submit("shortcuts drop")
    check("drop takes it back again",
          "ax" in REGISTRY.get("axis").aliases, False)
    check("  without disturbing a hand-written alias",
          REGISTRY.resolve_prefix("sq"), ["box"])
    check("  which is still in the file",
          _shell_mod._read_aliases()[0].get("sq"), "box")
    engine.submit("unalias sq")
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

    def _box(icon, text, buttons, title="Revolve"):
        b = _QW.QMessageBox()
        b.setIcon(icon)
        b.setWindowTitle(title)
        b.setText(text)
        b.setStandardButtons(buttons)
        return b

    _reject = _box(_QW.QMessageBox.Critical, "Select a shape for revolution.",
                   _QW.QMessageBox.Ok)
    _kind, _text, _buttons = _modals.read(_reject)
    check("a lone OK on a complaint is a rejection", _kind, "rejection")
    check("  and its role is what marks it", _buttons[0][1], "AcceptRole")
    check("the words come through", "revolution" in _text, True)
    check("  with the title folded in", _text.startswith("Revolve"), True)

    # An Information box is the command reporting that it worked. Reading
    # every one-button box as a rejection rolled the transaction back and
    # called a success a failure.
    _notice = _box(_QW.QMessageBox.Information, "No errors found in the mesh.",
                   _QW.QMessageBox.Ok, title="Mesh check")
    check("an informational box is a notice, not a rejection",
          _modals.read(_notice)[0], "notice")

    _ask = _box(_QW.QMessageBox.Question, "Save changes before closing?",
                _QW.QMessageBox.Save | _QW.QMessageBox.Discard
                | _QW.QMessageBox.Cancel)
    _k2, _text2, _buttons2 = _modals.read(_ask)
    check("several buttons make a question", _k2, "question")
    check("  offering three ways out", len(_buttons2), 3)
    check("  with Discard as the destructive one",
          sorted(r for _, r in _buttons2),
          ["AcceptRole", "DestructiveRole", "RejectRole"])

    check("without the bang, a question is cancelled",
          _modals._pick(_buttons2, force=False).text().replace("&", ""),
          "Cancel")
    check("the bang asks for the destructive answer instead",
          _modals._pick(_buttons2, force=True).text().replace("&", ""),
          "Discard")
    check("the bang changes nothing when there is nothing to discard",
          _modals._pick(_buttons, force=True).text().replace("&", ""), "OK")

    # A file chooser has no buttons worth reading, and calling .text() on
    # one raised out of the event filter -- which left the chooser up and
    # the caller hanging, which is the bug this module exists for.
    _chooser = _QW.QFileDialog()
    _kc, _tc, _bc = _modals.read(_chooser)
    check("a file chooser is its own kind", _kc, "chooser")
    check("  with no buttons to read", _bc, [])
    check("  and an answer that says what to do instead",
          "path as an argument" in _tc, True)

    _dupe = _box(_QW.QMessageBox.Warning, "Revolve", _QW.QMessageBox.Ok)
    check("a title the body repeats appears once",
          _modals.read(_dupe)[1], "Revolve")
    _long = _box(_QW.QMessageBox.Critical, "x " * 400, _QW.QMessageBox.Ok)
    check("a wall of text is capped",
          len(_modals.read(_long)[1]) <= _modals.LIMIT, True)

    # Caught: a notice alone is not a failure, so the command still commits.
    _c = _modals.Caught()
    _c.notices.append("done")
    check("a notice on its own does not fail the command", bool(_c), False)
    _c.faults.append("nope")
    check("  a rejection does", bool(_c), True)

    # Nested arming. One filter per block let the inner one claim a dialog
    # the outer had raised, and the outer then committed a command it
    # should have failed.
    with _modals.intercepted() as _outer:
        with _modals.intercepted() as _inner:
            check("the innermost block is the one armed",
                  _modals._FILTER.targets[-1] is _inner, True)
        check("  and the outer one is armed again after it",
              _modals._FILTER.targets[-1] is _outer, True)
    check("nothing stays armed once the blocks are done",
          _modals._FILTER.targets, [])

    for _b in (_reject, _notice, _ask, _dupe, _long, _chooser):
        _b.deleteLater()

    print("\n5y. a panel line is cut at the names, not the spaces")
    from fccli.panels import split_assignments as _split

    # A value holds spaces -- 3/4 in, Center of mass / centroid -- so a
    # name=value line cannot be read a whitespace token at a time.
    check("two assignments, values intact",
          _split("xposition=25 mm zposition=3/4 in")[0],
          [("xposition", "25 mm"), ("zposition", "3/4 in")])

    # And a value can hold something that reads as an assignment. What
    # tells them apart is the space before the `=`.
    check("prose inside a value is not a split point",
          _split("label=Wall A = north")[0], [("label", "Wall A = north")])
    check("  even when it is a whole clause",
          _split("name=set x = 3")[0], [("name", "set x = 3")])
    check("a name meant as one still splits, so it can be reported",
          [n for n, _ in _split("xposition=6 nosuch=1 zposition=8")[0]],
          ["xposition", "nosuch", "zposition"])
    check("quoting settles what is left",
          _split('label="a = b"')[0], [("label", "a = b")])
    check("a prefix name splits like any other",
          _split("xpos=5 mm")[0], [("xpos", "5 mm")])
    check("and a typo does too, so it can be named",
          _split("xpositon=25")[0], [("xpositon", "25")])
    check("something that is not an assignment says so",
          _split("justaword"), ([], "justaword"))

    print("\n5z. a command a workbench has not brought yet")
    # The descriptor is harvested with every workbench activated, so it
    # knows about commands a running FreeCAD has not registered. `grid` is
    # Arch_Grid, and Arch commands come with BIM -- which the command's own
    # name does not say, so the descriptor has to.
    import fccli.factory as _fmod
    _paths_desc = _fmod.DESCRIPTOR
    _cmds = _load_desc()["commands"]
    _owned = [n for n, v in _cmds.items() if v.get("workbench")]
    check("commands say which workbench brings them", len(_owned) > 300, True)
    check("  Arch_Grid comes with BIM",
          _cmds["Arch_Grid"]["workbench"], "BIMWorkbench")
    check("  and a Draft command says Draft, not whatever loaded first",
          _cmds["Draft_Line"]["workbench"], "DraftWorkbench")
    check("Std claims no workbench",
          _cmds["Std_ViewFront"].get("workbench"), None)
    # The harvest snapshots listCommands() before activating anything, so
    # whatever the startup workbench had loaded -- Part, Sketcher and Part
    # Design on a machine that starts in Part Design -- was credited to
    # nobody, and the stem repair only ran over what the loop attributed.
    # 238 commands. A command whose stem names a workbench carries it.
    check("  Part_Box comes with Part, whatever loaded it first",
          _cmds["Part_Box"].get("workbench"), "PartWorkbench")
    _by_stem = {w.lower(): w for w in _load_desc()["workbenches"]}
    _orphans = [n for n in _cmds if not _cmds[n].get("workbench")
                and (_by_stem.get(n.split("_", 1)[0].lower() + "workbench")
                     or _by_stem.get(n.split("_", 1)[0].lower()))]
    check("  every command whose stem names a workbench carries it",
          (len(_orphans), _orphans[:5]), (0, []))
    # whatsThis is the wiki page F1 resolves. getInfo had it all along and
    # the harvest dropped it; it is the official link from a command to
    # its documentation, and ADR-100 seeds every command file from it.
    check("commands carry their wiki page",
          sum(1 for v in _cmds.values() if v.get("wiki")) > 1000, True)
    check("  Part_Box's is Part_Box", _cmds["Part_Box"].get("wiki"), "Part_Box")
    check("  and one that differs from the name is kept as FreeCAD says it",
          _cmds["TechDraw_Annotation"].get("wiki"), "TechDraw_NewAnnotation")

    # The check that would have caught it. 148 commands reached the
    # descriptor carrying only a name, because the harvest read everything
    # off QActions and those have none. build_command_verb falls back
    # `tooltip or label or name`, so the gap never showed as missing --
    # it showed as a verb named arch_multimaterial whose whole
    # documentation was the string "Arch_MultiMaterial".
    check("every command has a label",
          [n for n, c in _cmds.items() if not c.get("label")], [])
    check("  and a tooltip",
          [n for n, c in _cmds.items() if not c.get("tooltip")], [])
    # endswith, not ==. The first version of this check asked for equality
    # and passed while 909 tooltips read "CubeCreates a solid cubePart_Box"
    # -- act.toolTip() is rich text in three blocks and clean() ran them
    # together, so the name was glued to a sentence rather than being the
    # whole string. Equality could not see it.
    check("  and no command's documentation ends in its own name",
          [n for n, c in _cmds.items()
           if (c.get("tooltip") or "").endswith(n)], [])
    # Nothing in a shipped artifact may name the machine that built it.
    _raw = open(_paths_desc, encoding="utf-8").read()
    check("the descriptor names no home directory", "/home/" in _raw, False)
    check("  and no per-document cache path",
          "FreeCAD_Doc_" in _raw, False)
    # Dropping the transient ones must not take the real templates with
    # it. The first version matched on HOME as an unanchored substring,
    # which with HOME=/ or HOME unset -- ordinary in a container -- would
    # have discarded every absolute default in silence. Both new checks
    # above assert on absence, so neither could have seen it.
    _abs = {p["default"] for t in _load_desc()["types"].values()
            for p in t.get("params", [])
            if isinstance(p.get("default"), str)
            and p["default"].startswith("/")}
    check("  and the real template paths survive", len(_abs), 3)
    # getInfo hands back raw resource strings. Std_About's status is
    # "Displays information about %1" where the action's is substituted.
    check("no documentation carries an unsubstituted placeholder",
          [n for n, c in _cmds.items()
           if "%" in (c.get("tooltip") or "") + (c.get("status") or "")], [])

    # Every command reaches a verb. A tier-0 name already taken used to be
    # dropped without a word -- 90 of them before this, 133 after labels
    # got better and more commands wanted the same short names.
    _fresh = _Registry()
    _c = register_all(_fresh, tier0=True, patches=PatchSet())
    check("every command gets a tier-0 verb", _c["tier0"], len(_cmds))
    check("  none is left unreachable", _c.get("unreachable", 0), 0)
    check("  and the ones that had to move say so", _c["qualified"] > 100, True)

    # Who wins a contested short name is FreeCAD's call, not the alphabet's.
    # Two commands whose labels slug the same both want the plain name and
    # the first registered takes it; sorted by command name that picked
    # CAM_Compound over Part_Compound and Arch_Material over the
    # BIM_Material in a toolbar. Twenty names moved that way before
    # _by_prominence, every one of them off a command FreeCAD surfaces and
    # onto one reachable only from code.
    for _verb, _want in (("compound", "Part_Compound"),
                         ("material", "BIM_Material"),
                         ("cross_sections", "Mesh_CrossSections"),
                         ("mesh_from_shape", "Mesh_FromPartShape")):
        _got = _fresh.get(_verb)
        check(f"  {_verb} is the one FreeCAD puts on a toolbar",
              _got.gui_command if _got else None, _want)
    # The loser is qualified, not lost.
    check("  and the one it beat is still reachable",
          _fresh.by_gui_command("CAM_Compound") is not None, True)
    # Stable: the rank is the key, the descriptor's order breaks ties.
    _again = _Registry()
    register_all(_again, tier0=True, patches=PatchSet())
    check("  and rebuilding gives the same answer",
          {n: _again.get(n).gui_command for n in _again.names()},
          {n: _fresh.get(n).gui_command for n in _fresh.names()})

    print("\n5aa. FreeCAD's settings stay FreeCAD's")
    # The picker used to turn Draft's grid off on every snap because the
    # operator's gridSpacing was 0 -- while their alwaysShowGrid was on.
    # Overruling a preference at runtime is the same imposition as
    # rewriting it. The condition gets reported instead.
    from fccli import picking as _pick

    # Revert detectors, not behaviour: an inlined suppression leaves these
    # green. Named so nobody counts them as coverage.
    check("quiet_grid is not back by that name",
          hasattr(_pick, "quiet_grid"), False)
    check("  nor _hushed", hasattr(_pick, "_hushed"), False)

    _was_draw, _was_space = _pick._grid_will_draw, _pick._grid_spacing
    try:
        def _report(will_draw, spacing, notify=True, fresh=True):
            said = []
            if fresh:
                _pick._GRID_REPORTED = False
            _pick._grid_will_draw = lambda: will_draw
            _pick._grid_spacing = lambda: spacing
            _pick.report_grid(said.append if notify else None)
            return said
        check("zero spacing on a grid that draws is reported",
              len(_report(True, 0.0)), 1)
        check("  and it names where to fix it",
              "Preferences" in _report(True, 0.0)[0], True)
        check("a working spacing says nothing", _report(True, 10.0), [])
        check("a grid nobody shows says nothing", _report(False, 0.0), [])
        check("an unreadable preference says nothing", _report(True, None), [])

        # Once per session: three point steps must not print it three times.
        _pick._GRID_REPORTED = False
        said = []
        _pick._grid_will_draw, _pick._grid_spacing = lambda: True, lambda: 0.0
        for _ in range(3):
            _pick.report_grid(said.append)
        check("it is said once, not once per pick", len(said), 1)

        # A call that had nowhere to say it must not count as having said
        # it. bvt calls ensure_snapper() bare, and that used to silence the
        # report for the rest of the process.
        _pick._GRID_REPORTED = False
        _report(True, 0.0, notify=False, fresh=False)
        check("a call with no way to speak does not use up the one report",
              len(_report(True, 0.0, fresh=False)), 1)

        # Nothing to say yet is not the same as said. Draft carries a
        # parameter observer for gridSpacing because it changes mid-session.
        _pick._GRID_REPORTED = False
        _report(True, 10.0, fresh=False)
        check("a spacing corrected to zero later is still reported",
              len(_report(True, 0.0, fresh=False)), 1)
    finally:
        _pick._grid_will_draw, _pick._grid_spacing = _was_draw, _was_space
        _pick._GRID_REPORTED = False

    # A workbench fetched to run a command is handed back. Driven against a
    # stub, because the import is inside the function: what matters is the
    # order, the no-op when it is already active, and that the restore
    # happens when the body raises.
    from fccli import panels as _panels

    class _FakeWb:
        def __init__(self, name): self._name = name
        def name(self): return self._name

    class _FakeGui:
        def __init__(self, active, brings=None):
            self.active, self.calls = active, []
            # What each workbench registers when it is activated.
            self.brings = brings or {}
            self.commands = []
        def activeWorkbench(self): return _FakeWb(self.active)
        def listWorkbenches(self): return ["PartDesignWorkbench",
                                           "BIMWorkbench"]
        def listCommands(self): return list(self.commands)
        def activateWorkbench(self, name):
            self.active = name
            self.calls.append(name)
            self.commands += self.brings.get(name, [])

    # Nothing inside this block may EXECUTE a module: an import that runs
    # would bind the fake permanently, past the finally. An import
    # statement that resolves from sys.modules is fine, and there is one
    # -- not_yet_loaded does `from .factory import load_descriptor`.
    # Importing fccli.panels does not pull fccli.factory in, so that would
    # be a cold import here if nothing else had loaded it. Load it now, so
    # the window holds by construction rather than by what ran before it.
    import fccli.factory  # noqa: F401
    _real_gui = sys.modules.get("FreeCADGui")
    try:
        gui = _FakeGui("PartDesignWorkbench")
        sys.modules["FreeCADGui"] = gui
        with _panels._workbench_borrowed("BIMWorkbench") as was:
            inside = gui.active
        check("the borrow activates what was asked for",
              inside, "BIMWorkbench")
        check("  and names what it displaced", was, "PartDesignWorkbench")
        check("  and puts it back",
              gui.calls, ["BIMWorkbench", "PartDesignWorkbench"])

        gui = _FakeGui("BIMWorkbench")
        sys.modules["FreeCADGui"] = gui
        with _panels._workbench_borrowed("BIMWorkbench"):
            pass
        check("already there means no switch back",
              gui.calls, ["BIMWorkbench"])

        gui = _FakeGui("PartDesignWorkbench")
        sys.modules["FreeCADGui"] = gui
        try:
            with _panels._workbench_borrowed("BIMWorkbench"):
                raise RuntimeError("the command blew up")
        except RuntimeError:
            pass
        check("a body that raises still gives the workbench back",
              gui.calls, ["BIMWorkbench", "PartDesignWorkbench"])

        # And the fetch says where it went. This is the whole user-visible
        # half of the fix -- a fetch rebuilds the toolbars twice, and an
        # unexplained double flicker is what it replaced.
        def _fetch(active, brings, already=()):
            said = []
            g = _FakeGui(active, brings)
            g.commands = list(already)
            sys.modules["FreeCADGui"] = g
            complaint = _panels.not_yet_loaded("Arch_Grid", said.append)
            return said, complaint, g.calls
        _brings = {"BIMWorkbench": ["Arch_Grid"]}
        check("a fetch from elsewhere names both ends",
              _fetch("PartDesignWorkbench", _brings)[0],
              ["fetched Arch_Grid from BIMWorkbench, "
               "back to PartDesignWorkbench"])
        check("  a fetch from the same workbench has nowhere to go back to",
              _fetch("BIMWorkbench", _brings)[0],
              ["fetched Arch_Grid from BIMWorkbench"])
        _said, _complaint, _calls = _fetch(
            "PartDesignWorkbench", _brings, already=["Arch_Grid"])
        check("a command already there is not fetched", _calls, [])
        check("  and nothing is said about it", _said, [])
        check("  and it does not complain", _complaint, None)
        _said, _complaint, _calls = _fetch(
            "PartDesignWorkbench", {"BIMWorkbench": []})
        check("a fetch that does not produce the command complains",
              bool(_complaint) and "BIMWorkbench" in _complaint, True)
        check("  and claims no fetch it did not make", _said, [])
    finally:
        if _real_gui is not None:
            sys.modules["FreeCADGui"] = _real_gui
        else:
            sys.modules.pop("FreeCADGui", None)

    print("\n5ab. a command FreeCAD has that the descriptor never saw")
    # ADR-600, layer 2. An addon installed after the descriptor was
    # harvested registers its commands with FreeCAD, and register_all read
    # the descriptor only -- so the addon was invisible until somebody ran
    # make descriptor on a machine that had it. At startup, a command in
    # listCommands() the descriptor does not know gets a tier-0 verb with
    # its label from getInfo(), the way the harvest would have named it.
    class _FakeCmd:
        def __init__(self, info): self._info = info
        def getInfo(self): return self._info

    class _RuntimeGui:
        def __init__(self, extra):
            self.extra = extra
        def listCommands(self):
            return list(_cmds)[:5] + list(self.extra)
        class Command:
            registry = {}
            @classmethod
            def get(cls, name): return cls.registry.get(name)

    class _Raising:
        def getInfo(self): raise RuntimeError("no info")

    _RuntimeGui.Command.registry = {
        "Acme_Widget": _FakeCmd({"menuText": "&Widget Thing",
                                 "toolTip": "Makes a widget"}),
        "Acme_About": _FakeCmd({"menuText": "About %1",
                                "toolTip": "About %1"}),
        "Std_ViewFront": _FakeCmd({"menuText": "Not used"}),
        # Collides with a descriptor tier-0 name.
        "Acme_Box": _FakeCmd({"menuText": "Box", "toolTip": "An addon box"}),
        # Collides with a tier-1 typed verb, which registers after tier 0.
        "Acme_Tier1": _FakeCmd({"menuText": "Additive Box",
                                "toolTip": "Not PartDesign's"}),
        # Rich text and entities, the way an addon writes a tooltip.
        "Acme_Rich": _FakeCmd({"menuText": "Rich",
                               "toolTip": "<p><b>Cut</b> A &amp; B\nnow</p>"}),
        # A percent sign that is not a Qt placeholder.
        "Acme_Pct": _FakeCmd({"menuText": "Pct",
                              "toolTip": "Scales by 50% of the box"}),
        "Acme_Raise": _Raising(),
    }
    _extra = ["Acme_Widget", "Acme_About", "Std_ViewFront", "Acme_Box",
              "Acme_Tier1", "Acme_Rich", "Acme_Pct", "Acme_Raise",
              "Acme_Null"]        # Command.get returns None for this one
    _real_gui = sys.modules.get("FreeCADGui")
    try:
        sys.modules["FreeCADGui"] = _RuntimeGui(_extra)
        _rt = _Registry()
        _rc = register_all(_rt, tier0=True, patches=PatchSet())
        check("commands the descriptor never saw are registered",
              _rc.get("runtime", 0), 8)
        _bx = _rt.by_gui_command("Acme_Box")
        check("  a name a descriptor command holds is qualified, not taken",
              (_bx.name if _bx else None, _rt.get("box").gui_command),
              ("acme_box", "Part_Box"))
        _t1 = _rt.by_gui_command("Acme_Tier1")
        check("  a name a tier-1 verb holds is qualified, not overwritten",
              (_t1.name if _t1 else None,
               getattr(_rt.get("additive_box"), "creates", None)),
              ("acme_additive_box", "PartDesign::AdditiveBox"))
        _rich = _rt.by_gui_command("Acme_Rich")
        check("  rich text and entities are cleaned the way the harvest does",
              _rich.doc if _rich else None, "Cut A & B now")
        _pct = _rt.by_gui_command("Acme_Pct")
        check("  a percent sign that is not a placeholder is kept",
              _pct.doc if _pct else None, "Scales by 50% of the box")
        _null = _rt.by_gui_command("Acme_Null")
        _raise = _rt.by_gui_command("Acme_Raise")
        check("  no info at all still gets a verb, documented as a name",
              (_null.name if _null else None, _null.doc if _null else None,
               _raise.name if _raise else None),
              ("acme_null", "Acme Null", "acme_raise"))
        _w = _rt.get("widget_thing")
        check("  named from getInfo's menuText, mnemonic dropped",
              _w.gui_command if _w else None, "Acme_Widget")
        check("  documented from its toolTip",
              _w.doc if _w else None, "Makes a widget")
        _a = _rt.by_gui_command("Acme_About")
        check("  a placeholder label falls back to the command name",
              _a.name if _a else None, "acme_about")
        check("  and a descriptor command is not registered twice",
              _rc["tier0"], len(_cmds))
        _launchers = [_rt.get(n) for n in _rt.names()
                      if _rt.get(n).gui_command == "Std_ViewFront"
                      and _rt.get(n).open is not None]
        check("  the descriptor's own label wins for Std_ViewFront",
              [v.name for v in _launchers], ["1_front"])
        check("  and the runtime label for it was not used",
              _rt.get("not_used"), None)
    finally:
        if _real_gui is None:
            sys.modules.pop("FreeCADGui", None)
        else:
            sys.modules["FreeCADGui"] = _real_gui
    # A workbench opened later brings more. The second call registers only
    # what is new, and says how many.
    from fccli.factory import register_runtime
    _gui2 = _RuntimeGui(["Acme_Widget"])
    _RuntimeGui.Command.registry["Acme_Later"] = _FakeCmd(
        {"menuText": "Later Thing", "toolTip": "Came with a workbench"})
    try:
        sys.modules["FreeCADGui"] = _gui2
        _rt3 = _Registry()
        register_all(_rt3, tier0=True, patches=PatchSet())
        check("  a second pass with nothing new registers nothing",
              register_runtime(_rt3), 0)
        _gui2.extra.append("Acme_Later")
        check("  and a workbench's new commands are picked up on the next",
              register_runtime(_rt3), 1)
        check("    reachable by the name getInfo gives it",
              _rt3.get("later_thing").gui_command
              if _rt3.get("later_thing") else None, "Acme_Later")
    finally:
        if _real_gui is None:
            sys.modules.pop("FreeCADGui", None)
        else:
            sys.modules["FreeCADGui"] = _real_gui
    # An addon that declares a verb and registers a command of the same
    # name: the declared verb wins the name and the launcher is re-homed,
    # the way a displaced tier-1 verb is, rather than erased.
    from fccli.patches import PatchSet as _PS
    _decl = _PS([("addon", "<test>", {"key": "Acme", "verbs": {
        "widget_thing": {"doc": "Declared.", "emit": lambda v: None}}})])
    try:
        sys.modules["FreeCADGui"] = _RuntimeGui(["Acme_Widget"])
        _rt4 = _Registry()
        register_all(_rt4, tier0=True, patches=_decl)
        _w4 = _rt4.by_gui_command("Acme_Widget")
        check("  a declared verb re-homes the launcher it displaces",
              (_rt4.get("widget_thing").doc, _w4.name if _w4 else None),
              ("Declared.", "acme_widget_thing"))
    finally:
        if _real_gui is None:
            sys.modules.pop("FreeCADGui", None)
        else:
            sys.modules["FreeCADGui"] = _real_gui
    # Nothing to read: a FreeCADGui with no listCommands, which is what
    # the offscreen suite has, registers nothing and raises nothing.
    _rt2 = _Registry()
    _rc2 = register_all(_rt2, tier0=True, patches=PatchSet())
    check("  no GUI, no runtime commands, no error", _rc2.get("runtime", 0), 0)
    print("\n5ac. a command file round-trips, and lands where its workbench says")
    # ADR-100. The tree under fccli/lib/commands is the hand-owned layer:
    # one Markdown file per command, a generated: block the tool owns and
    # authored fields it never touches. tools/lint_dictionary.py checks the
    # tree in make lint; this checks the model the three tools share.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import command_files as _cf
    check("a workbench names its directory",
          [_cf.workbench_dir(w) for w in
           ("SketcherWorkbench", "CurvedShapesWB", None, "BIMWorkbench")],
          ["sketcher", "curvedshapes", "std", "bim"])
    _gen = {"freecad": "1.1.3", "label": "Circle From Center",
            "tooltip": "Creates a circle", "toolbar": None,
            "menu": "Geometries", "shortcut": "G, C",
            "workbench": "SketcherWorkbench",
            "wiki": "Sketcher_CreateCircle", "wiki_rev": "0499378",
            "seed": "9c1e0b7d2a44"}
    _auth = {"verb": "circle_center", "aliases": ["cc"],
             "requires": ["sketch-edit"],
             "type": {"steps": ["Radius"], "strict": True}}
    _text = _cf.render("Sketcher_CreateCircle", _gen, _auth,
                       "A circle.\n\n## See also\n\n- Sketcher_CreateArc")
    _front, _body = _cf.parse(_text)
    check("  the generated block reads back as written",
          _front["generated"], _gen)
    check("  and so do the authored fields, defaults filled in",
          _cf.authored_of(_front),
          {**{k: v for k, v in _cf.AUTHORED.items()}, **_auth})
    check("  the body is the body", _body.strip().splitlines()[0], "A circle.")
    check("  a comment in the frontmatter survives the template",
          "# authored from here down" in _text, True)
    # The wiki page reader. Every defect the review found in the bodies
    # was in untested code; each is a line here now.
    import generate_commands as _gc
    _page = (
        "---\n GuiCommand:\n   Name: Acme Thing\n   Shortcut: **G** **C**\n"
        "   Version: \n   SeeAlso: Acme_Other, Acme_More\n---\n\n# Acme Thing\n\n"
        "## Description\n\nThe <img src=x.svg> [Acme Thing](Acme_Thing.md) "
        "tool does " + "'" * 3 + "things" + "'" * 3 + " <small>(v0.21)</small> : and "
        "\\'\\'more\\'\\'\\. {{Version|1.0}}\n\n ![](images/Acme.png) \n\n*A caption*\n\n"
        "-   First item\n-   Second [item](X.md)\n    wrapped\n1.  Third\n\n"
        "### Sub heading\n\nStill the description.\n\n## Usage\n\nNot.\n\n"
        "---\n⏵ [documentation index](../README.md) > Acme > Acme Thing\n")
    _front, _desc, _redir = _gc.page_parts(_page)
    check("a page's fields are read a line at a time, not as YAML",
          (_front.get("Shortcut"), _gc.see_also(_front)),
          ("**G** **C**", ["Acme_Other", "Acme_More"]))
    check("  an empty field does not swallow the next line",
          _front.get("Version"), None)
    check("  the prose comes out clean",
          _desc.split("\n\n")[0],
          "The Acme Thing tool does things and more.")
    check("  a list stays a list; a wrapped item rejoins; numbers stay",
          _desc.split("\n\n")[1], "- First item\n- Second item wrapped\n1. Third")
    check("  a ### inside the Description is part of it; ## Usage ends it",
          _desc.split("\n\n")[2:], ["## Sub heading", "Still the description."])
    check("  the image, its caption, the template and the footer are gone",
          ("caption" in _desc, "{{" in _desc, "index" in _desc, "Not." in _desc),
          (False, False, False, False))
    _d3 = _gc.page_parts("### Description\n\nDeep.\n\n### Other\n\nx\n")
    check("  ### Description counts and ends at the next ###", _d3[1], "Deep.")
    _r = _gc.page_parts("---\n GuiCommand:\n   Name: X\n---\n\n"
                        "1.  REDIRECT [Part_Common](Part_Common.md)\n")
    check("  a redirect names where to look", _r[2], "Part_Common")
    _i = _gc.page_parts("## Introduction\n\nIntro text.\n\n## Usage\n\nx\n")
    check("  Introduction serves when there is no Description", _i[1], "Intro text.")
    # A C1 control in a label wedges YAML unless escaped.
    _weird = _cf.render("X", {"label": "a\x85b\x7fc"}, {}, "")
    check("  a control character in a harvested string round-trips",
          _cf.parse(_weird)[0]["generated"]["label"], "a\x85b\x7fc")
    # The lint says what is wrong with a wrong-typed field, once.
    _bad_dir = tempfile.mkdtemp(prefix="fccli-lint-")
    os.makedirs(os.path.join(_bad_dir, "part"))
    _gen_pb = {k: _cmds["Part_Box"].get(k) for k in
               ("label", "tooltip", "toolbar", "menu", "shortcut",
                "workbench", "wiki")}
    _gen_pb["freecad"] = _load_desc()["freecad"]
    with open(os.path.join(_bad_dir, "part", "Part_Box.md"), "w") as _fh:
        _fh.write(_cf.render("Part_Box", _gen_pb,
                             {"panel": ["pick"], "requires": "sketch-edit",
                              "family": False}, "x"))
    import lint_dictionary as _ld2
    _n2, _p2 = _ld2.lint(_bad_dir, _ld2.DESCRIPTOR, os.path.join(_bad_dir, "none.json"))
    _shapes = [p for p in _p2 if "wrong shape" in p]
    check("  a wrong-typed field is one message, and family: false is allowed",
          (len(_shapes), any("family" in p and "shape" in p for p in _p2)),
          (2, False))
    import shutil as _sh2; _sh2.rmtree(_bad_dir, ignore_errors=True)

    # The tree in the repository agrees with the descriptor: every command
    # has a file in its workbench's directory and no file names a command
    # that is not there. This is lint rule 1, run here so a stale tree
    # fails the suite and not only make lint.
    import lint_dictionary as _ld, compile_dictionary as _cd
    _n, _problems = _ld.lint(_cd.DEFAULT_TREE, _ld.DESCRIPTOR, _cd.DEFAULT_OUT)
    check("  the tree in the repository is clean", (_n, _problems[:3]),
          (len(_cmds), []))

    print("\n5ad. the command tree is read, and what it says changes the verbs")
    # ADR-100. fccli/dictionary.json is the compiled tree. A file's verb,
    # aliases, rank, family/choice and body reach the registry through
    # register_all; measured against a run with no dictionary at all, so
    # each check is the difference the tree makes.
    from fccli.factory import load_dictionary
    from fccli import families as _fam, curation as _curation
    from fccli.bus import INFO as _INFO
    _dict = load_dictionary()
    check("the compiled dictionary is shipped", bool(_dict), True)
    _bare = _Registry()
    register_all(_bare, tier0=True, patches=PatchSet(), dictionary={})
    _with = _Registry()
    _wc = register_all(_with, tier0=True, patches=PatchSet())
    check("  and register_all counts the authored files", _wc.get("authored"), 9)
    # #19: every descriptor command is some verb's gui_command. Nine were
    # not, because a typed verb added over their launcher; _make_room
    # qualifies the launcher instead.
    _reached = {getattr(_with.get(n), "gui_command", None) for n in _with.names()}
    check("  every descriptor command reaches a verb",
          sorted(c for c in _cmds if c not in _reached), [])
    _bimbox = _with.by_gui_command("BIM_Box")
    check("    BIM_Box, once lost to Part::Box's `box`, is bim_box",
          _bimbox.name if _bimbox else None, "bim_box")
    # The first two entries: generic words for workbench-specific tools.
    check("  Mesh_PolySegm is `segment` with no tree and mesh_segment with it",
          (_bare.by_gui_command("Mesh_PolySegm").name,
           _with.by_gui_command("Mesh_PolySegm").name),
          ("segment", "mesh_segment"))
    check("  Draft_Split likewise",
          (_bare.by_gui_command("Draft_Split").name,
           _with.by_gui_command("Draft_Split").name),
          ("split", "draft_split"))
    # The page reaches the verb; the one-liner stays the tooltip.
    _cc = _with.by_gui_command("Sketcher_CreateCircle")
    check("  a command's page is its manual",
          _cc.manual.startswith("The Sketcher CreateCircle tool"), True)
    check("  and its one-line doc is still the tooltip",
          _cc.doc, _cmds["Sketcher_CreateCircle"]["tooltip"])
    check("  a verb with no tree has no manual",
          _bare.by_gui_command("Sketcher_CreateCircle").manual, "")
    # NOT_ACTIONS moved to std/_families.yaml; the fallback in code is the
    # same list, so the shipped tree and a bare run agree today.
    check("  the family exclusions come from the tree",
          sorted(_dict.get("families", {}).get("exclude", [])),
          sorted(_fam.NOT_ACTIONS))
    # A dictionary handed in directly: rank, family, aliases, requires.
    _custom = {"commands": {
        "Std_ViewFitAll": {"rank": "registry", "aliases": ["fa"],
                           "requires": ["document"]},
        "Std_ViewFront": {"family": "look", "choice": "front"},
        "Std_ViewTop": {"family": "look", "choice": "top"},
        "Std_ViewRear": {"family": "look", "choice": "back"},
    }}
    _cr = _Registry()
    register_all(_cr, tier0=True, patches=PatchSet(), dictionary=_custom)
    # The launcher, not a hand-written verb that shares its gui_command.
    _fa = next(v for v in (_cr.get(n) for n in _cr.names())
               if v.gui_command == "Std_ViewFitAll" and v.open is not None)
    check("  rank: registry demotes a toolbar command",
          _curation.current().rank_of(_fa), _curation.REGISTRY)
    check("  aliases and requires ride along",
          (_cr.get("fa") is _fa, _fa.requires), (True, ["document"]))
    _look = _cr.get("look")
    check("  three files with family: look make a family verb",
          sorted(_look.steps[0].choices) if _look else None,
          ["back", "front", "top"])
    check("  and the derived `view` family lost those three",
          [c for c in _cr.get("view").steps[0].choices
           if c in ("front", "top", "rear")], [])
    # An authored name that collides is handled, never silently taken.
    _bad = {"commands": {
        "Mesh_PolySegm": {"verb": "additive_box"},       # a tier-1 name
        # a launcher's name, a family's, a typed verb's -- and one free
        "Std_ViewFitAll": {"aliases": ["cube", "view", "box", "fitall"]},
    }}
    _cb = _Registry()
    _cbc = register_all(_cb, tier0=True, patches=PatchSet(), dictionary=_bad)
    _seg = _cb.by_gui_command("Mesh_PolySegm")
    check("  a verb that collides with a typed verb is re-homed, not lost",
          (_seg.name if _seg else None,
           getattr(_cb.get("additive_box"), "creates", None)),
          ("mesh_additive_box", "PartDesign::AdditiveBox"))
    check("  an alias cannot take a name in use, a family's, or a typed verb's",
          (getattr(_cb.get("cube"), "gui_command", None) != "Std_ViewFitAll",
           _cb.get("view").family, _cb.get("box").creates,
           _cb.get("fitall").gui_command, _cbc.get("aliases_dropped")),
          (True, "view", "Part::Box", "Std_ViewFitAll", 3))
    # Put the shared curation back the way the shipped tree has it.
    _curation.load(_load_desc(), _dict)
    # A dictionary that will not parse costs its overrides, not the verbs.
    from fccli.factory import load_dictionary as _ld_fn
    _broken = os.path.join(tempfile.mkdtemp(prefix="fccli-dict-"), "d.json")
    open(_broken, "w").write("{not json")
    check("  a broken dictionary is treated as absent", _ld_fn(_broken), None)
    # man shows the page.
    # man reads the shell's own registry, which register_all filled from
    # the shipped tree earlier in this suite.
    _seen_man = []
    _man_bus = Bus()
    _man_bus.subscribe(_seen_man.append)
    _eng = Engine(_man_bus, REGISTRY)
    _eng.submit("man mesh_segment")
    _texts = [m.text for m in _seen_man if m.kind == _INFO]
    check("  man prints DESCRIPTION from the page",
          any(t == "DESCRIPTION" for t in _texts)
          and any("segment" in t.lower() for t in _texts), True)
    # The page's See also joins FreeCAD's toolbar neighbours, as verbs.
    _seen_man.clear()
    _eng.submit("man circle_from_center")
    _texts = [m.text for m in _seen_man if m.kind == _INFO]
    _arc = REGISTRY.by_gui_command("Sketcher_CreateArc").name
    _line = next((t for t in _texts if _arc in t), "")
    check("  the page's See also is answered in verb names, once",
          (_texts.count("SEE ALSO"), any("Sketcher_CreateArc" in t for t in _texts),
           _arc in [n.strip() for n in _line.split(",")]),
          (1, False, True))

    print("\n5ae. reconcile reads a new harvest and brings the tree to it")
    # ADR-100's prize. A copy of the tree and a descriptor with one of
    # every kind of change; the report names each, --apply performs each,
    # the lint holds afterwards, and a second run has nothing to say.
    import reconcile as _rc, shutil as _shutil, json as _json
    _tmp = tempfile.mkdtemp(prefix="fccli-reconcile-")
    _tree = os.path.join(_tmp, "commands")
    _shutil.copytree(_cd.DEFAULT_TREE, _tree)
    _old = os.path.join(_tmp, "old.json"); _new = os.path.join(_tmp, "new.json")
    _shutil.copyfile(_ld.DESCRIPTOR, _old)
    _d = _json.load(open(_old)); _c = _d["commands"]
    _d["freecad"] = "9.9.9"
    _c["Acme_New"] = {"name": "Acme_New", "label": "New Thing",
                      "tooltip": "Does a new thing", "toolbar": None,
                      "menu": None, "shortcut": None, "wiki": None}
    del _c["Std_Test1"]
    _c["Part_Box"]["label"] = "Cuboid"
    _c["Draft_Line"]["workbench"] = "BIMWorkbench"
    # Re-homed and authored, both: everything a person wrote must move.
    with open(os.path.join(_tree, "draft", "Draft_Line.md")) as _fh:
        _dl = _fh.read()
    _dl = _dl.replace("verb: null", 'verb: "dline"').replace(
        "aliases: []", "aliases:\n- dl").replace("rank: null", 'rank: "registry"')
    with open(os.path.join(_tree, "draft", "Draft_Line.md"), "w") as _fh:
        _fh.write(_dl)
    _c["Std_TestConsoleOutput"]["tooltip"] = "Console output, verified"
    _c["Std_Test2"]["tooltip"] = "Test 2 moved"
    _c["Mesh_PolySegm"]["label"] = "Mesh Segment"
    _json.dump(_d, open(_new, "w"))
    with open(os.path.join(_tree, "std", "Std_Test2.md"), "a") as _fh:
        _fh.write("\nA person wrote this.\n")
    _rep = _rc.reconcile(_tree, _old, _new, apply=False, quiet=True)
    # Without the wiki clone no body is compared; the rest of the report
    # is the same, and the suite says which world it ran in.
    _online = not _rep.no_docs
    check("the report names one of each" + ("" if _online else " (no clone)"),
          (_rep.stamp, _rep.added, [r.split(" ")[0] for r in _rep.removed],
           [r.split(":")[0] for r in _rep.rehomed], _rep.reseeded,
           [r.split(":")[0] for r in _rep.conflicts],
           [r.split(":")[0] for r in _rep.identity]),
          (("1.1.3", "9.9.9"), ["Acme_New"], ["Std_Test1"], ["Draft_Line"],
           ["Std_TestConsoleOutput"] if _online else [],
           ["Std_Test2"] if _online else [], ["Mesh_PolySegm"]))
    check("  and every changed field",
          sorted(r.split(":")[0] for r in _rep.changed),
          ["Mesh_PolySegm", "Part_Box", "Std_Test2", "Std_TestConsoleOutput"])
    check("  a dry run writes nothing",
          os.path.exists(os.path.join(_tree, "std", "Acme_New.md")), False)
    _rc.reconcile(_tree, _old, _new, apply=True, quiet=True)
    _front, _body = _cf.read(os.path.join(_tree, "std", "Std_Test2.md"))
    check("  applied: the conflict keeps the written body",
          _body.strip().endswith("A person wrote this."), True)
    _front2, _body2 = _cf.read(os.path.join(_tree, "std",
                                            "Std_TestConsoleOutput.md"))
    check("  applied: the unedited body is reseeded",
          _body2.strip(), "Console output, verified." if _online
          else "Run test cases to verify console messages.")
    check("  applied: files moved, added, retired",
          (os.path.exists(os.path.join(_tree, "bim", "Draft_Line.md")),
           os.path.exists(os.path.join(_tree, "draft", "Draft_Line.md")),
           os.path.exists(os.path.join(_tree, "std", "Acme_New.md")),
           os.path.exists(os.path.join(_tree, "_retired", "std", "Std_Test1.md"))),
          (True, False, True, True))
    _front3, _ = _cf.read(os.path.join(_tree, "part", "Part_Box.md"))
    check("  applied: generated block carries the new label and stamp",
          (_front3["generated"]["label"], _front3["generated"]["freecad"]),
          ("Cuboid", "9.9.9"))
    _front4, _ = _cf.read(os.path.join(_tree, "bim", "Draft_Line.md"))
    check("  applied: the re-homed file keeps everything authored",
          (_front4.get("verb"), _front4.get("aliases"), _front4.get("rank")),
          ("dline", ["dl"], "registry"))
    # --force keeps a written body AND the seed it departed from, so a
    # later reconcile still sees it as written rather than laundering it.
    # _old is the new descriptor by now: --apply copied it there.
    _gc.generate(_tree, force=True, quiet=True, descriptor_path=_old)
    _front5, _body5 = _cf.read(os.path.join(_tree, "std", "Std_Test2.md"))
    check("  --force keeps the written body and its old seed",
          (_body5.strip().endswith("A person wrote this."),
           _cf.edited(_front5, _body5)), (True, True))
    _n, _problems = _ld.lint(_tree, _old, os.path.join(_tmp, "dictionary.json"))
    check("  the lint holds against the descriptor it applied",
          (_n, _problems[:2]), (1111, []))
    # Identity is reported on every run until the entry is deleted; it is
    # advice, not a change. Everything else is settled.
    _again = _rc.reconcile(_tree, _old, _new, apply=False, quiet=True)
    check("  and a second run has only the identity advice left",
          (_again.stamp, _again.added, _again.removed, _again.rehomed,
           _again.changed, _again.reseeded, _again.conflicts,
           len(_again.identity)),
          (None, [], [], [], [], [], [], 1))
    # Offline: no clone means no page to compare, so no body is touched --
    # otherwise 835 wiki-seeded bodies would "move" to their tooltips.
    _shutil.copytree(_cd.DEFAULT_TREE, os.path.join(_tmp, "offline"))
    import docs_clone as _dc
    _was = _dc.ensure
    _dc.ensure = lambda **kw: None
    try:
        _off = _rc.reconcile(os.path.join(_tmp, "offline"), _old, _new,
                             apply=True, quiet=True)
    finally:
        _dc.ensure = _was
    _fo, _bo = _cf.read(os.path.join(_tmp, "offline", "sketcher",
                                     "Sketcher_CreateCircle.md"))
    check("  offline, bodies are left alone and the report says so",
          (_off.no_docs, _off.reseeded, _bo.startswith("The Sketcher CreateCircle tool")),
          (True, [], True))
    _shutil.rmtree(_tmp, ignore_errors=True)

    print("\n5af. the root the terminal navigates")
    # ADR-601. A real directory laid out after the FHS, a working directory
    # on the session, and cd/ls/pwd/cat as verbs on it. Under a temporary
    # XDG_DATA_HOME so nothing here touches the operator's root.
    from fccli import root as _root
    _xdg_was = os.environ.get("XDG_DATA_HOME")
    _xdg = tempfile.mkdtemp(prefix="fccli-root-")
    os.environ["XDG_DATA_HOME"] = _xdg
    try:
        _notes = _root.layout()
        _r = _root.root()
        check("the root is under XDG_DATA_HOME", _r, os.path.join(_xdg, "fccli"))
        check("  bin, etc and lib exist",
              all(os.path.isdir(os.path.join(_r, d)) for d in ("bin", "etc", "lib")),
              True)
        check("  lib/commands links to the shipped tree",
              os.path.realpath(os.path.join(_r, "lib", "commands")),
              os.path.realpath(_cd.DEFAULT_TREE))
        check("  macros links to FreeCAD's macro directory, or says why not",
              os.path.islink(os.path.join(_r, "macros"))
              or any(n.startswith("macros:") for n in _notes), True)
        _again = _root.layout()
        check("  a second layout changes nothing and says nothing new",
              _again, _notes)
        # The jail.
        check("  .. above / stays at /",
              [_root.resolve("/", ".."), _root.resolve("/a", "../../.."),
               _root.resolve("/a/b", "../c"), _root.resolve("/a", "/x/./y/")],
              ["/", "/", "/a/c", "/x/y"])
        # Verbs on it, through the engine, with a session.
        os.makedirs(os.path.join(_r, "plinth", "notes"))
        open(os.path.join(_r, "plinth", "tower.fccli"), "w").write("box 0,0,0 10 10 10\n")
        open(os.path.join(_r, "plinth", "README.md"), "w").write("# Plinth\n\nA tower.\n")
        from fccli.session import Session as _Session
        _rbus = Bus(); _rseen = []
        _rbus.subscribe(_rseen.append)
        _reng = Engine(_rbus, REGISTRY)
        _rsess = _Session(_reng, _rbus, history=_History(os.path.join(_xdg, "h")))
        def _lines():
            return [m.text for m in _rseen if m.kind == _INFO]
        _reng.submit("ls")
        check("  ls at / shows the layout, directories first",
              [l.strip() for l in _lines() if "bin/" in l][:1] != [], True)
        _rseen.clear(); _reng.submit("cd plinth")
        check("  cd moves the session", _rsess.cwd, "/plinth")
        check("    and the socket state carries it", _rsess.state()["cwd"], "/plinth")
        _rseen.clear(); _reng.submit("ls")
        check("  ls in it marks a directory and a script",
              sorted(n for row in _lines() for n in row.split()),
              ["README.md", "notes/", "tower.fccli*"])
        _rseen.clear(); _reng.submit("pwd")
        check("  pwd says where", _lines(), ["/plinth"])
        _rseen.clear(); _reng.submit("cat README.md")
        check("  cat prints a note", _lines(), ["# Plinth", "", "A tower."])
        _rseen.clear(); _reng.submit("cd nowhere")
        check("  cd to nothing is an error and stays put",
              ([m.text for m in _rseen if m.kind == ERROR] != [], _rsess.cwd),
              (True, "/plinth"))
        _rseen.clear(); _reng.submit("cd ../../..")
        check("  cd cannot leave the root", _rsess.cwd, "/")
        _reng.submit("cd plinth")
        from fccli.completion import path_entries as _pe
        check("  path completion lists the working directory, names only",
              _pe(_reng), ["notes/", "README.md", "tower.fccli"])
        # What layout must never do: write through a link, or give up.
        _other = tempfile.mkdtemp(prefix="fccli-elsewhere-")
        _r2 = os.path.join(_xdg, "fccli2")
        os.makedirs(_r2)
        os.symlink(_other, os.path.join(_r2, "lib"))
        open(os.path.join(_r2, "bin"), "w").write("a file")
        _notes2 = _root.layout(_r2)
        check("  a linked lib is left alone and nothing is made inside it",
              (sorted(os.listdir(_other)), any("lib is a link" in n for n in _notes2)),
              ([], True))
        check("  a file named bin is said once and the rest is still made",
              (any("bin is a file" in n for n in _notes2),
               os.path.isdir(os.path.join(_r2, "etc"))), (True, True))
        # The root itself as a link is the operator's: followed, not refused.
        _elsewhere = tempfile.mkdtemp(prefix="fccli-git-")
        _r4 = os.path.join(_xdg, "fccli4"); os.symlink(_elsewhere, _r4)
        _n4 = _root.layout(_r4)
        check("  a root that is itself a link is followed",
              (os.path.isdir(os.path.join(_elsewhere, "bin")),
               any("link" in n for n in _n4)), (True, False))
        _r3 = os.path.join(_xdg, "fccli3"); os.makedirs(_r3); _n3 = []
        _root._link(os.path.join(_r3, "macros"), "Macro", _n3)
        check("  a relative macro path makes no link",
              (os.path.lexists(os.path.join(_r3, "macros")), len(_n3)), (False, 1))
        # cat on what is not text, and on what is too long.
        with open(os.path.join(_r, "plinth", "big.txt"), "w") as _fh:
            _fh.write("x" * (_root.LIMIT + 10))
        with open(os.path.join(_r, "plinth", "odd.txt"), "w") as _fh:
            _fh.write("a\x1b]0;title\x07b\n")
        _rseen.clear(); _reng.submit("cat /plinth/odd.txt")
        check("  cat shows only printable characters", _lines(), ["a?]0;title?b"])
        _rseen.clear(); _reng.submit("cat /plinth/big.txt")
        check("  and says when it cut a file short",
              _lines()[-1].startswith("(/plinth/big.txt: cut at"), True)
        _rseen.clear(); _reng.submit("ls /plinth/nothing")
        check("  an error names the virtual path, never the disk",
              ([m.text for m in _rseen if m.kind == ERROR][-1].startswith("ls failed: /plinth/nothing"),
               _xdg in [m.text for m in _rseen if m.kind == ERROR][-1]), (True, False))
        check("  the idle prompt carries the path",
              _rsess.state()["cwd"], "/plinth")
    finally:
        if _xdg_was is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = _xdg_was
        import shutil as _sh3; _sh3.rmtree(_xdg, ignore_errors=True)

    print("\n5ag. a script is lines the parser already accepts, run as one verb")
    # ADR-601. A .fccli in bin/ is a verb by file name with the arguments
    # its frontmatter declares; elsewhere it runs by path with them inline.
    # The call is one history line; the lines inside are not recorded; the
    # first error or unanswered prompt stops it.
    from fccli import scripts as _scripts
    _xdg_was = os.environ.get("XDG_DATA_HOME")
    _xdg = tempfile.mkdtemp(prefix="fccli-scripts-")
    os.environ["XDG_DATA_HOME"] = _xdg
    try:
        _root.layout()
        _r = _root.root()
        with open(os.path.join(_r, "bin", "plinth.fccli"), "w") as _fh:
            _fh.write("---\ndoc: A plinth.\nsteps:\n"
                      "  - {id: size, kind: quantity, prompt: Size, unit: mm}\n"
                      "  - {id: height, kind: quantity, prompt: Height, unit: mm, default: 5}\n"
                      "---\n# the plinth\nnew\nbox 0,0,0 $size $size $height   # a slab\n")
        with open(os.path.join(_r, "bin", "plinth.md"), "w") as _fh:
            _fh.write("A square slab, size by height.\n")
        _added, _notes = _scripts.register(REGISTRY)
        check("a script in bin is a verb by file name",
              (_added, _notes, REGISTRY.get("plinth").steps[0].id), (["plinth"], [], "size"))
        from fccli.session import Session as _Session
        _sbus = Bus(); _sseen = []
        _sbus.subscribe(_sseen.append)
        _seng = Engine(_sbus, REGISTRY)
        _ssess = _Session(_seng, _sbus, history=_History(os.path.join(_xdg, "h")))
        _ssess.submit("plinth 30")
        _results = [m for m in _sseen if m.kind == RESULT]
        check("  it runs its lines and the call is the one recorded result",
              ([m.data.get("verb") for m in _results],
               [m.data.get("record") for m in _results]),
              (["new", "box", "plinth"], [False, False, True]))
        check("  the argument reached the line as typed text",
              round(float(App.ActiveDocument.Objects[-1].Length), 3), 30.0)
        check("  the default filled the other",
              round(float(App.ActiveDocument.Objects[-1].Height), 3), 5.0)
        check("  history holds the call and not the lines",
              [h for h in _ssess.history.tail(5) if "plinth" in h or "box 0,0,0 30" in h],
              ["plinth 30.00mm"])
        check("  and the engine is idle after", (_seng.state, _seng.suppress_record), ("idle", 0))
        # A bad line stops it, before what follows.
        with open(os.path.join(_r, "bin", "broken.fccli"), "w") as _fh:
            _fh.write("no_such_verb_xyz\nbox 0,0,0 1 1 1\n")
        _scripts.register(REGISTRY)
        _sseen.clear(); _before = len(App.ActiveDocument.Objects)
        _ssess.submit("broken")
        check("  the first error stops a script",
              ([m.text for m in _sseen if m.kind == ERROR][-1].startswith("broken failed: broken stopped at line 1"),
               len(App.ActiveDocument.Objects)), (True, _before))
        with open(os.path.join(_r, "bin", "waits.fccli"), "w") as _fh:
            _fh.write("circle\nbox 0,0,0 1 1 1\n")
        _scripts.register(REGISTRY)
        _sseen.clear()
        _ssess.submit("waits")
        check("  a line that still wants input stops it and cancels",
              ("still wants" in [m.text for m in _sseen if m.kind == ERROR][-1], _seng.state),
              (True, "idle"))
        # A line that errors and still wants more: closed, then reported.
        with open(os.path.join(_r, "bin", "half.fccli"), "w") as _fh:
            _fh.write("box 0,0,0 1 1 zzz\n")
        _scripts.register(REGISTRY)
        _sseen.clear(); _ssess.submit("half")
        check("  an erroring line that left a prompt open is closed",
              (_seng.state, _seng.verb), ("idle", None))
        check("  and an empty Enter repeats the script, not its last line",
              _seng.repeat_hint, "half")
        check("  driving is back to zero", _seng.driving, 0)
        # A script that runs itself stops.
        with open(os.path.join(_r, "bin", "ouro.fccli"), "w") as _fh:
            _fh.write("ouro\n")
        _scripts.register(REGISTRY)
        _sseen.clear(); _ssess.submit("ouro")
        check("  a script that runs itself stops at the depth limit",
              (any("deep" in m.text for m in _sseen if m.kind == ERROR), _seng.script_depth),
              (True, 0))
        # A # inside an argument is the argument's.
        _f2, _l2 = _scripts.parse("save /tmp/a#b.FCStd  # comment\n# whole\n")
        check("  a comment needs a space before its #", _l2, ["save /tmp/a#b.FCStd"])
        # Frontmatter that would take a name: refused, with the verb's name.
        with open(os.path.join(_r, "bin", "sneaky.fccli"), "w") as _fh:
            _fh.write("---\nverb: box\naliases: [cd, zq]\n---\npwd\n")
        _ad, _nt = _scripts.register(REGISTRY)
        check("  a verb: that is taken is refused; a taken alias is dropped",
              (REGISTRY.get("box").script, any("box is taken" in n for n in _nt)),
              (None, True))
        with open(os.path.join(_r, "bin", "sneaky.fccli"), "w") as _fh:
            _fh.write("---\naliases: [cd, zq]\n---\npwd\n")
        _ad, _nt = _scripts.register(REGISTRY)
        check("    the script registers under its own name with the free alias",
              (REGISTRY.get("sneaky") is not None, REGISTRY.get("cd").script,
               REGISTRY.get("zq").name), (True, None, "sneaky"))
        # An optional step needs a default; an unknown kind is refused.
        with open(os.path.join(_r, "bin", "loose.fccli"), "w") as _fh:
            _fh.write("---\nsteps:\n  - {id: a, kind: quantity, optional: true}\n---\npwd\n")
        _ad, _nt = _scripts.register(REGISTRY)
        check("  an optional step without a default is refused",
              any("needs a default" in n for n in _nt), True)
        # A default in the step's own unit.
        with open(os.path.join(_r, "bin", "inch.fccli"), "w") as _fh:
            _fh.write("---\nsteps:\n  - {id: w, kind: quantity, unit: in, default: 2}\n---\n"
                      "box 0,0,0 $w $w 1\n")
        _scripts.register(REGISTRY)
        _sseen.clear(); _ssess.submit("inch")
        check("  a default is written in the step's unit",
              round(float(App.ActiveDocument.Objects[-1].Length), 2), 50.8)
        _sseen.clear(); _ssess.submit("inch"); _ssess.submit("")
        check("    and reads the same when Enter takes it at the prompt",
              round(float(App.ActiveDocument.Objects[-1].Length), 2), 50.8)
        _sseen.clear(); _ssess.submit("inch 3in")
        check("    and an answer goes into the line as it was typed",
              round(float(App.ActiveDocument.Objects[-1].Length), 2), 76.2)
        # By path, arguments inline; and the ./ sugar.
        os.makedirs(os.path.join(_r, "plinth"))
        with open(os.path.join(_r, "plinth", "tower.fccli"), "w") as _fh:
            _fh.write("---\nsteps:\n  - {id: size, kind: quantity, unit: mm}\n---\n"
                      "box 0,0,0 $size $size 50\n")
        _sseen.clear(); _ssess.submit("run plinth/tower.fccli 12")
        check("  run by path with the argument inline",
              ([m.text for m in _sseen if m.kind == ERROR],
               round(float(App.ActiveDocument.Objects[-1].Length), 3)), ([], 12.0))
        check("  and it left no verb behind", REGISTRY.get("tower"), None)
        check("  and history holds the run call only",
              [h for h in _ssess.history.tail(3) if "tower" in h], ["run plinth/tower.fccli 12"])
        _ssess.submit("cd bin"); _ssess.submit("./plinth.fccli 9"); _ssess.submit("cd /")
        check("  a bin script run by path is still a verb after",
              (REGISTRY.get("plinth").script is not None,
               round(float(App.ActiveDocument.Objects[-1].Length), 3)), (True, 9.0))
        _sseen.clear(); _ssess.submit("run plinth/tower.fccli")
        check("  by path without its argument is an error, not a prompt",
              ("wants" in [m.text for m in _sseen if m.kind == ERROR][-1], _seng.state),
              (True, "idle"))
        _ssess.submit("cd plinth"); _sseen.clear(); _ssess.submit("./tower.fccli 7")
        check("  ./tower is run tower",
              ([m.text for m in _sseen if m.kind == ERROR],
               round(float(App.ActiveDocument.Objects[-1].Length), 3)), ([], 7.0))
        # A macro is FreeCAD's tier.
        with open(os.path.join(_r, "plinth", "hello.FCMacro"), "w") as _fh:
            _fh.write("import FreeCAD\nFreeCAD.fccli_probe = 'ran'\n")
        _sseen.clear(); _ssess.submit("run hello.FCMacro")
        check("  a macro runs as Python",
              ([m.text for m in _sseen if m.kind == ERROR], getattr(App, "fccli_probe", None)),
              ([], "ran"))
        with open(os.path.join(_r, "plinth", "bad.FCMacro"), "w") as _fh:
            _fh.write("import FreeCAD\nFreeCAD.fccli_count = getattr(FreeCAD, 'fccli_count', 0) + 1\n"
                      "raise ValueError('boom')\n")
        _sseen.clear(); _ssess.submit("run /plinth/bad.FCMacro")
        check("  a macro that raises ran once and is reported once",
              (getattr(App, "fccli_count", 0),
               sum(1 for m in _sseen if m.kind == ERROR)), (1, 1))
        # rehash, and man.
        with open(os.path.join(_r, "bin", "gadget.fccli"), "w") as _fh:
            _fh.write("pwd\n")
        with open(os.path.join(_r, "bin", "new.fccli"), "w") as _fh:
            _fh.write("pwd\n")
        _sseen.clear(); _ssess.submit("rehash")
        check("  rehash adds a new script and refuses a taken name",
              (REGISTRY.get("gadget") is not None,
               getattr(REGISTRY.get("new"), "script", None),
               any("new is taken" in m.text for m in _sseen)), (True, None, True))
        _sseen.clear(); _ssess.submit("man plinth")
        _mt = [m.text for m in _sseen if m.kind == _INFO]
        check("  man on a script shows its note and its path",
              ("DESCRIPTION" in _mt, any("A square slab" in t for t in _mt),
               "SCRIPT" in _mt), (True, True, True))
    finally:
        for _n in ("plinth", "broken", "waits", "gadget", "half", "ouro",
                   "sneaky", "inch"):
            REGISTRY.remove(_n)
        if _xdg_was is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = _xdg_was
        import shutil as _sh4; _sh4.rmtree(_xdg, ignore_errors=True)
    print("\n5ah. the prompt shows where the session is")
    # ADR-300. One STATE message from the session, rendered by both
    # terminals; completion ordered by the active workbench within a
    # rank; a command that cannot run here says so before running.
    from fccli import context as _context
    from fccli.bus import STATE as _STATE, PROMPT as _PROMPT
    check("the segment leaves out what is empty",
          [_context.segment(c) for c in (
              {}, {"workbench": "Part"}, {"cwd": "/plinth"},
              {"workbench": "PartDesign", "active": ["Body", "Sketch"],
               "dirty": True, "selection": 2, "cwd": "/plinth"},
              {"dirty": True})],
          ["", "Part", "/plinth", "PartDesign Body › Sketch* [2] /plinth", "*"])
    check("  and the prompt is bare with nothing to say",
          (_context.prompt({}), _context.prompt({"workbench": "Part"})),
          ("> ", "Part > "))
    check("  a requires reads as a reason",
          (_context.reason(["sketch-edit", "selection:face"]), _context.reason([])),
          ("needs a sketch in edit mode, a face selected", "is not available here"))
    # With a GUI that answers.
    class _Sel:
        items = ["a", "b"]
        def getSelection(self): return list(self.items)
    class _Wb:
        def __init__(self, n): self._n = n
        def name(self): return self._n
    class _Cmd:
        def __init__(self, on): self.on = on
        def isActive(self): return self.on
    class _CtxGui:
        ActiveDocument = None
        Selection = _Sel()
        wb = "SketcherWorkbench"
        cmds = {}
        def activeWorkbench(self): return _Wb(self.wb)
        def listCommands(self): return []
        class Command:
            registry = {}
            @classmethod
            def get(cls, name): return cls.registry.get(name)
    _ctx_gui = _CtxGui()
    _real_gui = sys.modules.get("FreeCADGui")
    sys.modules["FreeCADGui"] = _ctx_gui
    try:
        check("  the snapshot reads the GUI",
              (_context.workbench(), _context.selected()), ("Sketcher", 2))
        from fccli.session import Session as _Session
        _cbus = Bus(); _cseen = []
        _cbus.subscribe(_cseen.append)
        _ceng = Engine(_cbus, REGISTRY)
        _csess = _Session(_ceng, _cbus, history=_History(os.path.join(tempfile.mkdtemp(), "h")))
        _csess.cwd = "/plinth"
        _cseen.clear(); _ceng.submit("pwd")
        _states = [m for m in _cseen if m.kind == _STATE]
        # Earlier sections leave documents dirty; the star is theirs.
        check("  the session answers an idle PROMPT with STATE",
              (len(_states) >= 1, _states[-1].text.replace("*", ""),
               _states[-1].data.get("cwd")),
              (True, "Sketcher [2] /plinth", "/plinth"))
        check("  and the socket state carries the same segment",
              _csess.state()["context"]["segment"].replace("*", ""),
              "Sketcher [2] /plinth")
        _cseen.clear(); _csess.announce_context()
        check("  a change announces without a command",
              [m.kind for m in _cseen], [_STATE])
        # Order: a Sketcher command before a Part one of the same rank.
        from fccli import curation as _cur3
        _cur3.load(_load_desc(), _dict)
        _ordered = _cur3.current().order(REGISTRY, ["cube", "circle_from_center"],
                                         workbench=_context.workbench())
        check("  completion puts this workbench's commands first within a rank",
              _ordered[0] if _cur3.current().rank_of(REGISTRY.get("cube")) ==
              _cur3.current().rank_of(REGISTRY.get("circle_from_center"))
              else "circle_from_center", "circle_from_center")
        check("  and leaves the order alone without a workbench",
              _cur3.current().order(REGISTRY, ["cube", "circle_from_center"]),
              _cur3.current().order(REGISTRY, ["cube", "circle_from_center"], workbench=None))
        # Part active: a Part command first, PartDesign's not counted as
        # Part's by prefix. additive_helix is PartDesign_Helix and
        # appearance_per_face is a Part command, both promoted; the
        # PartDesign name sorts first alphabetically, so only the home key
        # can put the Part command ahead -- and it does only when the
        # workbench is matched by equality, since "partdesignworkbench"
        # startswith "part".
        _c3 = _cur3.current()
        _pd, _pt = "additive_helix", "appearance_per_face"
        assert _c3.rank_of(REGISTRY.get(_pd)) == _c3.rank_of(REGISTRY.get(_pt))
        assert _pd < _pt
        check("  a PartDesign command is not Part's by prefix",
              _c3.order(REGISTRY, [_pd, _pt], workbench="part"),
              [_pt, _pd])
        # A hand-written verb that runs a Std command keeps its place: its
        # command has no workbench, so the home key is neutral. transform
        # is hand-written (Std_TransformManip); box is Part_Box.
        assert _c3.rank_of(REGISTRY.get("transform")) == _c3.rank_of(REGISTRY.get("box"))
        check("  a verb whose command has no workbench keeps its place",
              (_c3.order(REGISTRY, ["transform", "box"], workbench="part"),
               _c3.order(REGISTRY, ["box", "transform"], workbench="part")),
              (["box", "transform"], ["box", "transform"]))
        # Refusal: FreeCAD says no, the file says why.
        from fccli import panels as _pn
        _CtxGui.Command.registry["Sketcher_CreateCircle"] = _Cmd(False)
        _CtxGui.Command.registry["Std_ViewFront"] = _Cmd(False)
        _ctx_gui.listCommands = lambda: ["Sketcher_CreateCircle", "Std_ViewFront"]
        _cc = REGISTRY.by_gui_command("Sketcher_CreateCircle")
        _cc.requires = ["sketch-edit"]
        _cseen.clear(); _ceng.submit(_cc.name)
        check("  a command that cannot run here says why, from its file",
              [m.text for m in _cseen if m.kind == ERROR],
              [f"{_cc.name}: needs a sketch in edit mode"])
        _vf = next(v for v in (REGISTRY.get(n) for n in REGISTRY.names())
                   if v.gui_command == "Std_ViewFront" and v.open is not None)
        _cseen.clear(); _ceng.submit(_vf.name)
        check("  and says it is not available when the file says nothing",
              [m.text for m in _cseen if m.kind == ERROR],
              [f"{_vf.name}: is not available here"])
        check("  can_run is True when FreeCAD cannot say",
              _pn.can_run("Nothing_Here"), True)
        _cc.requires = []
    finally:
        if _real_gui is None:
            sys.modules.pop("FreeCADGui", None)
        else:
            sys.modules["FreeCADGui"] = _real_gui

    print("\n5ai. the zoom and view tables moved into family/choice entries")
    # ADR-100 test case. shell.py's ZOOM_TARGETS and VIEW_TARGETS are gone;
    # the five fit/zoom commands carry family: zoom in their files, with
    # the family's aliases and default in std/_families.yaml, and the view
    # commands keep their alternate spellings as `also`.
    check("the code tables are gone", (hasattr(_shell_mod, "ZOOM_TARGETS"),
          hasattr(_shell_mod, "VIEW_TARGETS")), (False, False))
    _reng5 = Engine(Bus(), REGISTRY)
    from fccli.factory import load_dictionary as _ld5
    _d5 = _ld5()
    _zoom = REGISTRY.get("zoom")
    check("  zoom is a curated family with its aliases and default",
          (sorted(set(_zoom.steps[0].choices)),
           sorted(_zoom.aliases), _zoom.steps[0].default),
          (["all", "extents", "in", "out", "selection", "window"],
           ["fit", "zf"], "all"))
    check("  fit and zf reach it", (REGISTRY.get("fit") is _zoom,
          REGISTRY.get("zf") is _zoom), (True, True))
    from fccli.families import families as _fams, overrides_of as _oo, meta_of as _mo
    _over, _exc = _oo(_d5)
    _fam5 = _fams(_load_desc()["commands"], overrides=_over, exclude=_exc)
    check("  extents and all are the same command",
          (_fam5["zoom"]["extents"]["command"], _fam5["zoom"]["all"]["command"]),
          ("Std_ViewFitAll", "Std_ViewFitAll"))
    check("  the family's meta comes from _families.yaml",
          _mo(_d5, "zoom").get("aliases"), ["fit", "zf"])
    # A bare zoom finishes on the one optional step; the default runs.
    _ran = []
    class _RunGui:
        def runCommand(self, c): _ran.append(c)
    _rg = _RunGui(); _rgw = sys.modules.get("FreeCADGui")
    sys.modules["FreeCADGui"] = _rg
    try:
        _zoom.emit({"_engine": None})
        _zoom.emit({"target": "extents", "_engine": None})
    finally:
        if _rgw is None: sys.modules.pop("FreeCADGui", None)
        else: sys.modules["FreeCADGui"] = _rgw
    check("  a bare zoom runs its default, and extents is the same command",
          _ran, ["Std_ViewFitAll", "Std_ViewFitAll"])
    check("  a choice step lists the family's choices on the space",
          _complete(_reng5, "zoom ")[2][:3], ["all", "extents", "in"])
    check("  and narrows as it is typed", _complete(_reng5, "zoom ex")[2], ["extents"])
    _view = REGISTRY.get("view")
    check("  view keeps its alternate spellings",
          all(x in set(_view.steps[0].choices)
              for x in ("front", "back", "rear", "iso", "isometric", "axonometric")),
          True)
    # The lint refuses two commands claiming one choice in a family.
    _cldir = tempfile.mkdtemp(prefix="fccli-choice-")
    os.makedirs(os.path.join(_cldir, "std"))
    for _n, _ch in (("Std_ViewFitAll", "all"), ("Std_ViewFitSelection", "all")):
        _g = {k: _cmds[_n].get(k) for k in ("label", "tooltip", "toolbar",
              "menu", "shortcut", "workbench", "wiki")}
        _g["freecad"] = _load_desc()["freecad"]
        with open(os.path.join(_cldir, "std", _n + ".md"), "w") as _fh:
            _fh.write(_cf.render(_n, _g, {"family": "zoom", "choice": _ch}, "x"))
    import lint_dictionary as _ld6
    _ln, _lp = _ld6.lint(_cldir, _ld6.DESCRIPTOR, os.path.join(_cldir, "none.json"))
    check("  a choice claimed twice in a family is a lint error",
          any("is also" in p and "zoom" in p for p in _lp), True)
    import shutil as _sh5; _sh5.rmtree(_cldir, ignore_errors=True)

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


def main():
    """Run the suite, and put the unit schema back whatever happens.

    UserSchema is a real FreeCAD preference that persists to user.cfg, and
    4f moves it to exercise the schemas. The restore used to sit on the
    happy path, so a failing check anywhere after it left the operator in
    ImperialBuilding -- and every later run of the suite then failed on
    bare numbers meaning inches, which reads as a code regression.
    """
    from fccli import units as _u
    entry = _u.current_name()
    try:
        return _run()
    finally:
        try:
            _u.set_schema(entry)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
