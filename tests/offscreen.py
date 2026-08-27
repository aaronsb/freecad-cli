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

from fccli.bus import Bus, ERROR, INFO, LIVE, PROMPT, RESULT  # noqa: E402
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
        # Path::FeatureShape rather than PartDesign::Groove, which the
        # GH #69 round tuned: the example has to be a type nobody has
        # written a block for, and a Path feature is outside that class.
        untuned = fresh.get("feature_shape")
        check("an unpatched type is still a usable verb",
              untuned is not None and len(untuned.steps) > 3, True)
        check("enumerations become choices",
              any(st.choices for st in untuned.steps), True)
        # GH #52: a generated step list is the type's properties in
        # alphabetical order, so `FuzzyTolerance` sat in front of the
        # length pad is about and `pad 10` set the tolerance. The command
        # file names the order instead.
        pad = fresh.get("pad")
        check("  a tuned type leads with the argument the command is about",
              [s.id for s in pad.steps][0], "Length")
        check("    and the tolerance that used to swallow it is gone",
              [s.id for s in pad.steps].count("FuzzyTolerance"), 0)
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
    check("select completes document objects too",
          hits("select Brac"), ["Bracket"])
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

    print("\n5al. every description rule fails when its fault is put back")
    # GH #48, the description spec's mechanical half (A2, A3, A5, A6). A
    # check nobody has seen fail is a check nobody has seen: each case
    # here is one fault, reintroduced, and the rule it must fire. The
    # first is the control -- the same command, correct, silent.
    import descriptions as _dsc
    _spec_desc = _load_desc()
    _spec_modes = _dsc.load_modemap()

    def _spec(commands, types=None, body="a body that is nobody's summary"):
        files = {n: (c["file"], {"generated": {}}, body)
                 for n, c in commands.items()}
        return _dsc.inspect(_spec_desc,
                            {"commands": commands, "types": types or {},
                             "families": {}}, files, modemap=_spec_modes)

    def _raises(fn):
        try:
            fn()
        except Exception:
            return True
        return False

    def _fired(found, needle, channel):
        lines = found.problems if channel == "problems" else found.reports
        return sum(1 for line in lines if needle in line)

    def _box(**kw):
        return {"Part_Box": {"file": "part/Part_Box.md", "doc": "x", **kw}}

    def _tune(**kw):
        return {"Part::Box": {"file": "part/Part_Box.md", **kw}}

    # Part_Box is claimed by fccli/verbs.py, so the two shape rules
    # decline for it on purpose. Part_Cylinder is the same shape of
    # command with nobody's hand on it, and is what those cases use.
    def _cyl(**kw):
        return {"Part_Cylinder": {"file": "part/Part_Cylinder.md",
                                  "doc": "x", **kw}}

    def _tune_cyl(**kw):
        return {"Part::Cylinder": {"file": "part/Part_Cylinder.md", **kw}}

    _good = _tune(steps=["Length", "Width", "Height"], strict=True)
    _good_cyl = _tune_cyl(steps=["Radius", "Height"], strict=True)
    _cases = [
        ("a correct command says nothing",
         _box(example="box 40 30 20", type={"of": "Part::Box"}), _good,
         "part/Part_Box.md", "problems", 0),
        ("type.steps naming no property of the type",
         _box(type={"of": "Part::Box"}),
         _tune(steps=["Lenght", "Width"], strict=True),
         "type.steps names 'Lenght'", "problems", 1),
        ("the same property spoken for twice",
         _box(type={"of": "Part::Box"}),
         _tune(steps=["Length"], hide=["Length"], strict=True),
         "type.hide names 'Length', which type.steps already", "problems", 1),
        ("two authored arguments under one gloss",
         _cyl(type={"of": "Part::Cylinder"}),
         _tune_cyl(steps=["Radius", "Height"], strict=True,
                   prompts={"Radius": "a length", "Height": "a length"}),
         "Radius and Height share one gloss", "problems", 1),
        ("an example naming no verb at all",
         _cyl(example="cylnider 12 40"), _good_cyl,
         "'cylnider', which is no verb", "problems", 1),
        ("an example naming somebody else's verb",
         _cyl(example="sphere 15"), _good_cyl,
         "does not reach this command", "problems", 1),
        ("  and the same on a command a hand-written verb owns, which "
         "this module cannot name",
         _box(example="sphere 15"), _good,
         "does not reach this command", "problems", 0),
        ("  which is a report there instead",
         _box(example="sphere 15"), _good,
         "does not reach this command", "reports", 1),
        ("an example written as a shell line",
         _box(example="fccli exec 'box 1 2 3'"), _good,
         "is a shell line", "problems", 1),
        ("  but not a path with a backslash in it, which is not a shell",
         _cyl(example="image_plane C:\\images\\plan.png 100 75"), _good_cyl,
         "is a shell line", "problems", 0),
        ("an example on two lines",
         _box(example="box 1 2 3\nbox 4 5 6"), _good,
         "spans more than one line", "problems", 1),
        ("an example passing more than the synopsis takes",
         _cyl(example="cylinder 12 40 5 5"), _good_cyl,
         "passes 4 arguments to a synopsis that takes 2", "reports", 1),
        ("a tuning line that names nothing and so does nothing",
         _box(), _tune(steps=["Length"], options=["Nope"], strict=True),
         "type.options names 'Nope'", "reports", 1),
        ("two generated arguments under one gloss",
         {"Part_Cone": {"file": "part/Part_Cone.md", "doc": "x"}}, {},
         "Radius1 and Radius2 share one gloss", "reports", 1),
        ("a positional command with no example",
         {"Arch_Axis": {"file": "arch/Arch_Axis.md", "doc": "x"}}, {},
         "a positional command with no example", "reports", 1),
        # ADR-200's two-part example, and A5's reading of it (GH #54). The
        # command half is what the verb rules judge; the setup half is
        # held to being a `select`, and to matching what the mode wants.
        ("a two-part example on a selection command says nothing",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box, Box001; part_cut"}}, {},
         "part/Part_Cut.md", "problems", 0),
        ("  and nothing on the reports either",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box, Box001; part_cut"}}, {},
         "(A5)", "reports", 0),
        ("a selection command whose example names no operands",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "part_cut"}}, {},
         "names no operands", "reports", 1),
        ("a positional command whose example selects operands first",
         {"Arch_Axis": {"file": "bim/Arch_Axis.md", "doc": "x",
                        "example": "select Box; axis"}}, {},
         "selects operands first", "reports", 1),
        ("  but a panel command may want either, so neither is remarked on",
         {"Part_Fillet": {"file": "part/Part_Fillet.md", "doc": "x",
                          "example": "part_fillet"}}, {},
         "(A5)", "reports", 0),
        ("a setup half that is not a select",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "pick Box, Box001; part_cut"}}, {},
         "only a select may stand before the semicolon", "problems", 1),
        ("a setup half with no command after it",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box, Box001;"}}, {},
         "has a setup half and no command after it", "problems", 1),
        ("a command half naming somebody else's verb",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box, Box001; sphere 15"}}, {},
         "does not reach this command", "problems", 1),
        ("a two-part example reaching its command through a family door",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "select Box; view front"}}, {},
         "std/Std_ViewFront.md", "problems", 0),
        ("  and one naming the wrong choice behind that door",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "select Box; view top"}}, {},
         "does not reach this command", "problems", 1),
        ("a shell line hiding in the command half",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box; part_cut | tee out"}}, {},
         "is a shell line", "problems", 1),
        ("a third half, which ADR-200 does not write",
         {"Part_Cut": {"file": "part/Part_Cut.md", "doc": "x",
                       "example": "select Box; part_cut; sphere 15"}}, {},
         "is a shell line", "problems", 1),
        ("an example on a command only a person can drive",
         {"Arch_AxisTools": {"file": "bim/Arch_AxisTools.md", "doc": "x",
                             "example": "axis_tools"}}, {},
         "an example on a manual-mode command", "reports", 1),
        ("the family door with the wrong choice behind it",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "view top"}}, {},
         "does not reach this command", "problems", 1),
        ("the family door with the right one",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "view front"}}, {},
         "std/Std_ViewFront.md", "problems", 0),
        ("a family where only some members carry an example",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "view front"}}, {},
         "family view: 1 of 41 members carries an example", "reports", 1),
        ("a family whose examples are typed two ways",
         {"Std_ViewFront": {"file": "std/Std_ViewFront.md", "doc": "x",
                            "example": "view front"},
          "Std_ViewTop": {"file": "std/Std_ViewTop.md", "doc": "x",
                          "example": "3_top"}}, {},
         "the examples are typed two ways", "reports", 1),
        ("a collapsed point built from a property that is not there",
         _box(type={"of": "Part::Box"}),
         _tune(steps=["Length"], point={"base": ["Nope"]}, strict=True),
         "type.point[base] collapses 'Nope'", "problems", 1),
        ("an example passing arguments to a verb with no synopsis",
         {"Draft_Arc": {"file": "draft/Draft_Arc.md", "doc": "x",
                        "example": "arc 0,0,0 15 0 90"}}, {},
         "has no synopsis of its own", "reports", 1),
        ("and one passing none, which is how a launcher is called",
         {"Arch_Axis": {"file": "arch/Arch_Axis.md", "doc": "x",
                        "example": "axis"}}, {},
         "has no synopsis of its own", "reports", 0),
        ("two tuned siblings disagreeing on argument order", {},
         {"Part::Cylinder": {"file": "a", "steps": ["Radius", "Height"]},
          "Part::Helix": {"file": "b", "steps": ["Pitch", "Height", "Radius"]}},
         "disagree about which comes first", "reports", 1),
    ]
    for _label, _commands, _types, _needle, _channel, _want in _cases:
        check("  " + _label,
              _fired(_spec(_commands, _types), _needle, _channel), _want)
    # The hand-authored tier. `box` is `corner length width height` in
    # fccli/verbs.py and `Length Width Height` in the generated one, and
    # fccli.verbs needs FreeCAD to import -- so the two shape rules must
    # decline for the commands those files claim rather than answer from
    # the wrong verb. Deleting the skip puts the false positive back.
    _claimed = _dsc.authored_commands()
    # 14 is a tripwire, not a constant: writing a hand-authored verb for
    # a fifteenth command fails this until somebody moves the number and
    # reads what the rules stopped seeing.
    check("  the hand-authored tier is found by name, and its verb with it",
          (len(_claimed), _claimed.get("Part_Box"), _claimed.get("Std_Save"),
           "Draft_Arc" in _claimed),
          (14, ("box", "fccli/verbs.py"), ("save", "fccli/shell.py"), False))
    check("  a source with no gui_command= raises rather than claiming none",
          _raises(lambda: _dsc.authored_commands(
              (os.path.join(os.path.dirname(__file__), "offscreen.py"),))),
          True)
    _blind = _spec(_box(example="box 0,0,0 40 30 20",
                        type={"of": "Part::Box"}), _good)
    check("  a command a hand-written verb owns is not measured against "
          "the generated one",
          (_fired(_blind, "passes 4 arguments", "reports"),
           _blind.records["Part_Box"]["checks"]["A2"],
           _blind.records["Part_Box"]["checks"]["A3"]),
          (0, "unread", "unread"))
    check("    and the record says why, naming the verb that owns it",
          ([n for n in _blind.records["Part_Box"]["notes"]
            if "`box` in fccli/verbs.py" in n] != [],
           _blind.records["Part_Box"].get("authored_verb")),
          (True, "box"))
    # One note per command, not one note mentioning one command: `notes`
    # is machine-read, and a record that talks about somebody else is a
    # record the campaign has to disbelieve.
    _other = _spec({"Draft_Circle": {"file": "draft/Draft_Circle.md",
                                     "doc": "x"}})
    check("    and it is that command's verb, not another's",
          ([n for n in _other.records["Draft_Circle"]["notes"]
            if "`circle`" in n and "box" not in n] != [],
           _other.records["Draft_Circle"].get("authored_verb")),
          (True, "circle"))
    # F5's half in this module: a registry that will not build takes the
    # whole hard-fail tier with it, so it cannot be a report.
    _old_build = _dsc.build_registry
    try:
        _dsc.build_registry = lambda descriptor, dictionary: None
        _unbuilt = _dsc.inspect(_spec_desc, {"commands": {}}, {})
    finally:
        _dsc.build_registry = _old_build
    check("  a registry that will not build is a problem, not a quiet report",
          (len(_unbuilt.problems), _unbuilt.reports), (1, []))
    # And F5's other half, in the lint: the catch around inspect() keeps a
    # traceback off the operator, and must not keep the failure off too.
    _old_inspect = _dsc.inspect
    try:
        def _boom(*a, **kw):
            raise RuntimeError("a shape descriptions.py did not expect")
        _dsc.inspect = _boom
        _n5, _p5 = _ld.lint(_cd.DEFAULT_TREE, _ld.DESCRIPTOR, _cd.DEFAULT_OUT)
    finally:
        _dsc.inspect = _old_inspect
    check("    and so is a description pass that raised",
          [p for p in _p5 if "did not run: RuntimeError" in p] != [], True)
    # A tuning fault is registry-independent, so it is still a problem
    # for a command whose verb this module cannot see -- and it has to
    # reach the record, which is where the campaign reads verdicts.
    _tuned_bad = _spec(_box(type={"of": "Part::Box"}),
                       _tune(steps=["Lenght"], strict=True))
    check("  a tuning fault reaches the record of the file that carries it",
          (_tuned_bad.records["Part_Box"]["checks"]["A2"],
           any("not a property" in n
               for n in _tuned_bad.records["Part_Box"]["notes"])),
          ("fail", True))
    _typed = _spec({}, {"Part::Helix": {"file": "part/_types.yaml",
                                        "options": ["Style"]}})
    check("    and a type with no command file is filed under its type",
          _typed.types.get("Part::Helix", {}).get("verdict"), "report")
    _typed_bad = _spec({}, {"Part::Helix": {"file": "part/_types.yaml",
                                            "steps": ["Lenght"]}})
    check("      with a problem filed as one, not softened to a report",
          (_typed_bad.types.get("Part::Helix", {}).get("verdict"),
           len(_typed_bad.problems)), ("fail", 1))

    # A1 and A4 are a person's reading; these three are the damage a
    # reader meets before the reading starts.
    check("  a summary left as a letter by the label strip",
          _fired(_spec(_box(summary="S the selected profiles.")),
                 "the label was stripped off", "reports"), 1)
    check("  and an article, which is a word",
          _fired(_spec(_box(summary="A link is an object that references "
                                    "another.")),
                 "the label was stripped off", "reports"), 0)
    check("  a body that only says the summary again",
          _fired(_spec(_box(summary="Compound tools."), body="Compound tools"),
                 "one line twice", "reports"), 1)
    check("  a body whose link never closes",
          _fired(_spec(_box(), body="[Part Boolean\n\nis a generic tool."),
                 "prints the bracket", "reports"), 1)
    check("  a body that is not there at all",
          _fired(_spec(_box(), body=""), "there is no body", "reports"), 1)
    # The rules run at all: a report the whole tree cannot produce means
    # something silently declined to build the registry.
    _live = _spec({"Part_Box": {"file": "part/Part_Box.md", "doc": "x"}})
    check("  and the registry they read is really built",
          bool(_live.records["Part_Box"]["synopsis"]), True)


    print("\n5dl. every grammar rule fails when its fault is put back")
    # GH #49, the grammar spec (D1, D3, D4, D5). Same shape as 5al: each
    # case is one fault, reintroduced, and the rule it must fire. The
    # problem tier is three classes that are all empty on this tree, so
    # each of those needs its fault built rather than found -- which is
    # the point of building it.
    import interaction as _ixn
    import copy as _copy_module
    import re as _re
    from fccli.grammar import Step as _Step, TEXT as _TEXT, CHOICE as _CHOICE

    _tree = _cd.compile_tree(_cd.DEFAULT_TREE)

    def _grammar(commands=None, registry=None, dictionary=None,
                 descriptor=None):
        """The grammar rules over a dictionary, real or built for a case.

        A case that wants one fault names the four commands it needs; a
        case that wants the tree passes the compiled one. The difference
        matters more here than it does for the description rules: the
        family choices come out of the tree's own `choice:` and `also:`
        lines, and `iso` -- GH #55 -- is one of those.
        """
        if dictionary is None:
            dictionary = {"commands": commands or {}, "types": {},
                          "families": {}}
        commands = dictionary["commands"]
        files = {n: (c["file"], {"generated": {}}, "")
                 for n, c in commands.items() if c.get("file")}
        return _ixn.inspect(descriptor or _spec_desc, dictionary, files,
                            registry=registry)

    # The tree as it stands, so a case can put one fault into a real
    # registry rather than a hand-built one that agrees with the rule.
    _real = _dsc.build_registry(_spec_desc, _tree)

    def _copy_registry():
        from fccli.grammar import Registry as _R
        import copy as _copy
        clone = _R()
        for _n in _real.names():
            clone.add(_copy.deepcopy(_real.get(_n)))
        clone.reindex()
        return clone

    # --- D1: a choice no input selects.
    _live_d1 = _grammar(dictionary=_tree)
    check("  no choice on the tree is unreachable, exact winning over prefix",
          _fired(_live_d1, "no input selects", "reports"), 0)
    # The fault, put back. D1 asks `grammar.match_choice` rather than
    # keeping a copy, so stripping the exact tier off the matcher -- the
    # engine GH #55 was filed against -- brings the whole class back, and
    # the two lines below are the ones this suite used to pin.
    import fccli.grammar as _gmod
    _old_match = _gmod.match_choice
    try:
        _gmod.match_choice = lambda choices, text: [
            c for c in choices if c.lower().startswith(text.lower())]
        _prefix_only = _grammar(dictionary=_tree)
    finally:
        _gmod.match_choice = _old_match
    check("    and the prefix-only matcher put back brings 21 of them back",
          (_fired(_prefix_only, "the family door `view` lists 'iso', and "
                                "typing it also selects 'isometric'",
                  "reports"),
           _fired(_prefix_only, "`draw_view_annotation <TextStyle>` lists "
                                "'Bold'", "reports"),
           _fired(_prefix_only, "no input selects", "reports")),
          (1, 1, 21))
    check("    the sibling that shadows is never the one reported",
          (_fired(_live_d1, "lists 'isometric'", "reports"),
           _fired(_prefix_only, "lists 'isometric'", "reports")), (0, 0))
    check("  two commands under one choice, which is silent where it happens",
          _fired(_live_d1, "`save as` is two commands", "reports"), 1)
    # The problem half of D1: the tree authored the spelling. Three
    # commands so the family reaches MIN_MEMBERS, two of them asking for
    # the same choice -- families() writes one over the other and the
    # loser's file still documents a line that runs somebody else.
    _clash = {"Part_Box": {"file": "part/Part_Box.md", "doc": "x",
                           "family": "make", "choice": "thing"},
              "Part_Cylinder": {"file": "part/Part_Cylinder.md", "doc": "x",
                                "family": "make", "choice": "thing"},
              "Part_Cone": {"file": "part/Part_Cone.md", "doc": "x",
                            "family": "make", "choice": "cone"},
              "Part_Sphere": {"file": "part/Part_Sphere.md", "doc": "x",
                              "family": "make", "choice": "ball"}}
    check("  an authored choice two files ask for, which is a problem",
          _fired(_grammar(_clash), "the tree authored this spelling",
                 "problems"), 1)
    _clean = dict(_clash)
    _clean["Part_Cylinder"] = dict(_clean["Part_Cylinder"], choice="tube")
    check("    and the same four files with distinct choices say nothing",
          _fired(_grammar(_clean), "the tree authored this spelling",
                 "problems"), 0)

    # --- D3: a step with no pool to offer.
    _live_d3 = _grammar(dictionary=_tree)
    check("  a choice step the harvest read no values off",
          _fired(_live_d3, "`fem_post_pipeline <Frame>` takes one of a "
                           "closed set and has none to take", "reports"), 1)
    check("  the inline option that moves what position means",
          _fired(_live_d3, "verbs take an inline option", "reports"), 1)
    # The problem half: a pool name from_source does not know. Both tiers
    # get the fault, because they are read two different ways -- the
    # hand-written one out of the source text, the generated one off the
    # built step.
    _bad_src = _ixn.declared_sources
    try:
        _ixn.declared_sources = lambda *a, **k: {"objekts": ["fccli/shell.py"]}
        _typo = _grammar()
    finally:
        _ixn.declared_sources = _bad_src
    check("  a hand-written step completing from a pool that is not one",
          _fired(_typo, "completes from 'objekts', which from_source does "
                        "not know", "problems"), 1)
    check("    and the sources really declared, which are all known",
          (sorted(_ixn.declared_sources()) != [],
           sorted(set(_ixn.declared_sources()) - _ixn.known_sources())),
          (True, []))
    _reg_typo = _copy_registry()
    _reg_typo.get("part_cut").steps.append(
        _Step("what", _TEXT, "What", completes="objekts"))
    check("  a built step completing from a pool that is not one",
          _fired(_grammar(registry=_reg_typo),
                 "`part_cut <what>` completes from 'objekts'", "problems"), 1)
    _reg_ok = _copy_registry()
    _reg_ok.get("part_cut").steps.append(
        _Step("what", _TEXT, "What", completes="objects"))
    check("    and the same step spelled right says nothing",
          _fired(_grammar(registry=_reg_ok), "completes from", "problems"), 0)
    check("  a from_source with no pool names left in it raises",
          _raises(lambda: _ixn.known_sources(
              os.path.join(os.path.dirname(__file__), "offscreen.py"))),
          True)

    # --- D4: the word a verb answers to.
    _live_d4 = _grammar(dictionary=_tree)
    check("  a generic word answering for one workbench of several",
          _fired(_live_d4, "naming: 'cut' is the meaningful word of",
                 "reports"), 1)
    check("  a verb no meaningful word reaches",
          _fired(_live_d4, "verbs are not reachable by their meaningful "
                           "word", "reports"), 1)
    check("  a prefix that names no workbench anyone switches to (GH #21)",
          _fired(_live_d4, "commands are prefixed Arch_ and ship in "
                           "BIMWorkbench", "reports"), 1)
    check("    and a prefix that names its own workbench, which is silent",
          _fired(_live_d4, "prefixed Part_ and ship in PartWorkbench",
                 "reports"), 0)
    # A family door winning a generic word is the design working, and a
    # hand-written verb winning one is a verb this module is not looking
    # at. Neither is a hijack, and both are shapes that fired before the
    # two guards went in.
    check("  the family door winning its own word, which is not a hijack",
          _fired(_live_d4, "naming: 'view' is the meaningful word of",
                 "reports"), 0)
    check("  a word won by a verb somebody wrote, which nobody here meets",
          (_fired(_live_d4, "naming: 'box' is the meaningful word of",
                  "reports"),
           _live_d4.words["box"].get("blind")), (0, True))
    check("  a verb reachable through its family door, which is reachable",
          (_live_d4.records["Std_ViewFront"]["checks"]["D4"],
           any("`view front` does" in n
               for n in _live_d4.records["Std_ViewFront"]["notes"])),
          ("pass", True))
    # The problem half of D4: the file asks for a name and something else
    # answers to it. Rule 4 of this lint checks the tree's names against
    # each other; nothing checked them against the verbs that get built.
    check("  a file asking for a name a family door already owns",
          _fired(_grammar({"Part_Box": {"file": "part/Part_Box.md",
                                        "doc": "x", "aliases": ["view"]}}),
                 "asks for the name 'view' and it runs `view`", "problems"), 1)
    check("    and one asking for a name of its own, which it gets",
          _fired(_grammar({"Part_Box": {"file": "part/Part_Box.md",
                                        "doc": "x", "aliases": ["boxy"]}}),
                 "asks for the name", "problems"), 0)
    _gone = _copy_registry()
    _gone.remove("box")
    check("  a file asking for a name no verb answers to",
          _fired(_grammar({"Part_Box": {"file": "part/Part_Box.md",
                                        "doc": "x", "verb": "box"}},
                          registry=_gone),
                 "asks for the name 'box' and no verb answers", "problems"), 1)
    _nameless = os.path.join(tempfile.mkdtemp(), "nothing.py")
    with open(_nameless, "w") as _fh:
        _fh.write("REGISTRY = []\n")
    check("  a source with no name= raises rather than claiming no verbs",
          _raises(lambda: _ixn.authored_verbs((_nameless,))), True)
    check("    and the real sources, which have thirty-four between them",
          len(_ixn.authored_verbs()) >= 30, True)

    # --- D5: the unit a quantity echoes in.
    _live_d5 = _grammar(dictionary=_tree)
    check("  a dimensionless property carrying the factory's millimetres",
          _fired(_live_d5, "steps over App::PropertyFloatConstraint echo in "
                           "mm", "reports"), 1)
    check("  a Quantity property, whose unit is the runtime tier's to read",
          _fired(_live_d5, "carries its unit on the instance rather than the "
                           "type", "reports"), 1)
    _reg_unit = _copy_registry()
    for _s in _reg_unit.get("cylinder").steps:
        if _s.id == "Radius":
            _s.unit = "furlong"
    check("  a unit the harvest cannot produce",
          _fired(_grammar(registry=_reg_unit),
                 "'furlong', which the harvest cannot produce",
                 "problems"), 1)
    _reg_swap = _copy_registry()
    for _s in _reg_swap.get("cylinder").steps:
        if _s.id == "Radius":
            _s.unit = "deg"
    check("  a unit the factory did not carry through from the descriptor",
          _fired(_grammar(registry=_reg_swap),
                 "echoes in 'deg' and the descriptor harvested 'mm'",
                 "problems"), 1)
    check("    and the unit the factory did carry through, which is silent",
          _fired(_live_d5, "did not carry the unit through", "problems"), 0)

    # --- what this lint is not looking at, said out loud.
    _blind_g = _grammar({"Part_Box": {"file": "part/Part_Box.md", "doc": "x"},
                         "Part_Cylinder": {"file": "part/Part_Cylinder.md",
                                           "doc": "x"}})
    check("  a command a hand-written verb owns has no rule answering for it",
          ([_blind_g.records["Part_Box"]["checks"][r]
            for r in ("D1", "D3", "D4", "D5")],
           _blind_g.records["Part_Box"].get("authored_verb")),
          (["unread"] * 4, "box"))
    check("    and a command beside it, which nobody wrote, is answered",
          ([_blind_g.records["Part_Cylinder"]["checks"][r]
            for r in ("D1", "D3", "D4", "D5")],
           _blind_g.records["Part_Cylinder"].get("authored_verb")),
          (["n/a", "n/a", "pass", "pass"], None))
    # A report filed against a blind command's file must not be read as
    # that rule having answered. Without the guard, the D4 line about the
    # generated `box` turned Part_Box's unread into a report.
    # Deleting the _note override turns each of these into an answer the
    # rule never gave: a line filed against a blind command's file is
    # about the generated verb standing in, and `box` is not that verb.
    _blind_g.report("part/Part_Box.md", "something about the generated verb",
                    "D4")
    _blind_g.problem("part/Part_Box.md", "something worse about it", "D5")
    check("    and a later line about the stand-in leaves unread alone",
          ([_blind_g.records["Part_Box"]["checks"][r] for r in ("D4", "D5")],
           [n.split(":")[0] for n in _blind_g.records["Part_Box"]["notes"][-2:]]),
          (["unread", "unread"], ["D4", "D5"]))
    check("      though the problem line still fails the lint",
          [p for p in _blind_g.problems if "something worse" in p] != [], True)
    _seen_g = _grammar({"Part_Cylinder": {"file": "part/Part_Cylinder.md",
                                          "doc": "x"}})
    _seen_g.report("part/Part_Cylinder.md", "something about its verb", "D4")
    check("      and a command nobody wrote takes the verdict as normal",
          _seen_g.records["Part_Cylinder"]["checks"]["D4"], "report")
    # The two rules that stop at a blind command, each with the fault put
    # into a verb a hand-written one owns and then into one beside it. Both
    # guards were silent branches until this pair went in: nothing on this
    # tree happens to be blind and faulty at once.
    _two = {"Part_Box": {"file": "part/Part_Box.md", "doc": "x"},
            "Part_Cylinder": {"file": "part/Part_Cylinder.md", "doc": "x"}}
    _blind_pool = _copy_registry()
    _blind_pool.get("box").steps.append(_Step("Mode", _CHOICE, "Mode"))
    _seen_pool = _copy_registry()
    _seen_pool.get("cylinder").steps.append(_Step("Mode", _CHOICE, "Mode"))
    check("  a choice step with no pool, on a command somebody wrote a verb for",
          (_fired(_grammar(_two, registry=_blind_pool),
                  "`box <Mode>` takes one of a closed set", "reports"),
           _fired(_grammar(_two, registry=_seen_pool),
                  "`cylinder <Mode>` takes one of a closed set", "reports")),
          (0, 1))
    _dim = _copy_module.deepcopy(_spec_desc)
    for _tid in ("Part::Box", "Part::Cylinder"):
        for _p in _dim["types"][_tid]["params"]:
            if _p["name"] == "Height":
                _p.pop("unit", None)
                _p["property_type"] = "App::PropertyFloat"
    _dim_found = _grammar(_two, descriptor=_dim)
    check("  a dimensionless step in mm, on one written for and one not",
          ([n for n in _dim_found.records["Part_Box"]["notes"]
            if "App::PropertyFloat" in n],
           [n for n in _dim_found.records["Part_Cylinder"]["notes"]
            if "App::PropertyFloat" in n] != []),
          ([], True))
    # --- the report lists stay each group's own (found in review of #66).
    # `reports = found.reports` followed by `reports += grammar.reports`
    # bound the A group's list and extended it in place, so every grammar
    # line landed inside descriptions.Findings.reports -- and --report runs
    # after that, writing totals.reports = 559 into the artifact where the
    # A group's own count is 435.
    _fa, _fb = _dsc.Findings(), _ixn.Findings()
    _fa.reports.extend(["A-one", "A-two"])
    _fb.reports.append("D-one")
    _both = _ld.combined_reports(_fa, _fb)
    check("  combining the two groups' reports leaves each list alone",
          (_both, _fa.reports, _fb.reports),
          (["A-one", "A-two", "D-one"], ["A-one", "A-two"], ["D-one"]))
    check("    and a strict group contributes nothing, having been promoted",
          (_ld.combined_reports(_fa, _fb, strict_descriptions=True),
           _ld.combined_reports(_fa, _fb, strict_grammar=True),
           _fa.reports),
          (["D-one"], ["A-one", "A-two"], ["A-one", "A-two"]))

    # --- DIMENSIONLESS, pinned member by member. Three of the six could be
    # dropped with the suite green, which is 87 of the 253 steps the rule
    # exists to find. App::PropertyPercent has no instances on this tree, so
    # a census cannot pin it; that is stated rather than left to look pinned.
    # 212, down from 253: the GH #69 round hides FuzzyTolerance on
    # thirty-nine more types -- every PartDesign primitive, every base
    # feature type, and the patterns -- plus PartDesign::Helix's own
    # Tolerance and LinearPattern's Occurrences2. The forty tolerances
    # are the FloatConstraint (87 -> 47); Occurrences2 the
    # IntegerConstraint (19 -> 18). The rule finds fewer steps because
    # fewer unitless properties are steps, which is the point of it.
    #
    # 141, down from 212: the GH #78 round gives an integer step no unit
    # at all, so the two integer types leave the census cured rather than
    # counted -- 53 + 18. They stay in DIMENSIONLESS, which is the rule's
    # reading of the property and not of the step, so a factory that
    # defaulted them back to millimetres would be counted again. What is
    # left is the float half, and it is #47's D5 to finish.
    _census = {}
    for _line in _live_d5.reports:
        _m = _re.match(r"units: (\d+) steps over (\S+) echo in mm", _line)
        if _m:
            _census[_m.group(2)] = int(_m.group(1))
    check("  every dimensionless property type is counted, by name",
          (_census, sum(_census.values())),
          ({"App::PropertyFloat": 80, "App::PropertyFloatConstraint": 47,
            "App::PropertyPrecision": 14}, 141))
    check("    and the one with no instances is in the set, uncounted",
          ("App::PropertyPercent" in _ixn.DIMENSIONLESS,
           "App::PropertyPercent" in _census), (True, False))
    check("    the integer types are in the set and cured, not counted",
          ({_p for _p in _ixn.DIMENSIONLESS if "Integer" in _p} <=
           set(_ixn.DIMENSIONLESS),
           [_p for _p in _census if "Integer" in _p]), (True, []))
    check("    and no step echoes in a unit parse_quantity cannot read back",
          [_l for _l in _live_d5.problems if "which the harvest cannot "
           "produce" in _l], [])

    # --- the blind tier reads aliases as well as names. `register_all`
    # refuses a generated verb on a taken alias exactly as it does on a
    # taken name, and reading only `name=` shipped a D4 line about `help`
    # as though Std_OnlineHelp were reachable by it.
    _named = _ixn.authored_verbs()
    check("  an alias of a hand-written verb is a name nobody else gets",
          {_k: _named.get(_k) for _k in ("exit", "help", "sel")},
          {"exit": ("quit", "fccli/shell.py"),
           "help": ("man", "fccli/shell.py"),
           "sel": ("select", "fccli/shell.py")})
    check("    and the record says which verb it is an alias of",
          (_fired(_live_d4, "the name `help` is an alias of the hand-written "
                            "verb `man`", "reports"),
           _fired(_live_d4, "the name `box` is the hand-written verb `box`",
                  "reports")), (1, 1))
    check("    so the word is no longer spoken of as a way in",
          _fired(_live_d4, "naming: 'help' is the meaningful word of",
                 "reports"), 0)
    _half = os.path.join(tempfile.mkdtemp(), "half.py")
    with open(_half, "w") as _fh:
        _fh.write('Verb(name="only", steps=[])\n')
    check("  a source with names and no aliases raises, not half an answer",
          _raises(lambda: _ixn.authored_verbs((_half,))), True)

    # --- D1 calls the engine's matcher rather than restating it. A copy of
    # the comparison could be made case-sensitive with the suite green and
    # the tree's D1 output byte-identical, because every shadowed pair the
    # tree carries agrees in case. This is the pair that does not.
    #
    # Calling it is also what re-aimed the rule when the matcher took an
    # exact value first (GH #55). The class it was written for -- a value
    # a longer value begins -- is settled at the matcher and gone from the
    # report; the class left is two spellings of one word in a door, which
    # is a case-insensitive question, so the case-sensitive mutant still
    # dies here.
    from fccli.grammar import match_choice as _match
    check("  the engine's matcher takes an exact value before a prefix",
          (_match(["iso", "isometric"], "iso"),
           _match(["Iso", "isometric"], "iso"),
           _match(["iso", "isometric"], "isom"),
           _match(["front", "top"], "FRONT"),
           _match(["front", "top"], "zzz")),
          (["iso"], ["Iso"], ["isometric"], ["front"], []))
    check("    and two spellings of one word are exact together, so neither wins",
          _match(["Iso", "iso", "front"], "ISO"), ["Iso", "iso"])
    _mixed = _copy_registry()
    _mixed.get("view").steps[0].choices = ["Iso", "iso", "front"]
    check("    so a door carrying both spellings is one D1 finds",
          (_fired(_grammar(dictionary=_tree, registry=_mixed),
                  "lists 'Iso', and typing it also selects 'iso'", "reports"),
           _fired(_grammar(dictionary=_tree, registry=_mixed),
                  "lists 'iso', and typing it also selects 'Iso'", "reports")),
          (1, 1))
    _unshadowed = _copy_registry()
    _unshadowed.get("view").steps[0].choices = ["iso", "isometric", "front"]
    check("    and one a longer value begins is not, the matcher having settled it",
          _fired(_grammar(dictionary=_tree, registry=_unshadowed),
                 "no input selects", "reports"), 0)

    # --- the choice collision is above the line, with the four the tree
    # carries grandfathered by name. The criterion is the consequence: a
    # collision runs the wrong command with no refusal and no message, and
    # that is true however the spelling arose. Demoting the class would
    # have left the next one joining a report nobody diffs.
    check("  a known collision is a report, and says it is grandfathered",
          (_fired(_live_d1, "`save as` is two commands", "reports"),
           _fired(_live_d1, "`save as` is two commands", "problems")), (1, 0))
    _new = _copy_module.deepcopy(_spec_desc)
    for _cmd, _label in (("Aaa_ZapThing", "Zap Thing"),
                         ("Bbb_ZapThing", "Zap Thing Too"),
                         ("Ccc_ZapOther", "Zap Other"),
                         ("Ddd_ZapMore", "Zap More")):
        _new["commands"][_cmd] = {"name": _cmd, "label": _label,
                                  "tooltip": _label, "workbench": None}
    check("  a collision the list does not name is a problem",
          _fired(_grammar(dictionary=_tree, descriptor=_new),
                 "`zap thing` is two commands", "problems"), 1)
    check("    and the four it does name stay reports beside it",
          _fired(_grammar(dictionary=_tree, descriptor=_new),
                 "is two commands", "problems"), 1)
    _stale = dict(_ixn.KNOWN_COLLISIONS, **{"nosuch.choice": "nothing (GH #0)"})
    _old_known = _ixn.KNOWN_COLLISIONS
    try:
        _ixn.KNOWN_COLLISIONS = _stale
        _pruned = _grammar(dictionary=_tree)
    finally:
        _ixn.KNOWN_COLLISIONS = _old_known
    check("  an entry the tree no longer collides on asks to be pruned",
          _fired(_pruned, "`nosuch choice` is grandfathered", "reports"), 1)

    check("  a generated verb standing on a hand-written name is said so",
          (_fired(_live_d4, "the name `select` is the hand-written verb "
                            "`select`", "reports"),
           _fired(_live_d4, "the family door `select` and its 17 choices do "
                            "not exist live", "reports")), (1, 1))
    # F5 in this module, both halves: a registry that will not build takes
    # every rule with it, and the lint's catch must not swallow a raise.
    _old_build_g = _dsc.build_registry
    try:
        _dsc.build_registry = lambda descriptor, dictionary: None
        _unbuilt_g = _ixn.inspect(_spec_desc, {"commands": {}}, {})
    finally:
        _dsc.build_registry = _old_build_g
    check("  a registry that will not build is a problem, not a quiet report",
          (len(_unbuilt_g.problems), _unbuilt_g.reports), (1, []))
    _old_ixn = _ixn.inspect
    try:
        def _boom_g(*a, **kw):
            raise RuntimeError("a shape interaction.py did not expect")
        _ixn.inspect = _boom_g
        _n6, _p6 = _ld.lint(_cd.DEFAULT_TREE, _ld.DESCRIPTOR, _cd.DEFAULT_OUT)
    finally:
        _ixn.inspect = _old_ixn
    check("    and a grammar pass that raised is a problem too",
          [p for p in _p6 if "grammar rules did not run: RuntimeError" in p]
          != [], True)
    # And the whole point: the tree as it stands carries no D-group
    # problem, so this lint joins make check without breaking it.
    check("  the tree in the repository has no grammar problem in it",
          _live_d1.problems, [])

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
    # 289 = the 278 counted after the GH #54 promotion, plus the 11 files
    # the GH #69 round gave a `type` block to that carried no authored
    # field before. Three of its fourteen already carried an example.
    check("  and register_all counts the authored files", _wc.get("authored"), 289)
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
    # A launcher with an authored summary shows it over FreeCAD's tooltip.
    _pf = _with.by_gui_command("Part_Fuse")
    check("  an authored summary is the launcher's one-liner",
          _pf.doc, _dict["commands"]["Part_Fuse"]["summary"])
    check("    and it is not the tooltip",
          _pf.doc == _cmds["Part_Fuse"]["tooltip"], False)
    # ADR-501: an authored example reaches the dictionary, and the verify
    # harness reads the state after a run to say what happened.
    check("  an authored example compiles into the dictionary",
          _dict["commands"]["Part_Box"].get("example"), "box 0,0,0 40 30 20")
    import verify as _verify
    check("  a clean positional run with a clean document is ok",
          _verify.classify(0, "idle", False, []), "ok")
    check("    a clean run that left an invalid object is invalid",
          _verify.classify(0, "idle", False, ["Fillet"]), "invalid")
    check("    an open task panel is panel, even mid-collection",
          (_verify.classify(0, "idle", True, []),
           _verify.classify(1, "collecting", True, [])),
          ("panel", "panel"))
    check("    a command still collecting is incomplete",
          _verify.classify(1, "collecting", False, []), "incomplete")
    check("    a non-zero exit with the engine idle is broken",
          _verify.classify(1, "idle", False, []), "broken")
    # GH #57 turned this reading round. The engine reports an object
    # FreeCAD rejected as an error, so a non-zero exit is what an invalid
    # run looks like from out here; reading the code first would file all
    # fourteen named instances as `broken`, which does not name the object.
    check("    an invalid object outranks the exit code it caused",
          _verify.classify(1, "idle", False, ["Fillet"]), "invalid")
    _rejected_line = ("error: pad: FreeCAD computed Pad and marked it "
                      "invalid -- the command ran, the result is not usable")
    check("    and a run that only raised keeps its own message",
          (_verify.rejection_only(_rejected_line),
           _verify.rejection_only("error: pad failed: boom"),
           _verify.rejection_only("error: pad failed: boom\n"
                                  + _rejected_line),
           _verify.rejection_only("")),
          (True, False, False, False))
    # And `verify_one` has to ask it. The function above is right on its
    # own, and forcing the call site to `extra = err` left the whole suite
    # green -- so nothing said whether a run that raised as well as
    # leaving something invalid kept what it said, or whether a clean
    # rejection had its own message read back to it in the ledger.
    _vsnaps = []
    _vreplies = {}

    def _vsnapshot():
        return _vsnaps.pop(0)

    def _vfccli(*args, **kw):
        return _vreplies.get(args[:2], (0, "", ""))

    def _vrun(err):
        _vsnaps[:] = [{"documents": [{"active": True, "invalid": []}]},
                      {"documents": [{"active": True, "invalid": ["Pad"]}],
                       "engine": "idle"}]
        _vreplies.clear()
        _vreplies[("exec", "pad 10")] = (1, "", err)
        return _verify.verify_one("pad 10")

    _vold_f, _vold_s = _verify.fccli, _verify._snapshot
    try:
        _verify.fccli, _verify._snapshot = _vfccli, _vsnapshot
        check("  an invalid run reports the object it left, by name",
              _vrun(_rejected_line), ("invalid", "Pad"))
        check("    and one that raised as well carries what it said",
              _vrun("error: pad failed: boom\n" + _rejected_line),
              ("invalid", "Pad; error: pad failed: boom\n"
               + _rejected_line))
    finally:
        _verify.fccli, _verify._snapshot = _vold_f, _vold_s
    check("    a held-elsewhere floor code is busy",
          _verify.classify(75, "idle", False, []), "busy")
    check("    busy outranks a panel someone else left open",
          _verify.classify(75, "idle", True, []), "busy")
    # A sweep survives its own targets: known and recorded hazards are
    # planned out, --force plans them back in, --start-at resumes.
    check("  a known hazard is planned out of a sweep",
          _verify.plan({"Std_ToggleToolBarLock": "lock_toolbars",
                        "Part_Box": "box 1 1 1"}, {}),
          ({"Part_Box": "box 1 1 1"},
           {"Std_ToggleToolBarLock":
            _verify.KNOWN_HAZARDS["Std_ToggleToolBarLock"]}))
    check("    so is one an earlier sweep recorded",
          _verify.plan({"Mod_X": "x"},
                       {"Mod_X": {"result": "hazard",
                                  "detail": "killed the FreeCAD instance"}}),
          ({}, {"Mod_X": "killed the FreeCAD instance"}))
    check("    --force plans it back in",
          _verify.plan({"Mod_X": "x"},
                       {"Mod_X": {"result": "hazard"}}, force=True),
          ({"Mod_X": "x"}, {}))
    check("    --start-at drops everything before it",
          _verify.plan({"A_One": "a", "B_Two": "b"}, {}, start_at="B")[0],
          {"B_Two": "b"})
    # GH #62: FreeCAD never holds a --log file; a bounded copier does. The
    # cap holds however much the instance spams, and the pipe is drained
    # to the end so the writer never blocks.
    import importlib.machinery as _glc_machinery
    import importlib.util as _glc_util
    _glc_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _glc_loader = _glc_machinery.SourceFileLoader(
        "_fccli_bin", os.path.join(_glc_repo, "bin", "fccli"))
    _glc_spec = _glc_util.spec_from_loader("_fccli_bin", _glc_loader)
    _glc_bin = _glc_util.module_from_spec(_glc_spec)
    _glc_spec.loader.exec_module(_glc_bin)
    with tempfile.TemporaryDirectory() as _glc_dir:
        _glc_spam = os.path.join(_glc_dir, "spam.log")
        # Cap above the 64K read chunk, so the accumulation across chunks
        # is load-bearing -- a copier that never adds up passes a
        # single-chunk cap and is GH #62 restored (PR #63 review, 5).
        _sh.run([sys.executable, "-c", _glc_bin.LOG_COPIER, _glc_spam,
                 str(256 * 1024)],
                input=b"x" * (4 * 1024 * 1024), timeout=60)
        check("  the --log copier stops writing at the cap",
              os.path.getsize(_glc_spam) < 300 * 1024, True)
        # The cap is the file's, not the run's: a second start appends
        # nothing to a file already at it.
        _sh.run([sys.executable, "-c", _glc_bin.LOG_COPIER, _glc_spam,
                 str(256 * 1024)],
                input=b"x" * 65536, timeout=60)
        check("    and holds across starts on the same file",
              os.path.getsize(_glc_spam) < 300 * 1024, True)
        # The writer must never see EPIPE. subprocess.run(input=...)
        # swallows BrokenPipeError, so drive the writer by hand: a copier
        # that stops reading at the cap breaks this pipe -- for FreeCAD
        # that is a SIGPIPE.
        _glc_drain = os.path.join(_glc_dir, "drain.log")
        _glc_proc = _sh.Popen(
            [sys.executable, "-c", _glc_bin.LOG_COPIER, _glc_drain, "4096"],
            stdin=_sh.PIPE)
        _glc_err = None
        try:
            for _ in range(64):
                _glc_proc.stdin.write(b"y" * 65536)
                _glc_proc.stdin.flush()
            _glc_proc.stdin.close()     # the flush that can also EPIPE
        except OSError as _glc_exc:
            _glc_err = _glc_exc
        _glc_proc.wait(timeout=30)
        check("    and never breaks the pipe under FreeCAD", _glc_err, None)
        # A file error stops the writing, never the reading.
        _glc_bad = os.path.join(_glc_dir, "nodir", "x.log")
        _glc_proc2 = _sh.Popen(
            [sys.executable, "-c", _glc_bin.LOG_COPIER, _glc_bad, "4096"],
            stdin=_sh.PIPE)
        _glc_err2 = None
        try:
            for _ in range(8):
                _glc_proc2.stdin.write(b"z" * 65536)
                _glc_proc2.stdin.flush()
            _glc_proc2.stdin.close()
        except OSError as _glc_exc:
            _glc_err2 = _glc_exc
        check("    an unopenable file drains rather than dies",
              (_glc_proc2.wait(timeout=30), _glc_err2), (0, None))
        # A write error mid-run, not just at open: /dev/full opens fine
        # and fails the first write with ENOSPC.
        if os.path.exists("/dev/full"):
            _glc_proc3 = _sh.Popen(
                [sys.executable, "-c", _glc_bin.LOG_COPIER, "/dev/full", "0"],
                stdin=_sh.PIPE)
            _glc_err3 = None
            try:
                for _ in range(8):
                    _glc_proc3.stdin.write(b"w" * 65536)
                    _glc_proc3.stdin.flush()
                _glc_proc3.stdin.close()
            except OSError as _glc_exc:
                _glc_err3 = _glc_exc
            check("    a write error mid-run drains rather than dies",
                  (_glc_proc3.wait(timeout=30), _glc_err3), (0, None))
        _glc_small = os.path.join(_glc_dir, "small.log")
        _sh.run([sys.executable, "-c", _glc_bin.LOG_COPIER, _glc_small, "4096"],
                input=b"hello\n", timeout=60)
        check("    under the cap, everything is kept",
              open(_glc_small, "rb").read(), b"hello\n")
    # sweep() itself, on stubs (PR #63 review, findings 1/6/7/9): a
    # command that wedges the instance -- process alive, server silent --
    # is a recorded hazard, the sweep restarts and continues.
    _sw_events = []
    _sw_health = iter([False, True])
    _sw_restarts = []
    _sw_tally, _sw_fin, _sw_n = _verify.sweep(
        {"A_A": "a", "B_B": "b"},
        lambda cid, ex, res, det, extra=None: _sw_events.append((cid, res, det)),
        run_one=lambda cid, e: ("incomplete", ""),
        alive=lambda: True,
        healthy=lambda: next(_sw_health),
        restart=lambda: _sw_restarts.append(1) or True)
    check("  a wedge is a recorded hazard; the sweep restarts and continues",
          ([(c, r) for c, r, _ in _sw_events], _sw_n, _sw_fin),
          ([("A_A", "hazard"), ("B_B", "incomplete")], 1, True))
    check("    with the wedge named",
          _sw_events[0][2], "left the instance unresponsive")

    def _sw_boom(cid, example):
        raise _sh.TimeoutExpired("fccli", 60)
    _sw_events2 = []
    _sw_tally2, _sw_fin2, _sw_n2 = _verify.sweep(
        {"C_C": "c"},
        lambda cid, ex, res, det, extra=None: _sw_events2.append((cid, res, det)),
        run_one=_sw_boom, alive=lambda: True, healthy=lambda: True,
        restart=lambda: True)
    check("    a client timeout is recorded, not raised",
          (_sw_events2, _sw_fin2),
          ([("C_C", "hazard", "client timed out; instance wedged")], True))
    _sw_events3 = []
    _sw_tally3, _sw_fin3, _sw_n3 = _verify.sweep(
        {"D_D": "d", "E_E": "e"},
        lambda cid, ex, res, det, extra=None: _sw_events3.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: False, healthy=lambda: False,
        restart=lambda: False)
    check("    a failed restart stops the sweep, the hazard recorded",
          (_sw_events3, _sw_fin3),
          ([("D_D", "hazard", "killed the FreeCAD instance")], False))

    def _sw_slow(*a):
        raise _sh.TimeoutExpired("fccli", 60)
    _sw_events4 = []
    _sw_tally4, _sw_fin4, _sw_n4 = _verify.sweep(
        {"F_F": "f"},
        lambda cid, ex, res, det, extra=None: _sw_events4.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: True, healthy=_sw_slow, restart=lambda: True)
    check("    a health probe that itself times out is the same hazard",
          (_sw_events4, _sw_fin4),
          ([("F_F", "hazard", "left the instance unresponsive")], True))
    # _healthy is the server answering, not the process living -- the
    # wedged case is exactly a live process whose server is silent.
    _sw_old_snap, _sw_old_run = _verify._snapshot, _verify.running
    try:
        _verify.running = lambda: True
        _verify._snapshot = lambda: {}
        _sw_h1 = _verify._healthy()
        _verify._snapshot = lambda: {"engine": "idle"}
        _sw_h2 = _verify._healthy()
    finally:
        _verify._snapshot, _verify.running = _sw_old_snap, _sw_old_run
    check("  _healthy is the server answering, not the process living",
          (_sw_h1, _sw_h2), (False, True))
    # Ownership follows what the restart actually did: a reused instance
    # is not ours to quit! -- that discards someone's unsaved documents.
    _sw_old_restart = _verify._restart
    try:
        _verify._restart = lambda: (True, False)     # reused, not started
        _sw_own = {"it": False}
        _verify._restart_owned(_sw_own)
        _sw_reused = _sw_own["it"]
        _verify._restart = lambda: (True, True)      # started fresh
        _verify._restart_owned(_sw_own)
        _sw_started = _sw_own["it"]
    finally:
        _verify._restart = _sw_old_restart
    check("  a reused instance is never claimed; a started one is",
          (_sw_reused, _sw_started), (False, True))
    # A panel that will not close is not a wedge, and reuse keeps it. An
    # instance the sweep started is quit and replaced; one it borrowed is
    # not the sweep's to quit, so the sweep stops instead of recording the
    # same fact against every command left.
    _pz_old = (_verify._restart, _verify.running, _verify._snapshot,
               _verify._quit, _verify._cancel)
    try:
        _verify.running = lambda: True
        _verify._snapshot = lambda: {"panel": True}
        _verify._cancel = lambda: None
        _pz_quits = []
        _verify._quit = lambda: _pz_quits.append(1) or True
        _verify._restart = lambda: (True, True)
        _pz_ours = _verify._restart_owned({"it": True})
        _pz_quit_ours = len(_pz_quits)
        _pz_theirs = _verify._restart_owned({"it": False})
        check("  a poisoned instance the sweep started is quit and replaced",
              (_pz_ours, _pz_quit_ours), (True, 1))
        check("    one it borrowed is not, and the sweep stops",
              (_pz_theirs, len(_pz_quits)), (False, 1))
        # And an instance with nothing open is left alone either way.
        _verify._snapshot = lambda: {"panel": False}
        _pz_clean = _verify._restart_owned({"it": False})
        check("    an instance with no panel open is restarted, not quit",
              (_pz_clean, len(_pz_quits)), (True, 1))
    finally:
        (_verify._restart, _verify.running, _verify._snapshot,
         _verify._quit, _verify._cancel) = _pz_old
    # Resume: an answer stands; busy is the floor's state and retried;
    # a hazard stays so plan() reports the skip; a changed example and
    # an unrecorded draft both run.
    check("  resume keeps answers, retries busy, holds hazards",
          sorted(_verify.resumable(
              {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
              {"A": {"example": "a", "result": "ok"},
               "B": {"example": "b", "result": "busy"},
               "C": {"example": "c", "result": "hazard"},
               "D": {"example": "old", "result": "ok"}})),
          ["B", "C", "D", "E"])
    check("    and retries a no_fixture, the harness's gap not the command's",
          sorted(_verify.resumable(
              {"A": "a"}, {"A": {"example": "a", "result": "no_fixture"}})),
          ["A"])

    # GH #52, the selection tier. A hint is prose, so the read is by
    # phrase: what fixture it names, or the reason there is none.
    check("  a hint naming two solids builds two boxes",
          _verify.fixture_for("Part_Cut",
                              "two shapes (the second is subtracted "
                              "from the first)")[::2],
          ("two_solids", "Box, Box001"))
    check("    the recipe is the lines that build it",
          _verify.fixture_for("Part_Cut", "two shapes")[1],
          ["box 0,0,0 20 20 10", "box 10,10,5 20 20 10"])
    # A rule scoped to a workbench reads only that workbench's hints: the
    # same words mean a sketch inside the body, or one at the root.
    check("    'a sketch' in PartDesign is a sketch inside the body",
          _verify.fixture_for("PartDesign_Pad", "a sketch, or one or more "
                              "faces of the active body")[0],
          "body_sketch")
    check("    and in Part it is one at the document root",
          _verify.fixture_for("Part_MakeFace", "one or more objects "
                              "containing closed coplanar wires (e.g. a "
                              "sketch)")[0],
          "closed_wire")
    # Narrow above broad: a hint that offers a shape instead of a mesh
    # takes the shape, and one that rules a face out takes the solid.
    check("    a hint offering a shape instead of a mesh takes the shape",
          _verify.fixture_for("Part_PointsFromMesh",
                              "one or more geometric objects (shapes or "
                              "meshes)")[0],
          "solid")
    check("    a hint that rules a face out takes the whole solid",
          _verify.fixture_for("Part_CheckGeometry",
                              "a whole part (a solid, not just a face)")[0],
          "solid")
    # A punted workbench is punted whatever its hint says.
    check("  a workbench this tier cannot fixture is punted with a reason",
          _verify.fixture_for("Sketcher_ConstrainAngle", "two lines"),
          (None, [], _verify.PUNT_WORKBENCHES["Sketcher"]))
    check("    even when its hint reads like one the rules would take",
          _verify.fixture_for("TechDraw_ExtensionCustomizeFormat",
                              "one or more objects")[0],
          None)
    # A hint inside a covered workbench can still name what no command
    # line builds; the rule that says so maps to no fixture.
    check("  an unbuildable operand in a covered workbench is punted",
          _verify.fixture_for("Std_Cut", "one or more spreadsheet cells"),
          (None, [], "no fixture for a hint naming "
                     "'one or more spreadsheet cells'"))
    # The rule that says no must end the read, not defer to the next rule:
    # a mesh is "one or more objects" too, and the broad rule would hand
    # it a box.
    check("    and the rule that says no ends the read",
          _verify.fixture_for("Part_Zzz", "one or more mesh objects"),
          (None, [], "no fixture for a hint naming "
                     "'one or more mesh objects'"))
    check("  a hint no rule reads is punted, not guessed at",
          _verify.fixture_for("Part_Zzz", "the smell of rain"),
          (None, [], "no rule reads the hint 'the smell of rain'"))
    check("    and so is a command with no hint at all",
          _verify.fixture_for("Part_Zzz", None),
          (None, [], "no selection hint to build from"))
    # Every fixture a rule points at has a recipe.
    check("  every rule names a fixture that exists",
          sorted({n for _s, _p, n in _verify.HINT_RULES
                  if n is not None and n not in _verify.FIXTURES}),
          [])
    # And every recipe is reachable, through one of the two doors there
    # are: a hint rule, or a `panel_fixture` a panel draft authored
    # (GH #53). Falsifying this once removed two dead recipes, which is
    # why it is worth widening rather than dropping.
    _fx_authored = {e.get("panel_fixture") for e in _spec_modes.values()
                    if e.get("panel_fixture")}
    check("    and every fixture is one some rule or draft reaches",
          sorted(set(_verify.FIXTURES)
                 - {n for _s, _p, n in _verify.HINT_RULES} - _fx_authored),
          [])
    check("      every authored panel_fixture naming a fixture that exists",
          sorted(n for n in _fx_authored if n not in _verify.FIXTURES), [])

    # ADR-200 writes a selection example in two parts; the verb is the
    # half left to judge once the select has been run as setup.
    check("  the verb half of a two-part example is what runs",
          _verify.verb_line("select Box, Box001; part_cut"), "part_cut")
    check("    the first semicolon splits it",
          _verify.verb_line("select A; chamfer 45 equal_distance 0 2 2"),
          "chamfer 45 equal_distance 0 2 2")
    check("    a one-part example is the whole line",
          _verify.verb_line("part_cut"), "part_cut")

    # The fixture is built by command lines in a scratch document of its
    # own. The reset is best-effort; every recipe line after it must run.
    _fx_ran = []

    def _fx_ok(line):
        _fx_ran.append(line)
        return 0, "", ""
    check("  a fixture runs its recipe after a fresh scratch document",
          (_verify.build_fixture(["box 0,0,0 1 1 1", "select Box"],
                                 run=_fx_ok), _fx_ran),
          ((True, ""),
           ["close!", "new verify", "no_selection_filters",
            "box 0,0,0 1 1 1", "select Box"]))
    # GH #73. Part's selection filters are a mode, not a document: closing
    # the document does not clear one, and with one on `select` reports
    # success and selects nothing. So the preparation lifts the gate too,
    # before every command rather than after the one that set it -- and
    # after the document is open, because the lift needs one.
    check("    the preparation lifts a selection gate, once a document is open",
          _verify.PREPARE, ["close!", "new verify", "no_selection_filters"])
    _fx_gate = []

    def _fx_no_gate(line):
        _fx_gate.append(line)
        return (1, "", "no_selection_filters: is not available here") \
            if line == "no_selection_filters" else (0, "", "")
    check("      and nothing to lift is not a failure either",
          (_verify.build_fixture(["box 0,0,0 1 1 1"], run=_fx_no_gate)[0],
           len(_fx_gate)),
          (True, 4))

    def _fx_no_doc(line):
        return (1, "", "cannot open a document") if line == "new verify" \
            else (0, "", "")
    check("      but a document that will not open is a fixture undelivered",
          _verify.build_fixture(["box 0,0,0 1 1 1"], run=_fx_no_doc),
          (False, "new verify -- cannot open a document"))

    _fx_ran2 = []

    def _fx_no_close(line):
        _fx_ran2.append(line)
        return (1, "", "no document") if line == "close!" else (0, "", "")
    check("    the first command has nothing to close, which is not a failure",
          (_verify.build_fixture(["box 0,0,0 1 1 1"], run=_fx_no_close)[0],
           len(_fx_ran2)),
          (True, 4))

    _fx_ran3 = []

    def _fx_break(line):
        _fx_ran3.append(line)
        return (1, "", "no such object: Wire") if line.startswith("select") \
            else (0, "", "")
    _fx_bad = _verify.build_fixture(["upgrade", "select Wire", "part_cut"],
                                    run=_fx_break)
    check("    a recipe line that faults stops the build and names itself",
          (_fx_bad[0], _fx_bad[1], _fx_ran3[-1]),
          (False, "select Wire -- no such object: Wire", "select Wire"))
    check("      and the lines after it never run",
          "part_cut" in _fx_ran3, False)

    def _fx_silent(line):
        return (3, "", "") if line == "upgrade" else (0, "", "")
    check("      a fault with nothing on stderr still names its exit",
          _verify.build_fixture(["upgrade"], run=_fx_silent)[1],
          "upgrade -- exit 3")

    # What the tier drives, and what it says about the rest.
    _st_map = {"commands": {
        "Part_Cut": {"mode": "selection", "example": "part_cut",
                     "selection_hint": "two shapes"},
        "Part_Box": {"mode": "positional", "example": "box 1 1 1"},
        "Sketcher_Trim": {"mode": "selection", "example": "trim",
                          "selection_hint": "one or more sketch elements"},
        "Part_Mystery": {"mode": "selection", "example": "mystery",
                         "selection_hint": "the smell of rain"},
        "Part_Undrafted": {"mode": "selection", "example": "",
                           "selection_hint": "one or more objects"},
    }}
    _st_targets, _st_fixtures, _st_punted = _verify.selection_targets(_st_map)
    check("  the tier's example is ADR-200's two-part one",
          _st_targets, {"Part_Cut": "select Box, Box001; part_cut"})
    check("    and the select that hands the fixture over is its last line",
          _st_fixtures["Part_Cut"][-1], "select Box, Box001")
    check("    a positional command is not the selection tier's",
          "Part_Box" in _st_targets or "Part_Box" in _st_punted, False)
    check("    a hint with no fixture is punted, with the reason",
          (sorted(_st_punted),
           _st_punted["Sketcher_Trim"]),
          (["Part_Mystery", "Part_Undrafted", "Sketcher_Trim"],
           _verify.PUNT_WORKBENCHES["Sketcher"]))
    check("    so is a command the mode map drafted no example for",
          _st_punted["Part_Undrafted"],
          "the mode map drafted no example to run")

    # sweep()'s setup hook, on stubs: the fixture is the harness's job, so
    # a fixture that will not build is the harness's result, not a verb's.
    _sp_events = []
    _sp_ran = []
    _sp_tally, _sp_fin, _sp_n = _verify.sweep(
        {"A_A": "select Box; a", "B_B": "select Box; b"},
        lambda cid, ex, res, det, extra=None: _sp_events.append((cid, res, det)),
        run_one=lambda cid, e: _sp_ran.append(e) or ("ok", ""),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True,
        setup=lambda cid: (True, "") if cid == "A_A"
        else (False, "select Wire -- no such object: Wire"))
    check("  a fixture that will not build is no_fixture, and the sweep goes on",
          (_sp_events, _sp_fin),
          ([("A_A", "ok", ""),
            ("B_B", "no_fixture", "select Wire -- no such object: Wire")],
           True))
    check("    and the verb of a command with no fixture never runs",
          _sp_ran, ["select Box; a"])

    # A fixture that fails because the instance died is that hazard, not a
    # gap in the vocabulary -- the next command would hit it too.
    _sp_events2 = []
    _sp_restarts = []
    _sp_tally2, _sp_fin2, _sp_n2 = _verify.sweep(
        {"C_C": "select Box; c"},
        lambda cid, ex, res, det, extra=None: _sp_events2.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: False, healthy=lambda: False,
        restart=lambda: _sp_restarts.append(1) or True,
        setup=lambda cid: (False, "new verify -- no instance"))
    check("    a fixture that failed because FreeCAD died is a hazard",
          (_sp_events2, _sp_n2, _sp_fin2),
          ([("C_C", "hazard", "fixture: new verify -- no instance")], 1, True))

    _sp_events3 = []
    _sp_tally3, _sp_fin3, _sp_n3 = _verify.sweep(
        {"D_D": "select Box; d", "E_E": "select Box; e"},
        lambda cid, ex, res, det, extra=None: _sp_events3.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: False, healthy=lambda: False, restart=lambda: False,
        setup=lambda cid: (False, "new verify -- no instance"))
    check("      and a restart that fails stops the sweep there",
          ([c for c, _r, _d in _sp_events3], _sp_fin3), (["D_D"], False))

    def _sp_slow(cid):
        raise _sh.TimeoutExpired("fccli", 60)
    _sp_events4 = []
    _sp_tally4, _sp_fin4, _sp_n4 = _verify.sweep(
        {"F_F": "select Box; f"},
        lambda cid, ex, res, det, extra=None: _sp_events4.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True,
        setup=_sp_slow)
    check("    a fixture build that times out is recorded, not raised",
          _sp_events4,
          [("F_F", "no_fixture", "client timed out; instance wedged")])

    # Setup failure and a health probe that will not answer, together. A
    # probe that times out says nothing about the instance, so the failed
    # fixture cannot be charged to the vocabulary: it is the hazard PR #63
    # exists to catch, arriving through the setup door. Every other case
    # here varies one of the two, which is why this one is written out.
    def _sp_slow_health():
        raise _sh.TimeoutExpired("fccli", 60)
    _sp_events5, _sp_restarts5 = [], []
    _sp_tally5, _sp_fin5, _sp_n5 = _verify.sweep(
        {"G_G": "select Box; g", "H_H": "select Box; h"},
        lambda cid, ex, res, det, extra=None: _sp_events5.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: True, healthy=_sp_slow_health,
        restart=lambda: _sp_restarts5.append(1) or True,
        setup=lambda cid: (False, "new verify -- silence"))
    check("      a failed fixture whose health probe times out is the hazard",
          (_sp_events5, _sp_n5, len(_sp_restarts5), _sp_tally5, _sp_fin5),
          ([("G_G", "hazard", "fixture: new verify -- silence"),
            ("H_H", "hazard", "fixture: new verify -- silence")],
           2, 2, {"hazard": 2}, True))
    # Both timeouts at once: the build times out and so does the probe
    # that would say whether anything is still there.
    _sp_events6, _sp_restarts6 = [], []
    _sp_tally6, _sp_fin6, _sp_n6 = _verify.sweep(
        {"I_I": "select Box; i"},
        lambda cid, ex, res, det, extra=None: _sp_events6.append((cid, res, det)),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: True, healthy=_sp_slow_health,
        restart=lambda: _sp_restarts6.append(1) or True,
        setup=_sp_slow)
    check("      and a build and a probe that both time out is too",
          (_sp_events6, len(_sp_restarts6)),
          ([("I_I", "hazard",
             "fixture: client timed out; instance wedged")], 1))
    # ---------------------------------------------------------- panel tier
    # GH #53. A panel command takes `name=value` and then `done`, and the
    # engine answers with the panel's own field names on a name it has not
    # got. Every branch below was reintroduced as a mutant and the named
    # check confirmed to fail.
    #
    # A scripted panel, so each branch can be reached on its own -- a live
    # one reaches them one at a time and not on request. ``replies``
    # answers a line the way the client does, (code, out, err); ``snaps``
    # is the state after each read, the last one repeating. The first read
    # is the one `cleared` makes on the way in.
    _S_IDLE = {"engine": "idle", "options": [], "panel": False,
               "documents": [{"active": True, "invalid": []}]}
    _S_PANEL = {"engine": "collecting", "options": ["done"], "panel": True,
                "documents": [{"active": True, "invalid": []}]}
    _S_OPEN = {"engine": "idle", "options": [], "panel": True,
               "documents": [{"active": True, "invalid": []}]}

    def _panel(replies, snaps):
        log = {"lines": [], "cancels": 0, "snaps": list(snaps)}

        def run(line):
            log["lines"].append(line)
            return replies.get(line, (0, "", ""))

        def snapshot():
            queue = log["snaps"]
            if not queue:
                return {}
            return queue.pop(0) if len(queue) > 1 else queue[0]

        def cancel():
            log["cancels"] += 1
        return run, snapshot, cancel, log

    # A draft is one line a person can type: the verb, then the fields.
    check("  a panel draft splits into the verb and its fields",
          _verify.split_pairs("part_fillet filletstartradius=3"),
          ("part_fillet", [("filletstartradius", "3")]))
    check("    a draft with no fields is all verb",
          _verify.split_pairs("part_fillet"), ("part_fillet", []))
    check("    several fields, in order",
          _verify.split_pairs("transform xposition=25 zposition=3")[1],
          [("xposition", "25"), ("zposition", "3")])
    check("    a value runs to the next name=, so it may hold spaces",
          _verify.split_pairs("partdesign_mirror comboplane=Base XZ-plane"),
          ("partdesign_mirror", [("comboplane", "Base XZ-plane")]))
    check("      and a unit is part of the value, not a token after it",
          _verify.split_pairs("transform zposition=3/4 in xposition=2")[1],
          [("zposition", "3/4 in"), ("xposition", "2")])
    # panels.py's rule, and for its reason: no space before the `=` is
    # what tells an assignment from prose that contains one.
    check("      prose with an = in it is not a second assignment",
          _verify.split_pairs("label_it label=Wall A = north")[1],
          [("label", "Wall A = north")])
    check("    the verb keeps its positional arguments",
          _verify.split_pairs("place 0,0,0 xposition=2")[0], "place 0,0,0")
    # The copy of panels.ASSIGNMENT is a copy on purpose -- nothing in
    # verify.py may import FreeCAD's Qt -- so it is pinned to the original.
    _pn_src = open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "fccli", "panels.py"), encoding="utf-8").read()
    check("    and its regex is still the one panels.py uses",
          _verify._ASSIGNMENT.pattern in _pn_src, True)

    _ann = ("3 to set:\n"
            "  filletstartradius  fillettype         shapeobject\n"
            "name=value sets one · done applies · cancel abandons\n")
    check("  the block a panel prints when it opens names every field",
          _verify.announced_fields(_ann),
          ["filletstartradius", "fillettype", "shapeobject"])
    check("    the unindented hint line ends the block",
          _verify.announced_fields(_ann + "  and this is after it\n"),
          ["filletstartradius", "fillettype", "shapeobject"])
    check("    a re-announce after a choice reads the same way",
          _verify.announced_fields("2 to set now:\n  radius  height\n"),
          ["radius", "height"])
    check("    output with no block names nothing",
          _verify.announced_fields("= part_fillet\n"), [])
    check("    indented words with no heading over them are not fields",
          _verify.announced_fields("  radius  height\n"), [])
    check("    and a heading with nothing indented under it, nothing",
          _verify.announced_fields("3 to set:\nnot indented\n"), [])

    _short = ("error: '__fccli_probe' is not on this panel -- axis, "
              "changemode, checkboxmidplane, checkboxreversed, "
              "checkboxupdateview, revolveangle...")
    check("  the complaint on a wrong name lists the panel's real ones",
          _verify.probed_fields("error: 'radius' is not on this panel -- "
                                "filletstartradius, fillettype, shapeobject"),
          (["filletstartradius", "fillettype", "shapeobject"], False))
    check("    over six it is capped, and says so",
          (_verify.probed_fields(_short)[1],
           _verify.probed_fields(_short)[0][-1]),
          (True, "revolveangle"))
    check("    no complaint names nothing",
          _verify.probed_fields("incomplete: still wants name=value"),
          ([], False))

    check("  the engine's fault is the error line, without its prefix",
          _verify._fault("error: 'radius' is not on this panel -- a, b\n"
                         "incomplete: still wants name=value [done]"),
          "'radius' is not on this panel -- a, b")
    check("    a run with no error line has no fault",
          _verify._fault("incomplete: still wants name=value [done]"), "")

    # Asked both ways: the probe is an answer to a question, the block is
    # complete. A capped complaint is completed from the block, which is
    # the case a panel of eleven fields makes every time.
    _pf_probe = {f"{_verify.PROBE_NAME}=1": (1, "", _short)}
    _pf_run, _pf_snap, _pf_cancel, _pf_log = _panel(_pf_probe, [{}])
    check("  a capped complaint is completed from the announced block",
          _verify.panel_fields(_pf_run, "8 to set:\n  axis  changemode  "
                               "checkboxmidplane  checkboxreversed  "
                               "checkboxupdateview  revolveangle  showfinal  "
                               "showtransparentpreview\n"),
          ["axis", "changemode", "checkboxmidplane", "checkboxreversed",
           "checkboxupdateview", "revolveangle", "showfinal",
           "showtransparentpreview"])
    check("    and the probe is what was typed to ask",
          _pf_log["lines"], [f"{_verify.PROBE_NAME}=1"])
    _pf_run2, _, _, _ = _panel(
        {f"{_verify.PROBE_NAME}=1":
         (1, "", "error: 'x' is not on this panel -- radius, height")}, [{}])
    check("    with no block, the complaint is the whole answer",
          _verify.panel_fields(_pf_run2, "= verb\n"), ["height", "radius"])

    # C4, both ends. A panel is closed on the way in, because one left by
    # anything else is adopted by the next verb typed; and the close is
    # confirmed, because asking is not the same as it happening.
    _cl_run, _cl_snap, _cl_cancel, _cl_log = _panel({}, [_S_IDLE])
    check("  a panel that closes when asked is cleared, once",
          (_verify.cleared(_cl_snap, _cl_cancel), _cl_log["cancels"]),
          (True, 1))
    _cl_run2, _cl_snap2, _cl_cancel2, _cl_log2 = _panel({}, [_S_OPEN])
    check("    one that will not close is not, and it was asked three times",
          (_verify.cleared(_cl_snap2, _cl_cancel2), _cl_log2["cancels"]),
          (False, 3))

    # The whole step, on a scripted panel. The happy path first: the verb
    # opens it, the fields are read, the draft's pairs are set, done
    # applies, and nothing was left invalid.
    _vp_probe = {f"{_verify.PROBE_NAME}=1":
                 (1, "", "error: 'x' is not on this panel -- "
                         "filletstartradius, fillettype, shapeobject")}
    _vp_run, _vp_snap, _vp_cancel, _vp_log = _panel(
        dict(_vp_probe, **{"part_fillet": (1, _ann, "incomplete: still "
                                                    "wants name=value")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  a panel driven to completion is ok",
          _verify.verify_panel("select Box.Edge1; part_fillet "
                               "filletstartradius=3",
                               run=_vp_run, snapshot=_vp_snap,
                               cancel=_vp_cancel),
          ("ok", "", {"fields": ["filletstartradius", "fillettype",
                                 "shapeobject"]}))
    check("    the select half is setup, so the verb alone is what runs",
          _vp_log["lines"][0], "part_fillet")
    check("    the draft's field is set, and then done",
          _vp_log["lines"][2:], ["filletstartradius=3", "done"])
    check("    and a clean apply closes nothing after itself",
          _vp_log["cancels"], 1)

    # A draft with no pairs is still a run: open, read, done. That is C1
    # without parameters, and it is what most of the tier's drafts are.
    _vp_run2, _vp_snap2, _vp_cancel2, _vp_log2 = _panel(
        _vp_probe, [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  a draft with no fields still opens, reads and applies",
          (_verify.verify_panel("part_fillet", run=_vp_run2,
                                snapshot=_vp_snap2, cancel=_vp_cancel2)[0],
           _vp_log2["lines"][-1]),
          ("ok", "done"))

    # A panel left by something before this one, that nothing can close.
    # Every command run against it is answered as though it were the one
    # at fault -- 17 were, live -- so nothing is judged until it is gone.
    _vp_run0, _vp_snap0, _vp_cancel0, _vp_log0 = _panel({}, [_S_OPEN])
    check("  a command a panel stood in front of is blocked, and never ran",
          (_verify.verify_panel("part_fillet", run=_vp_run0,
                                snapshot=_vp_snap0, cancel=_vp_cancel0),
           _vp_log0["lines"]),
          (("blocked", "a panel left open before this command would not "
                       "close", {}), []))
    check("    which is not an answer about it, so a later sweep retries it",
          sorted(_verify.resumable(
              {"A_A": "a", "B_B": "b", "C_C": "c"},
              {"A_A": {"example": "a", "result": "blocked"},
               "B_B": {"example": "b", "result": "stuck_panel"},
               "C_C": {"example": "c", "result": "ok"}})),
          ["A_A"])

    # The floor belongs to someone else. Nothing was opened, so nothing is
    # closed, and the sweep retries a busy later.
    _vp_run3, _vp_snap3, _vp_cancel3, _vp_log3 = _panel(
        {"part_fillet": (75, "", "")}, [_S_IDLE])
    check("  a busy floor is busy, and the verb never got as far as a panel",
          (_verify.verify_panel("part_fillet", run=_vp_run3,
                                snapshot=_vp_snap3, cancel=_vp_cancel3),
           _vp_log3["lines"]),
          (("busy", "", {}), ["part_fillet"]))

    # no_panel: the mode map calls this a panel command and the verb is
    # not one. Three shapes of it, because the detail is the finding.
    _vp_run4, _vp_snap4, _vp_cancel4, _vp_log4 = _panel(
        {}, [_S_IDLE, _S_IDLE, _S_IDLE])
    check("  a verb that opened no panel is no_panel, not ok",
          _verify.verify_panel("multi_transform", run=_vp_run4,
                               snapshot=_vp_snap4, cancel=_vp_cancel4),
          ("no_panel", "no panel; the verb ran to completion", {}))
    check("    and nothing was typed at a panel that was not there",
          _vp_log4["lines"], ["multi_transform"])
    _vp_run5, _vp_snap5, _vp_cancel5, _ = _panel(
        {"revolution": (0, "", "")},
        [_S_IDLE, _S_IDLE,
         {"engine": "idle", "options": [], "panel": False,
          "documents": [{"active": True, "invalid": ["Revolution"]}]}])
    check("    a verb that left an invalid object says which",
          _verify.verify_panel("revolution", run=_vp_run5,
                               snapshot=_vp_snap5, cancel=_vp_cancel5),
          ("no_panel", "no panel; left invalid: Revolution", {}))
    _vp_run6, _vp_snap6, _vp_cancel6, _ = _panel(
        {"partdesign_mirror": (1, "", "error: partdesign_mirror: Active "
                                      "Body Required -- activate a body")},
        [_S_IDLE, _S_IDLE, _S_IDLE])
    check("    a refused verb carries FreeCAD's own reason",
          _verify.verify_panel("partdesign_mirror", run=_vp_run6,
                               snapshot=_vp_snap6, cancel=_vp_cancel6),
          ("no_panel", "no panel; partdesign_mirror: Active Body Required "
                       "-- activate a body", {}))
    # Collecting, but not at a panel step: a positional verb the mode map
    # called a panel. It is left holding a prompt, so it is cleared.
    _vp_run7, _vp_snap7, _vp_cancel7, _vp_log7 = _panel(
        {}, [_S_IDLE, _S_IDLE,
             {"engine": "collecting", "options": [], "panel": False,
              "prompt": "The radius",
              "documents": [{"active": True, "invalid": []}]},
             _S_IDLE])
    check("    a verb still collecting something that is not a field",
          (_verify.verify_panel("cylinder", run=_vp_run7,
                                snapshot=_vp_snap7, cancel=_vp_cancel7),
           _vp_log7["cancels"]),
          (("no_panel", "no panel; still wants The radius", {}), 2))

    # mouse_panel: something opened that the command line cannot drive.
    # The engine says so in its own words; either way it is closed (C4).
    _vp_run8, _vp_snap8, _vp_cancel8, _vp_log8 = _panel(
        {"check_geometry": (0, "the panel offers nothing this can type "
                               "into -- it is open for the mouse\n", "")},
        [_S_IDLE, _S_IDLE, _S_OPEN, _S_IDLE])
    check("  a panel with no way in from here is a mode, and is closed",
          (_verify.verify_panel("check_geometry", run=_vp_run8,
                                snapshot=_vp_snap8, cancel=_vp_cancel8),
           _vp_log8["cancels"]),
          (("mouse_panel", "a panel with no way in from here", {}), 2))
    _vp_run9, _vp_snap9, _vp_cancel9, _vp_log9 = _panel(
        {}, [_S_IDLE, _S_IDLE,
             {"engine": "collecting", "options": ["cancel"], "panel": True,
              "documents": [{"active": True, "invalid": []}]},
             _S_IDLE])
    check("    so is a panel step that does not offer done",
          (_verify.verify_panel("mode_thing", run=_vp_run9,
                                snapshot=_vp_snap9,
                                cancel=_vp_cancel9)[0],
           _vp_log9["cancels"]),
          ("mouse_panel", 2))
    # And a mode panel that will not close is the poisoning one, blamed on
    # the command that left it rather than on the next thing to run.
    _vp_run9b, _vp_snap9b, _vp_cancel9b, _ = _panel(
        {}, [_S_IDLE, _S_IDLE, _S_OPEN])
    check("      one that will not close is stuck_panel, with what it was",
          _verify.verify_panel("mesh_from_shape", run=_vp_run9b,
                               snapshot=_vp_snap9b, cancel=_vp_cancel9b)[:2],
          ("stuck_panel", "mouse_panel: a panel with no way in from here; "
                          "and the panel would not close"))

    # bad_field: the draft named a field the panel has not got. The detail
    # is the engine's complaint, which names the ones it has, and the
    # fields already read are kept -- that is what makes it diagnosable
    # rather than just failed.
    _vp_run10, _vp_snap10, _vp_cancel10, _vp_log10 = _panel(
        dict(_vp_probe, **{
            "part_fillet": (1, _ann, ""),
            "radius=3": (1, "", "error: 'radius' is not on this panel -- "
                                "filletstartradius, fillettype, shapeobject")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    _vp10 = _verify.verify_panel("part_fillet radius=3", run=_vp_run10,
                                 snapshot=_vp_snap10, cancel=_vp_cancel10)
    check("  a field the panel has not got is bad_field, with the real names",
          (_vp10[0], _vp10[1]),
          ("bad_field", "'radius' is not on this panel -- filletstartradius, "
                        "fillettype, shapeobject"))
    check("    the fields read before it are kept",
          _vp10[2], {"fields": ["filletstartradius", "fillettype",
                                "shapeobject"]})
    check("    done is never pressed on a draft that was refused",
          "done" in _vp_log10["lines"], False)
    check("      and the panel it was refused at is closed",
          _vp_log10["cancels"], 2)
    # A value the panel refuses is not a wrong name. The engine names the
    # choices, which is the answer somebody typing it would want.
    _vp_run11, _vp_snap11, _vp_cancel11, _vp_log11 = _panel(
        dict(_vp_probe, **{
            "combotype=zzz": (1, "", "error: combotype: 'zzz' is not one "
                                     "of: Fuse, Cut, Common")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  a value the panel refuses is broken, not bad_field",
          _verify.verify_panel("boolean_operation combotype=zzz",
                               run=_vp_run11, snapshot=_vp_snap11,
                               cancel=_vp_cancel11)[:2],
          ("broken", "combotype: 'zzz' is not one of: Fuse, Cut, Common"))
    check("    and that panel is closed too",
          _vp_log11["cancels"], 2)
    # The floor taken mid-draft, between two fields.
    _vp_run12, _vp_snap12, _vp_cancel12, _vp_log12 = _panel(
        dict(_vp_probe, **{"height=2": (75, "", "")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  a floor taken between two fields is busy, and closes the panel",
          (_verify.verify_panel("thing height=2", run=_vp_run12,
                                snapshot=_vp_snap12,
                                cancel=_vp_cancel12)[0],
           _vp_log12["cancels"]),
          ("busy", 2))

    # A choice can swap the page under whatever comes next, and the engine
    # re-announces when it does. Those names are the panel's too.
    _vp_run13, _vp_snap13, _vp_cancel13, _ = _panel(
        dict(_vp_probe, **{
            "fillettype=variable": (1, "2 to set now:\n  filletendradius  "
                                       "filletstartradius\n", "")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  fields a choice revealed are recorded with the rest",
          _verify.verify_panel("part_fillet fillettype=variable",
                               run=_vp_run13, snapshot=_vp_snap13,
                               cancel=_vp_cancel13)[2],
          {"fields": ["filletstartradius", "fillettype", "shapeobject",
                      "filletendradius"]})

    # What done left. The delta-invalidity read is the shared one (C3):
    # what this run made invalid, not what it found already broken.
    _vp_run14, _vp_snap14, _vp_cancel14, _vp_log14 = _panel(
        _vp_probe,
        [_S_IDLE,
         {"engine": "idle", "panel": False,
          "documents": [{"active": True, "invalid": ["Old"]}]},
         _S_PANEL,
         {"engine": "idle", "options": [], "panel": False,
          "documents": [{"active": True, "invalid": ["Old", "Fillet"]}]}])
    check("  a panel that applied an invalid object is invalid, and undone",
          (_verify.verify_panel("part_fillet", run=_vp_run14,
                                snapshot=_vp_snap14,
                                cancel=_vp_cancel14)[:2],
           _vp_log14["lines"][-1]),
          (("invalid", "Fillet"), "undo"))
    _vp_run15, _vp_snap15, _vp_cancel15, _vp_log15 = _panel(
        dict(_vp_probe, **{"done": (0, "", "")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_OPEN, _S_IDLE])
    check("  a panel done would not close is panel, and is closed after",
          (_verify.verify_panel("part_fillet", run=_vp_run15,
                                snapshot=_vp_snap15,
                                cancel=_vp_cancel15)[0],
           _vp_log15["cancels"]),
          ("panel", 2))
    _vp_run15b, _vp_snap15b, _vp_cancel15b, _vp_log15b = _panel(
        dict(_vp_probe, **{"done": (0, "", "")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_OPEN])
    check("    and one that will not close even then is stuck_panel",
          (_verify.verify_panel("mesh_from_shape", run=_vp_run15b,
                                snapshot=_vp_snap15b,
                                cancel=_vp_cancel15b)[:2],
           _vp_log15b["cancels"]),
          (("stuck_panel", "panel; and the panel would not close"), 4))
    _vp_run16, _vp_snap16, _vp_cancel16, _vp_log16 = _panel(
        dict(_vp_probe, **{"done": (1, "", "error: part_fillet: No edge "
                                          "selected -- check one first")}),
        [_S_IDLE, _S_IDLE, _S_PANEL, _S_IDLE])
    check("  a done the command refused is broken, with its reason",
          _verify.verify_panel("part_fillet", run=_vp_run16,
                               snapshot=_vp_snap16,
                               cancel=_vp_cancel16)[:2],
          ("broken", "part_fillet: No edge selected -- check one first"))
    _vp_run17, _vp_snap17, _vp_cancel17, _vp_log17 = _panel(
        _vp_probe,
        [_S_IDLE, _S_IDLE, _S_PANEL,
         {"engine": "collecting", "options": [], "panel": False,
          "documents": [{"active": True, "invalid": []}]},
         _S_IDLE])
    check("  a done that closed the panel and kept collecting is incomplete",
          (_verify.verify_panel("part_fillet", run=_vp_run17,
                                snapshot=_vp_snap17,
                                cancel=_vp_cancel17)[0],
           _vp_log17["cancels"]),
          ("incomplete", 2))

    # What the tier drives, and what it says about the rest.
    _pt_map = {"commands": {
        "Part_Fillet": {"mode": "panel", "verb": "part_fillet",
                        "example": "part_fillet filletstartradius=3",
                        "needs_selection": False, "selection_hint": None,
                        "panel_fixture": "solid_edge"},
        "Part_Primitives": {"mode": "panel", "verb": "primitives",
                            "example": None, "needs_selection": False,
                            "selection_hint": None},
        "Part_Sweep": {"mode": "panel", "verb": "sweep", "example": None,
                       "needs_selection": True,
                       "selection_hint": "a closed wire and a spine"},
        "Sketcher_Fillet": {"mode": "panel", "verb": "sketcher_fillet",
                            "example": None, "needs_selection": True,
                            "selection_hint": "two lines in the sketch"},
        "Part_Nameless": {"mode": "panel", "verb": None, "example": None,
                          "needs_selection": False, "selection_hint": None},
        "Part_Wrong": {"mode": "panel", "verb": "wrong", "example": None,
                       "needs_selection": False, "selection_hint": None,
                       "panel_fixture": "no_such_fixture"},
        "Draft_SetStyle": {"mode": "panel", "verb": "set_style",
                           "example": None, "needs_selection": False,
                           "selection_hint": None},
        "Part_Cut": {"mode": "selection", "verb": "part_cut",
                     "example": "part_cut", "needs_selection": True,
                     "selection_hint": "two shapes"},
    }}
    _pt_targets, _pt_fixtures, _pt_punted = _verify.panel_targets(_pt_map)
    check("  a panel command with no operands runs in an empty document",
          (_pt_targets["Part_Primitives"], _pt_fixtures["Part_Primitives"]),
          ("primitives", []))
    check("    one whose hint names operands gets the selection tier's fixture",
          (_pt_targets["Part_Sweep"], _pt_fixtures["Part_Sweep"][-1:]),
          ("select Wire, Line004; sweep", ["select Wire, Line004"]))
    check("    an authored panel_fixture is the fixture, hint or no hint",
          (_pt_targets["Part_Fillet"], _pt_fixtures["Part_Fillet"]),
          ("select Box.Edge1; part_fillet filletstartradius=3",
           ["box 0,0,0 20 20 10", "select Box.Edge1"]))
    check("    a panel_fixture naming no fixture is a punt, not a guess",
          _pt_punted.get("Part_Wrong"),
          "panel_fixture names no fixture: no_such_fixture")
    check("    a workbench this tier cannot furnish is punted with its reason",
          _pt_punted.get("Sketcher_Fillet"),
          _verify.PUNT_WORKBENCHES["Sketcher"])
    check("    a command the mode map named no verb for is punted",
          _pt_punted.get("Part_Nameless"), "the mode map named no verb to run")
    check("    a panel that writes the operator's settings is not pressed",
          _pt_punted.get("Draft_SetStyle"),
          _verify.PANEL_OFF_LIMITS["Draft_SetStyle"])
    check("    a selection command is not the panel tier's",
          "Part_Cut" in _pt_targets or "Part_Cut" in _pt_punted, False)
    check("    and every panel command is in one list or the other",
          sorted(set(_pt_targets) | set(_pt_punted)),
          sorted(c for c, e in _pt_map["commands"].items()
                 if e["mode"] == "panel"))
    check("  every off-limits panel is a panel command that exists",
          sorted(c for c in _verify.PANEL_OFF_LIMITS
                 if (_spec_modes.get(c) or {}).get("mode") != "panel"), [])
    # The two tiers and the ledger ask the same question of the same mode
    # map entry, and `panel_operands` is the one answer -- so a panel
    # driven by `make verify` gets the fixture the tier would have given
    # it. Each branch below was reintroduced as a mutant and the named
    # check confirmed to fail.
    check("  a panel that asks for no operands gets an empty document",
          _verify.panel_operands("Part_Primitives",
                                 {"needs_selection": False}),
          ([], None, ""))
    check("    an authored panel_fixture is the fixture, hint or no hint",
          _verify.panel_operands("Part_Fillet",
                                 {"panel_fixture": "solid_edge",
                                  "needs_selection": False}),
          (["box 0,0,0 20 20 10"], "Box.Edge1", ""))
    check("    one naming no fixture is a punt, not a guess",
          _verify.panel_operands("Part_Wrong", {"panel_fixture": "nope"}),
          (None, None, "panel_fixture names no fixture: nope"))
    check("    a hint whose operands this tier cannot build is a punt",
          _verify.panel_operands("Sketcher_Fillet",
                                 {"needs_selection": True,
                                  "selection_hint": "two lines"}),
          (None, None, _verify.PUNT_WORKBENCHES["Sketcher"]))
    check("    and a panel that writes the operator's settings is not pressed",
          _verify.panel_operands("Draft_SetStyle", {"needs_selection": False}),
          (None, None, _verify.PANEL_OFF_LIMITS["Draft_SetStyle"]))

    # -------------------------------------------------- the mode-routed ledger
    # GH #54. `make verify` drives every authored example, and the mode map
    # says how each one is driven. Before this, every example ran bare: a
    # selection example judged its own `select` line and a panel example
    # was recorded `panel` for opening the panel it exists to open.
    check("  the setup half of a two-part example is the select",
          _verify.select_half("select Box, Box001; part_cut"),
          "select Box, Box001")
    check("    a one-part example has no setup half",
          _verify.select_half("box 1 1 1"), "")
    check("    and it is the other side of verb_line",
          (_verify.select_half("select A; chamfer 45 equal_distance 0 2 2"),
           _verify.verb_line("select A; chamfer 45 equal_distance 0 2 2")),
          ("select A", "chamfer 45 equal_distance 0 2 2"))

    # Mode routing: the whole difference the ledger gained. A positional
    # example is the line; a selection example's select was setup, so only
    # the verb is judged; a panel example goes through the panel step.
    _dr = []

    def _dr_pos(example):
        _dr.append(("positional", example))
        return "ok", ""

    def _dr_panel(example):
        _dr.append(("panel", example))
        return "ok", "", {"fields": []}
    for _dr_mode, _dr_example in (("positional", "box 0,0,0 40 30 20"),
                                  ("selection", "select Box, Box001; part_cut"),
                                  ("panel", "select Box.Edge1; part_fillet "
                                            "filletstartradius=3")):
        _verify.drive(_dr_mode, _dr_example, positional=_dr_pos,
                      panel=_dr_panel)
    check("  a positional example is driven bare, as the whole line",
          _dr[0], ("positional", "box 0,0,0 40 30 20"))
    check("    a selection example is driven by its verb half alone",
          _dr[1], ("positional", "part_cut"))
    check("    and a panel example goes through the panel step, whole",
          _dr[2], ("panel", "select Box.Edge1; part_fillet "
                            "filletstartradius=3"))
    # A mode with no route is refused, not driven bare. `ledger_targets`
    # punts every such mode before a target is made, so nothing reaches
    # this today -- but a fifth mode added to the map later would be driven
    # bare and stamped verified, which is the bug the extraction exists to
    # make visible (PR #75 review, 1).
    _dr_before = len(_dr)
    _dr_said = ""
    try:
        _verify.drive("brand_new_mode", "whatever", positional=_dr_pos,
                      panel=_dr_panel)
    except ValueError as _dr_exc:
        _dr_said = str(_dr_exc)
    check("    a mode nothing routes is refused, and named",
          ("brand_new_mode" in _dr_said, len(_dr) - _dr_before), (True, 0))

    # What the ledger drives, per command, and what it says about the rest.
    _lg_dict = {
        "Part_Box": {"example": "box 0,0,0 40 30 20"},
        "Part_Cut": {"example": "select Box, Box001; part_cut"},
        "Part_Fillet": {"example": "select Box.Edge1; part_fillet "
                                   "filletstartradius=3"},
        "Part_Primitives": {"example": "primitive"},
        "Sketcher_Trim": {"example": "select Line; trim"},
        "Std_Whatsthis": {"example": "whats_this"},
        "Part_Unstamped": {"example": None},
        "Part_Unknown": {"example": "unknown 1"},
    }
    _lg_map = {
        "Part_Box": {"mode": "positional"},
        "Part_Cut": {"mode": "selection", "selection_hint": "two shapes"},
        "Part_Fillet": {"mode": "panel", "panel_fixture": "solid_edge",
                        "needs_selection": False},
        "Part_Primitives": {"mode": "panel", "needs_selection": False},
        "Sketcher_Trim": {"mode": "selection",
                          "selection_hint": "one or more sketch elements"},
        "Std_Whatsthis": {"mode": "manual"},
        "Part_Unstamped": {"mode": "positional"},
    }
    _lg_t, _lg_f, _lg_m, _lg_p = _verify.ledger_targets(_lg_dict, _lg_map)
    check("  a positional example is a target with no setup at all",
          (_lg_t["Part_Box"], _lg_f["Part_Box"], _lg_m["Part_Box"]),
          ("box 0,0,0 40 30 20", [], "positional"))
    check("    a selection example is driven behind the fixture its hint names",
          (_lg_t["Part_Cut"], _lg_f["Part_Cut"]),
          ("select Box, Box001; part_cut",
           ["box 0,0,0 20 20 10", "box 10,10,5 20 20 10",
            "select Box, Box001"]))
    check("      and the setup ends with the example's own select, not a "
          "canonical one",
          _verify.ledger_targets(
              {"Part_Cut": {"example": "select Box001; part_cut"}},
              {"Part_Cut": {"mode": "selection",
                            "selection_hint": "two shapes"}})[1]["Part_Cut"],
          ["box 0,0,0 20 20 10", "box 10,10,5 20 20 10", "select Box001"])
    check("    a panel example gets the panel tier's fixture and its mode",
          (_lg_f["Part_Fillet"], _lg_m["Part_Fillet"]),
          (["box 0,0,0 20 20 10", "select Box.Edge1"], "panel"))
    check("      one whose panel asks for no operands gets no setup",
          (_lg_t["Part_Primitives"], _lg_f["Part_Primitives"]),
          ("primitive", []))
    check("    an example the harness cannot fixture is punted, not driven",
          (_lg_p.get("Sketcher_Trim"), "Sketcher_Trim" in _lg_t),
          (_verify.PUNT_WORKBENCHES["Sketcher"], False))
    check("    a manual command is a person's, so the harness drives nothing",
          (_lg_p.get("Std_Whatsthis"), "Std_Whatsthis" in _lg_t,
           _lg_m.get("Std_Whatsthis")),
          ("mode manual: a person confirms this one and the harness records "
           "it (ADR-501)", False, "manual"))
    check("    a command with no example is not the ledger's business",
          ("Part_Unstamped" in _lg_t or "Part_Unstamped" in _lg_p), False)
    check("    and one the mode map never classified is driven bare",
          (_lg_t["Part_Unknown"], _lg_m["Part_Unknown"],
           _lg_f["Part_Unknown"]),
          ("unknown 1", "positional", []))
    check("    every example is a target or a punt, never neither",
          sorted(set(_lg_t) | set(_lg_p)),
          sorted(c for c, e in _lg_dict.items() if e["example"]))
    check("  --tier drives one mode and leaves the others alone",
          (sorted(_verify.ledger_targets(_lg_dict, _lg_map,
                                         tier="selection")[0]),
           sorted(_verify.ledger_targets(_lg_dict, _lg_map,
                                         tier="panel")[0])),
          (["Part_Cut"], ["Part_Fillet", "Part_Primitives"]))
    # Every mode the ledger routes has a driver; a mode with no driver
    # would be run bare and recorded as though it had been verified.
    check("    and every driven mode is one the mode map uses",
          sorted(set(_verify.DRIVEN_MODES)
                 - {e.get("mode") for e in _spec_modes.values()}), [])

    # Resume, the ledger's half. An answer stands only if it was about the
    # same example, in the same mode, against the same FreeCAD -- the
    # version because ADR-501's staleness rule is the version stamp, and
    # the mode because an entry written by a mode-blind sweep asserts a
    # driving that no longer happens.
    _rs_entries = {
        "Same": {"example": "a", "result": "ok", "freecad": "1.1.3",
                 "mode": "positional"},
        "OldVersion": {"example": "b", "result": "ok", "freecad": "1.1.2",
                       "mode": "positional"},
        "OtherMode": {"example": "c", "result": "ok", "freecad": "1.1.3",
                      "mode": "positional"},
        "NoMode": {"example": "d", "result": "ok", "freecad": "1.1.3"},
    }
    _rs_modes = {"Same": "positional", "OldVersion": "positional",
                 "OtherMode": "selection", "NoMode": "positional"}
    check("  a resumed ledger sweep runs what the record does not answer",
          sorted(_verify.resumable(
              {"Same": "a", "OldVersion": "b", "OtherMode": "c",
               "NoMode": "d"},
              _rs_entries, version="1.1.3", modes=_rs_modes)),
          ["NoMode", "OldVersion", "OtherMode"])
    check("    and with neither asked for, the draft rule is unchanged",
          sorted(_verify.resumable({"Same": "a", "OldVersion": "b"},
                                   _rs_entries)),
          [])

    # The hooks, and what a command the harness did not drive is called.
    _lh_built, _lh_routed = [], []
    _lh = _verify.ledger_hooks(
        {"Part_Cut": ["box 0,0,0 20 20 10", "select Box"]},
        {"Part_Cut": "selection"},
        build=lambda lines: _lh_built.append(lines) or (True, ""),
        route=lambda mode, example: _lh_routed.append((mode, example))
        or ("ok", ""))
    _lh["setup"]("Part_Cut")
    _lh["run_one"]("Part_Cut", "select Box; part_cut")
    check("  the ledger's setup builds the command's own fixture",
          _lh_built, [["box 0,0,0 20 20 10", "select Box"]])
    check("    and its run routes on the command's own mode",
          _lh_routed, [("selection", "select Box; part_cut")])
    check("  a hint with no fixture is the harness's gap; a manual mode is not",
          (_verify.punt_result("selection"), _verify.punt_result("panel"),
           _verify.punt_result("manual")),
          ("no_fixture", "no_fixture", "manual"))

    # The whole of `make verify`, on a scripted client: the mode reaches
    # the entry, and each mode was driven its own way. Without this, the
    # routing is checkable and the wiring that reaches it is not.
    import json as _json
    _mv_state = {"panel": False, "lines": []}

    def _mv_fccli(*args, **kw):
        if args[0] == "ls":
            return 0, "[]", ""
        if args[0] == "--json":
            snap = {"engine": "idle", "options": [], "panel": False,
                    "documents": [{"active": True, "invalid": []}]}
            if _mv_state["panel"]:
                snap = {"engine": "collecting", "options": ["done"],
                        "panel": True,
                        "documents": [{"active": True, "invalid": []}]}
            return 0, _json.dumps(snap), ""
        if args[0] == "cancel":
            _mv_state["panel"] = False
            return 0, "", ""
        if args[0] != "exec":
            return 0, "", ""
        line = args[1]
        _mv_state["lines"].append(line)
        if line == "part_fillet":
            _mv_state["panel"] = True
            return 1, "2 to set:\n  filletstartradius  fillettype\n", ""
        if line == "done":
            _mv_state["panel"] = False
            return 0, "", ""
        if line == f"{_verify.PROBE_NAME}=1":
            return 1, "", ("error: 'x' is not on this panel -- "
                           "filletstartradius, fillettype")
        return 0, "", ""

    _mv_dict = {
        "freecad": "9.9.9",
        "commands": {
            "Part_Box": {"example": "box 0,0,0 40 30 20"},
            "Part_Cut": {"example": "select Box, Box001; part_cut"},
            "Part_Fillet": {"example": "select Box.Edge1; part_fillet "
                                       "filletstartradius=3"},
            "Std_Whatsthis": {"example": "whats_this"},
        }}
    _mv_map = {"commands": {
        "Part_Box": {"mode": "positional"},
        "Part_Cut": {"mode": "selection", "selection_hint": "two shapes"},
        "Part_Fillet": {"mode": "panel", "panel_fixture": "solid_edge",
                        "needs_selection": False},
        "Std_Whatsthis": {"mode": "manual"},
    }}
    _mv_old = (_verify.DICT, _verify.MODEMAP, _verify.LEDGER, _verify.fccli)
    with tempfile.TemporaryDirectory() as _mv_dir:
        try:
            _verify.DICT = os.path.join(_mv_dir, "dictionary.json")
            _verify.MODEMAP = os.path.join(_mv_dir, "modemap.json")
            _verify.LEDGER = os.path.join(_mv_dir, "verified.json")
            _json.dump(_mv_dict, open(_verify.DICT, "w"))
            _json.dump(_mv_map, open(_verify.MODEMAP, "w"))
            _verify.fccli = _mv_fccli
            _mv_code = _verify.main([])
            # Read defensively: a checkpoint that never landed is a result
            # this check should report, not a crash that hides it.
            _mv_ledger = (_json.load(open(_verify.LEDGER))
                          if os.path.exists(_verify.LEDGER)
                          else {"commands": {}})
            _mv_before = len(_mv_state["lines"])
            _mv_again = _verify.main([])   # the resume, on a full ledger
            _mv_after = len(_mv_state["lines"])
        finally:
            (_verify.DICT, _verify.MODEMAP, _verify.LEDGER,
             _verify.fccli) = _mv_old
    _mv_got = {c: (e.get("mode"), e.get("result"))
               for c, e in _mv_ledger["commands"].items()}
    check("  make verify stamps every mode, and each was driven its own way",
          (_mv_code, _mv_got),
          (0, {"Part_Box": ("positional", "ok"),
               "Part_Cut": ("selection", "ok"),
               "Part_Fillet": ("panel", "ok"),
               "Std_Whatsthis": ("manual", "manual")}))
    check("    the selection example ran its verb, never its whole line",
          ("part_cut" in _mv_state["lines"],
           "select Box, Box001; part_cut" in _mv_state["lines"]),
          (True, False))
    def _mv_where(line):
        """Where a line was typed, or -1. A mutant that stops a line being
        typed at all must fail the check about it, not stop the run on an
        index that is not there (PR #75 review, 6)."""
        lines = _mv_state["lines"]
        return lines.index(line) if line in lines else -1
    _mv_at = _mv_where("part_cut")
    check("    behind the fixture its hint names, selected first",
          _mv_state["lines"][_mv_at - 6:_mv_at + 1],
          ["close!", "new verify", "no_selection_filters",
           "box 0,0,0 20 20 10", "box 10,10,5 20 20 10",
           "select Box, Box001", "part_cut"])
    # A positional example is driven bare -- no fixture, no select -- but
    # in a scratch document of its own, so which fixture the command
    # before it built cannot change the answer.
    _mv_box = _mv_where("box 0,0,0 40 30 20")
    check("    a positional example is driven bare, in a fresh document",
          _mv_state["lines"][_mv_box - 3:_mv_box + 1],
          ["close!", "new verify", "no_selection_filters",
           "box 0,0,0 40 30 20"])
    check("    the panel example set its field and pressed done",
          [ln for ln in _mv_state["lines"]
           if ln in ("part_fillet", "filletstartradius=3", "done")],
          ["part_fillet", "filletstartradius=3", "done"])
    check("    a manual command was recorded and never run",
          "whats_this" in _mv_state["lines"], False)
    check("    the ledger carries the version it was verified against",
          {e["freecad"] for e in _mv_ledger["commands"].values()}, {"9.9.9"})
    check("  and a second run has nothing left to do",
          (_mv_again, _mv_after - _mv_before), (0, 0))

    # The checkpoint, from outside: a sweep stopped mid-way keeps every
    # result it had recorded, and the run after it picks up exactly what is
    # missing. #54's "resumable" as a check rather than a claim.
    _in_lines = []

    def _in_fccli(stop):
        def call(*args, **kw):
            if args[0] == "ls":
                return 0, "[]", ""
            if args[0] == "--json":
                return 0, _json.dumps(
                    {"engine": "idle", "options": [], "panel": False,
                     "documents": [{"active": True, "invalid": []}]}), ""
            if args[0] != "exec":
                return 0, "", ""
            if args[1] == stop:
                raise KeyboardInterrupt
            _in_lines.append(args[1])
            return 0, "", ""
        return call
    _in_dict = {"freecad": "9.9.9", "commands": {
        "Part_Box": {"example": "box 1 1 1"},
        "Part_Cut": {"example": "select Box, Box001; part_cut"},
        "Std_Whatsthis": {"example": "whats_this"},
        "Zed_Last": {"example": "zed"},
    }}
    _in_map = {"commands": {
        "Part_Box": {"mode": "positional"},
        "Part_Cut": {"mode": "selection", "selection_hint": "two shapes"},
        "Std_Whatsthis": {"mode": "manual"},
        "Zed_Last": {"mode": "positional"},
    }}
    _in_old = (_verify.DICT, _verify.MODEMAP, _verify.LEDGER, _verify.fccli)
    with tempfile.TemporaryDirectory() as _in_dir:
        try:
            _verify.DICT = os.path.join(_in_dir, "dictionary.json")
            _verify.MODEMAP = os.path.join(_in_dir, "modemap.json")
            _verify.LEDGER = os.path.join(_in_dir, "verified.json")
            _json.dump(_in_dict, open(_verify.DICT, "w"))
            _json.dump(_in_map, open(_verify.MODEMAP, "w"))
            _verify.fccli = _in_fccli("zed")     # stop on the last command
            try:
                _in_code = _verify.main([])
            except KeyboardInterrupt:
                _in_code = "raised out of main"

            def _in_read():
                if not os.path.exists(_verify.LEDGER):
                    return []            # nothing checkpointed at all
                return sorted(_json.load(open(_verify.LEDGER))["commands"])
            _in_part = _in_read()
            _verify.fccli = _in_fccli("never")   # and resume
            _in_lines.clear()
            _in_code2 = _verify.main([])
            _in_whole = _in_read()
            _in_after = list(_in_lines)
        finally:
            (_verify.DICT, _verify.MODEMAP, _verify.LEDGER,
             _verify.fccli) = _in_old
    check("  a sweep stopped mid-way keeps every result it had",
          (_in_code, _in_part),
          (130, ["Part_Box", "Part_Cut", "Std_Whatsthis"]))
    check("    and the run after it finishes the one that was missing",
          (_in_code2, _in_whole),
          (0, ["Part_Box", "Part_Cut", "Std_Whatsthis", "Zed_Last"]))
    check("      running only that one, not the three already answered",
          [ln for ln in _in_after if ln not in _verify.PREPARE],
          ["zed"])

    # GH #72. A token that will not parse at a step but does match a verb
    # cancels the command and runs that verb instead. When the verb it
    # escapes to takes no steps, the line exits 0 with the engine idle and
    # nothing invalid, and every reading `classify` makes says the command
    # verified. The engine's own word for what it dropped is the only thing
    # that says otherwise.
    check("  the engine's word for a command it abandoned mid-line",
          (_verify.cancelled_in("loft cancelled\n= standard_views"),
           _verify.cancelled_in("= loft 5.00mm Wire,Wire001"),
           _verify.cancelled_in("cancelled")),
          ("loft", "", ""))
    _vc_snap = {"engine": "idle", "options": [], "panel": False,
                "documents": [{"active": True, "invalid": []}]}

    def _vc_fccli(*args, **kw):
        if args[0] == "--json":
            return 0, _json.dumps(_vc_snap), ""
        if args[0] == "exec" and args[1] == "loft standard":
            return 0, "loft cancelled\n= standard_views", ""
        if args[0] == "exec" and args[1] == "loft busy":
            return 75, "loft cancelled\n= standard_views", ""
        return 0, "", ""
    _vc_old = _verify.fccli
    try:
        _verify.fccli = _vc_fccli
        _vc_ok = _verify.verify_one("loft 5")
        _vc_gone = _verify.verify_one("loft standard")
        _vc_busy = _verify.verify_one("loft busy")
    finally:
        _verify.fccli = _vc_old
    check("    a line that abandoned its command is not a pass",
          (_vc_ok[0], _vc_gone[0]), ("ok", "cancelled"))
    check("      and the detail names what was abandoned",
          "cancelled loft" in _vc_gone[1], True)
    # `busy` outranks it: a floor held elsewhere means nothing of the line
    # ran, so there is nothing to say it abandoned (PR #75 review, 6).
    check("      but a held floor stays busy, cancelled line or not",
          _vc_busy[0], "busy")

    # The tally the campaign is measured by. One number says how much is
    # verified; the two-way one says what kind of verification it is.
    check("  the ledger counts by mode and result, in ADR-501's mode order",
          _verify.by_mode({
              "A": {"mode": "panel", "result": "ok"},
              "B": {"mode": "positional", "result": "ok"},
              "C": {"mode": "positional", "result": "ok"},
              "D": {"mode": "selection", "result": "invalid"},
              "E": {"mode": "manual", "result": "manual"},
              "F": {"result": "ok"}}),
          [f"{'positional':11} {'ok':11} 2",
           f"{'selection':11} {'invalid':11} 1",
           f"{'panel':11} {'ok':11} 1",
           f"{'-':11} {'ok':11} 1",
           f"{'manual':11} {'manual':11} 1"])

    # sweep() carries what a tier learned beyond its verdict, and a tier
    # with nothing extra to say keeps the shorter contract.
    _px_events = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b"},
        lambda cid, ex, res, det, extra=None:
            _px_events.append((cid, res, extra)),
        run_one=lambda cid, e: ("ok", "", {"fields": ["radius"]}) if e == "a"
        else ("ok", ""),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True)
    check("  what a tier learned reaches the record; two values still work",
          _px_events,
          [("A_A", "ok", {"fields": ["radius"]}), ("B_B", "ok", None)])
    # A bounded instance lifetime. A long-lived one degrades quietly, so
    # a reading that is meant to be reproducible asks for a fresh one
    # every N commands -- and never a pointless one after the last.
    _re_ran, _re_restarts = [], []
    _verify.sweep(
        {"A_A": "a", "B_B": "b", "C_C": "c", "D_D": "d"},
        lambda cid, ex, res, det, extra=None: _re_ran.append(cid),
        run_one=lambda cid, e: ("ok", ""),
        alive=lambda: True, healthy=lambda: True,
        restart=lambda: _re_restarts.append(len(_re_ran)) or True,
        restart_every=2)
    check("  a bounded lifetime restarts every N commands, not after the last",
          (_re_ran, _re_restarts), (["A_A", "B_B", "C_C", "D_D"], [2]))
    check("    and with no bound, never",
          _verify.sweep({"A_A": "a", "B_B": "b"},
                        lambda cid, ex, res, det, extra=None: None,
                        run_one=lambda cid, e: ("ok", ""), alive=lambda: True,
                        healthy=lambda: True,
                        restart=lambda: False)[2], 0)
    check("      a restart that fails between commands stops the sweep",
          _verify.sweep({"A_A": "a", "B_B": "b"},
                        lambda cid, ex, res, det, extra=None: None,
                        run_one=lambda cid, e: ("ok", ""), alive=lambda: True,
                        healthy=lambda: True, restart=lambda: False,
                        restart_every=1)[1],
          False)

    # Which command this instance ran before a failure. A result a rerun
    # on a fresh instance passes was broken by something, and the sweep
    # has the ordering, so it can name the suspect rather than leaving
    # "the instance was old" standing (PR #70 review).
    _af_seen = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b", "C_C": "c"},
        lambda cid, ex, res, det, extra=None:
            _af_seen.append((cid, res, (extra or {}).get("after", "-"))),
        run_one=lambda cid, e: ("broken", "no") if e == "b" else ("ok", ""),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True)
    check("  a failure records the command this instance ran before it",
          _af_seen,
          [("A_A", "ok", "-"), ("B_B", "broken", "A_A"), ("C_C", "ok", "-")])
    # A restart makes a fresh instance, so nothing precedes the command
    # after one. Something has to precede the hazard for that to be
    # visible at all -- with the hazard first, `previous` is None either
    # way and dropping the reset costs nothing.
    _af_seen2 = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b", "C_C": "c"},
        lambda cid, ex, res, det, extra=None:
            _af_seen2.append((cid, res, (extra or {}).get("after", "-"))),
        run_one=lambda cid, e: ("ok", "") if e == "a"
        else ("hazard", "died") if e == "b" else ("broken", "no"),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True)
    check("    a restart clears it: nothing precedes the command after one",
          _af_seen2,
          [("A_A", "ok", "-"), ("B_B", "hazard", "A_A"),
           ("C_C", "broken", None)])
    # And the same for the other door a restart comes through: a fixture
    # that failed because the instance had died.
    _af_health = iter([True, False, True])
    _af_seen2b = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b", "C_C": "c"},
        lambda cid, ex, res, det, extra=None:
            _af_seen2b.append((cid, res, (extra or {}).get("after", "-"))),
        run_one=lambda cid, e: ("ok", "") if e == "a" else ("broken", "no"),
        alive=lambda: True, healthy=lambda: next(_af_health),
        restart=lambda: True,
        setup=lambda cid: (False, "no instance") if cid == "B_B"
        else (True, ""))
    check("      including a restart a dead instance's fixture triggered",
          _af_seen2b,
          [("A_A", "ok", "-"), ("B_B", "hazard", "A_A"),
           ("C_C", "broken", None)])
    # A fixture that would not build still ran its recipe against the
    # instance, so it is what preceded whatever comes next.
    _af_seen3 = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b"},
        lambda cid, ex, res, det, extra=None:
            _af_seen3.append((cid, res, (extra or {}).get("after", "-"))),
        run_one=lambda cid, e: ("broken", "no"),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True,
        setup=lambda cid: (False, "no Wire") if cid == "A_A" else (True, ""))
    check("      a recipe that failed still counts as having run",
          _af_seen3,
          [("A_A", "no_fixture", None), ("B_B", "broken", "A_A")])
    _af_seen4 = []
    _verify.sweep(
        {"A_A": "a", "B_B": "b"},
        lambda cid, ex, res, det, extra=None:
            _af_seen4.append((cid, res, (extra or {}).get("after", "-"))),
        run_one=lambda cid, e: ("broken", "no"),
        alive=lambda: True, healthy=lambda: True, restart=lambda: True,
        restart_every=1)
    check("      and a scheduled restart clears it too",
          _af_seen4, [("A_A", "broken", None), ("B_B", "broken", None)])

    # An instance that never came up and one too old to answer are two
    # different things, and used to share one message.
    check("  no answer from the instance says so, and points at the start",
          _verify.precondition({}),
          "no answer from the instance -- it may not have come up; "
          "`fccli ls` says what is running")
    check("    an answer without panel facts is the old addon",
          _verify.precondition({"engine": "idle"}),
          "this FreeCAD predates ADR-302 and cannot report panel or "
          "validity facts -- restart it with the current addon")
    check("    and an answer with them is no obstacle",
          _verify.precondition({"engine": "idle", "panel": False}), None)

    # An instance with a panel stuck across it is no more fit to judge the
    # next command than a dead one, so the sweep restarts on that too.
    _px_events2, _px_restarts = [], []
    _px_tally, _px_fin, _px_n = _verify.sweep(
        {"C_C": "c", "D_D": "d"},
        lambda cid, ex, res, det, extra=None:
            _px_events2.append((cid, res)),
        run_one=lambda cid, e: ("stuck_panel", "would not close") if e == "c"
        else ("ok", ""),
        alive=lambda: True, healthy=lambda: True,
        restart=lambda: _px_restarts.append(1) or True)
    check("  a stuck panel restarts the instance and the sweep goes on",
          (_px_events2, len(_px_restarts), _px_n, _px_fin),
          ([("C_C", "stuck_panel"), ("D_D", "ok")], 1, 1, True))
    _px_events3, _px_restarts3 = [], []
    _verify.sweep(
        {"F_F": "f", "G_G": "g"},
        lambda cid, ex, res, det, extra=None: _px_events3.append((cid, res)),
        run_one=lambda cid, e: ("blocked", "a panel would not close")
        if e == "f" else ("ok", ""),
        alive=lambda: True, healthy=lambda: True,
        restart=lambda: _px_restarts3.append(1) or True)
    check("    and so does a command one of them blocked",
          (_px_events3, len(_px_restarts3)),
          ([("F_F", "blocked"), ("G_G", "ok")], 1))
    check("    and a restart that fails stops the sweep there",
          _verify.sweep({"E_E": "e"},
                        lambda cid, ex, res, det, extra=None: None,
                        run_one=lambda cid, e: ("stuck_panel", "would not close"),
                        alive=lambda: True, healthy=lambda: True,
                        restart=lambda: False)[1],
          False)

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

    print("\n5ad2. man carries the page and the example to the typed verb")
    # GH #38 and GH #44, one lookup gap between them: a tier-1 verb is
    # built from the type and never saw the linked command's file, so
    # `man cylinder` had no DESCRIPTION and could have no EXAMPLE.
    import json as _mjson
    from fccli import ledger as _ledger_mod

    def _man(topic):
        _seen_man.clear()
        _eng.submit(f"man {topic}")
        return [(m.text, m.data.get("role", "")) for m in _seen_man
                if m.kind == _INFO]

    def _section(rows, head):
        """The lines under a heading, up to the next heading."""
        out, taking = [], False
        for text, role in rows:
            if role == "head":
                taking = text == head
                continue
            if taking:
                out.append(text.strip())
        return out

    _cyl = _man("cylinder")
    _heads = [t for t, r in _cyl if r == "head"]
    check("  a typed verb shows the linked command's page (GH #38)",
          ("DESCRIPTION" in _heads,
           any("parametric cylinder" in t for t, _ in _cyl)),
          (True, True))
    def _at(heads, name):
        """Where a heading sits, or -1. A missing heading is a result, not
        an exception: a check that raises takes the suite down with it and
        says nothing about the eight below."""
        return heads.index(name) if name in heads else -1
    check("  and its authored example, between ARGUMENTS and DESCRIPTION",
          (_section(_cyl, "EXAMPLE")[:1],
           _at(_heads, "EXAMPLE") - _at(_heads, "ARGUMENTS"),
           _at(_heads, "DESCRIPTION") - _at(_heads, "EXAMPLE")),
          (["cylinder 12 40"], 1, 1))
    # The stamp, joined from the ledger by command id (ADR-501).
    check("  with the sweep's date and FreeCAD version beside it",
          any(t.strip() == "verified 2026-08-26 on FreeCAD 1.1.3"
              for t, _ in _cyl), True)
    # A launcher the factory re-homed around the typed verb is the same
    # command, so it keeps the page -- and loses the example, which names
    # the other door.
    _other = next(v.name for v in REGISTRY._verbs.values()
                  if v.gui_command == "Part_Cylinder" and v.name != "cylinder")
    _qual = _man(_other)
    check("  the re-homed launcher keeps the page and drops the example",
          ([t for t, r in _qual if r == "head"].count("DESCRIPTION"),
           any(t == "EXAMPLE" for t, r in _qual if r == "head")),
          (1, False))
    # A verb with no authored example has no EXAMPLE section at all.
    check("  a verb with no example shows no EXAMPLE",
          (REGISTRY.get("fillet").example,
           any(t == "EXAMPLE" for t, r in _man("fillet") if r == "head")),
          ("", False))
    # A two-part selection example says whose objects it names.
    _loft = _man("loft")
    check("  a selection example keeps its select, and says it is a fixture's",
          (_section(_loft, "EXAMPLE")[:2],),
          (["select Wire, Wire001; loft 5",
            "the select names objects in the verifier's fixture."],))
    check("  a one-part example gets no such line",
          any("fixture" in t for t, _ in _cyl), False)
    # A result the sweep did not call ok is said outright, with its detail.
    _solve = _man("solve_assembly")
    check("  a broken result is stamped as broken, and warns",
          (_section(_solve, "EXAMPLE"),
           [r for t, r in _solve if "broken" in t]),
          (["solve_assembly", "2026-08-26 on FreeCAD 1.1.3: broken",
            "error: solve_assembly: is not available here"], ["warn"]))
    # Two ways the stamp is withheld: no entry, and an entry that drove a
    # different invocation. Both leave the example itself standing.
    _ledger_dir = tempfile.mkdtemp(prefix="fccli-ledger-")
    _ledger_path = os.path.join(_ledger_dir, "verified.json")
    with open(_ledger_path, "w") as _fh:
        _mjson.dump({"commands": {"Part_Cylinder": {
            "date": "2001-01-01", "freecad": "0.0.0", "mode": "positional",
            "example": "cylinder 1 2", "result": "ok"}}}, _fh)
    _real_ledger = _ledger_mod.LEDGER
    _ledger_mod.LEDGER = _ledger_path
    _ledger_mod.forget()
    _drift = _man("cylinder")
    _absent = _man("solve_assembly")
    _ledger_mod.LEDGER = _real_ledger
    _ledger_mod.forget()
    check("  a stamp for a different invocation is not shown for this one",
          (_section(_drift, "EXAMPLE"), any("2001" in t for t, _ in _drift)),
          (["cylinder 12 40"], False))
    check("  and a command the ledger never saw shows the example bare",
          _section(_absent, "EXAMPLE"), ["solve_assembly"])
    # A ledger that will not parse costs the stamps, not the pages.
    with open(_ledger_path, "w") as _fh:
        _fh.write("{not json")
    try:
        _torn = _ledger_mod._read(_ledger_path)
    except Exception as _exc:                                # noqa: BLE001
        _torn = repr(_exc)
    check("  a broken ledger is treated as absent", _torn, {})

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
        # ADR-301: a verb name matches by substring, so a name the factory
        # qualified behind a workbench prefix is reachable by its meaningful
        # word. REGISTRY here holds the tier-0 launchers, so part_cut exists.
        _cut_hits = _cand(_ceng, "cut", history=None)[2]
        check("  substring reaches a qualified verb by its middle word",
              "part_cut" in _cut_hits, True)
        _cut_pref = [c for c in _cut_hits if c.startswith("cut")]
        _cut_sub = [c for c in _cut_hits if not c.startswith("cut")]
        check("    prefix hits lead the substring-only ones",
              _cut_hits, _cut_pref + _cut_sub)
        check("    and a real prefix hit leads", "cutout_shape" in _cut_pref, True)
        check("  one character is prefix only",
              all(h.startswith("c") for h in _cand(_ceng, "c", history=None)[2]),
              True)
        check("    so a middle-word match needs two characters",
              "part_cut" in _cand(_ceng, "c", history=None)[2], False)
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

    print("\n5aj. a command file's type block tunes the tier-1 verb")
    # ADR-100 option A. patches/part.py is gone; the Part primitives'
    # tuning is a `type` block on each Part_* command file, and the two
    # with no command (Wedge, Helix) are in part/_types.yaml. Measured
    # against a run with no dictionary, so each check is the difference.
    _tb_bare = _Registry()
    register_all(_tb_bare, tier0=True, patches=PatchSet(), dictionary={})
    _tb = _Registry()
    register_all(_tb, tier0=True, patches=PatchSet())
    check("part.py is gone", os.path.exists(os.path.join(
          os.path.dirname(__file__), "..", "fccli", "patches", "part.py")), False)
    from fccli.factory import load_dictionary
    _dt = load_dictionary().get("types")
    # Sixty-one, read member by member: the sixteen ADR-100 and GH #52
    # left, plus the forty-five the GH #69 round authored -- the sixteen
    # PartDesign primitives and their eight base types, five base
    # feature types, the two patterns, Groove and Revolution, Mirrored,
    # Draft, the two lofts, the two pipes, Part's Ellipsoid and Prism,
    # Thickness, Offset, Offset2D and Extrusion.
    check("  the dictionary carries type tuning keyed by type",
          sorted(_dt),
          ["Part::Box", "Part::Cone", "Part::Cylinder",
           "Part::Ellipsoid", "Part::Extrusion", "Part::Helix",
           "Part::Offset", "Part::Offset2D", "Part::Prism",
           "Part::RuledSurface", "Part::Sphere", "Part::Thickness",
           "Part::Torus", "Part::Wedge",
           "PartDesign::AdditiveBox", "PartDesign::AdditiveCone",
           "PartDesign::AdditiveCylinder", "PartDesign::AdditiveEllipsoid",
           "PartDesign::AdditiveHelix", "PartDesign::AdditiveLoft",
           "PartDesign::AdditivePipe", "PartDesign::AdditivePrism",
           "PartDesign::AdditiveSphere", "PartDesign::AdditiveTorus",
           "PartDesign::AdditiveWedge", "PartDesign::Box",
           "PartDesign::Chamfer", "PartDesign::Cone",
           "PartDesign::Cylinder", "PartDesign::Draft",
           "PartDesign::Ellipsoid", "PartDesign::FeatureExtrude",
           "PartDesign::Fillet", "PartDesign::Groove",
           "PartDesign::Helix", "PartDesign::Hole",
           "PartDesign::LinearPattern", "PartDesign::Loft",
           "PartDesign::Mirrored", "PartDesign::Pad", "PartDesign::Pipe",
           "PartDesign::Pocket", "PartDesign::PolarPattern",
           "PartDesign::Prism", "PartDesign::ProfileBased",
           "PartDesign::Revolution", "PartDesign::Sphere",
           "PartDesign::SubtractiveBox", "PartDesign::SubtractiveCone",
           "PartDesign::SubtractiveCylinder",
           "PartDesign::SubtractiveEllipsoid",
           "PartDesign::SubtractiveHelix", "PartDesign::SubtractiveLoft",
           "PartDesign::SubtractivePipe", "PartDesign::SubtractivePrism",
           "PartDesign::SubtractiveSphere", "PartDesign::SubtractiveTorus",
           "PartDesign::SubtractiveWedge", "PartDesign::Thickness",
           "PartDesign::Torus", "PartDesign::Wedge"])
    check("  a type block names its command's type",
          _dt["Part::Cylinder"].get("of") is None
          and _dt["Part::Cylinder"]["steps"], ["Radius", "Height"])
    # The tuning reaches the verb: ordered, strict, aliased.
    _cyl = _tb.by_gui_command("Part_Cylinder") or _tb.get("cylinder")
    check("  cylinder is ordered and strict from its file",
          [st.id for st in _tb.get("cylinder").steps], ["Radius", "Height"])
    check("  and without the tree it is alphabetical and optional",
          [st.id for st in _tb_bare.get("cylinder").steps][:1], ["Angle"])
    check("  cyl reaches it", _tb.get("cyl") is _tb.get("cylinder"), True)
    # GH #69, the rest of the class. Each of these led with a tolerance or
    # a link before the round, so the leading number set something the
    # command is not about; each now leads with the property the wiki and
    # FreeCAD's own dialog name first.
    check("  a tuned verb leads with the parameter its command is about",
          [(_tb.get(n).steps[0].id if _tb.get(n) else None) for n in
           ("additive_box", "subtractive_cylinder", "additive_prism",
            "additive_wedge", "ellipsoid", "prism", "linear_pattern",
            "polar_pattern", "groove", "partdesign_revolution",
            "additive_loft", "additive_pipe", "mirrored", "thickness",
            "offset", "offset2_d", "extrusion", "partdesign_helix")],
          ["Length", "Radius", "Polygon", "Xmin", "Radius1", "Polygon",
           "Length", "Angle", "Angle", "Angle", "Profile", "Profile",
           "MirrorPlane", "Value", "Value", "Value", "LengthFwd", "Mode"])
    # And the invariant behind them: a boolean-operation tolerance is
    # never a step of a type somebody has tuned.
    check("    and no tuned type still asks for a tolerance",
          sorted(v.name for v in _tb._verbs.values()
                 if v.creates in _dt
                 and any("Tolerance" in st.id for st in v.steps)), [])
    check("  box keeps its bx alias, and helix its doc",
          (_tb.get("bx") is _tb.by_gui_command("Part_Box") or
           _tb.get("bx").creates == "Part::Box",
           _tb.get("helix").doc.startswith("Create a helix")), (True, True))
    # Part::Line has no skip now: against the full registry (hand-written
    # line included) it collides and re-homes rather than shadowing.
    check("  the hand-written line stays, Part::Line re-homes to part_line",
          (REGISTRY.get("line").gui_command,
           REGISTRY.get("part_line") and REGISTRY.get("part_line").creates),
          ("Draft_Line", "Part::Line"))
    # An orphan type, tuned from _types.yaml.
    check("  a type with no command is tuned from _types.yaml",
          [st.id for st in _tb.get("wedge").steps],
          ["Xmin", "Ymin", "Zmin", "Xmax", "Ymax", "Zmax"])
    # A type block's `of` must name a real type, and one type is tuned once.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import command_files as _cf2, lint_dictionary as _ld7
    _ttmp = tempfile.mkdtemp(prefix="fccli-type-")
    os.makedirs(os.path.join(_ttmp, "part"))
    _g = {k: _cmds["Part_Cylinder"].get(k) for k in ("label", "tooltip",
          "toolbar", "menu", "shortcut", "workbench", "wiki")}
    _g["freecad"] = _load_desc()["freecad"]
    with open(os.path.join(_ttmp, "part", "Part_Cylinder.md"), "w") as _fh:
        _fh.write(_cf2.render("Part_Cylinder", _g,
                              {"type": {"steps": ["Radius"]}}, "x"))
    _tn, _tp = _ld7.lint(_ttmp, _ld7.DESCRIPTOR, os.path.join(_ttmp, "none.json"))
    check("  a type block with no `of` is a lint error",
          any("needs `of`" in x for x in _tp), True)
    import shutil as _sh7; _sh7.rmtree(_ttmp, ignore_errors=True)
    # _types.yaml: a bad key and a non-mapping are compile errors; a type
    # tuned in both a command file and _types.yaml is one too.
    import compile_dictionary as _cd7
    _yt = tempfile.mkdtemp(prefix="fccli-yt-"); os.makedirs(os.path.join(_yt, "part"))
    _gc7 = {k: _cmds["Part_Cylinder"].get(k) for k in ("label", "tooltip",
            "toolbar", "menu", "shortcut", "workbench", "wiki")}
    _gc7["freecad"] = _load_desc()["freecad"]
    open(os.path.join(_yt, "part", "Part_Cylinder.md"), "w").write(
        _cf2.render("Part_Cylinder", _gc7, {}, "x"))
    open(os.path.join(_yt, "part", "_types.yaml"), "w").write(
        "types:\n  Part::Wedge:\n    stepz: [X]\n")
    _yerr = None
    try:
        _cd7.compile_tree(_yt)
    except ValueError as _e:
        _yerr = str(_e)
    check("  a bad _types.yaml key is a compile error",
          _yerr is not None and "stepz" in _yerr, True)
    _sh7.rmtree(_yt, ignore_errors=True)

    print("\n5ak. the socket retains the session as a message ring (ADR-302)")
    import json as _json
    from fccli import server as _srv
    from fccli.bus import Message as _Msg

    class _FakeObj:
        Name, Label, TypeId = "Fillet", "Fillet", "Part::Fillet"
        State = ["Touched", "Invalid", "Up-to-date"]

    _w = _srv.wire(_Msg(kind=RESULT, text="fillet 3",
                        data={"replay": "fillet 3", "object": _FakeObj()}))
    check("  RESULT carries what it made",
          (_w["object"]["name"], _w["object"]["type"]),
          ("Fillet", "Part::Fillet"))
    check("    with Up-to-date filtered from its state",
          _w["object"]["state"], ["Touched", "Invalid"])
    check("    and the whole payload crosses a wire",
          _json.loads(_json.dumps(_w))["object"]["state"],
          ["Touched", "Invalid"])
    check("    a verb that made nothing says so",
          _srv.wire(_Msg(kind=RESULT, text="x",
                         data={"object": None}))["object"], None)

    _rdir = tempfile.mkdtemp(prefix="fccli-ring-")
    _rpath = os.path.join(_rdir, "transcript.jsonl")
    _ring = _srv.Ring(limit=3, transcript=_rpath)
    for _i in range(5):
        _ring.append({"kind": "info", "text": f"line {_i}"})
    check("  the ring keeps the last N, seq monotonic",
          [e["seq"] for e in _ring.entries], [3, 4, 5])
    check("    what leaves the ring lands in the transcript",
          [_json.loads(_l)["seq"] for _l in open(_rpath)], [1, 2])
    check("    tail and since read without consuming",
          ([e["seq"] for e in _ring.tail(2)],
           [e["seq"] for e in _ring.since(4)],
           [e["seq"] for e in _ring.entries]),
          ([4, 5], [5], [3, 4, 5]))

    class _StubFloor:
        holder = None

    class _StubSession:
        floor = _StubFloor()

    _sv = _srv.Server(None)
    _sv.session = _StubSession()
    _sv.ring = _ring
    _sinfo = {"name": "client:1", "resume": "tok-a",
              "subscribed": False, "buffer": b""}
    _rep = _sv._dispatch(_sinfo, {"op": "replay", "last": 2})
    check("  op=replay reads the tail and moves no cursor",
          ([e["seq"] for e in _rep["entries"]], len(_sv._cursors)),
          ([4, 5], 0))
    _res = _sv._dispatch(_sinfo, {"op": "resume", "id": "tok-a"})
    check("    an unknown resume id gets everything, and says expired",
          (_res["expired"], [e["seq"] for e in _res["entries"]]),
          (True, [3, 4, 5]))
    _ring.append({"kind": "info", "text": "later"})
    _res2 = _sv._dispatch(_sinfo, {"op": "resume", "id": "tok-a"})
    check("    a known id replays only what it missed",
          (_res2["expired"], [e["seq"] for e in _res2["entries"]]),
          (False, [6]))
    for _i in range(_srv.RESUME_IDS + 5):
        _sv._advance(f"tok-{_i}", _i)
    check("    the cursor table stays capped, oldest out",
          (len(_sv._cursors), "tok-0" in _sv._cursors),
          (_srv.RESUME_IDS, False))

    print("\n5am. a line reports what it did, and does nothing else "
          "(GH #55, #72, #57)")
    # --- GH #55: an exact choice a longer one shadowed. `view iso` asked
    # again for the view it had just been given, because `iso` also starts
    # `isometric` and the matcher insists on one hit. A dry engine
    # resolves and parses exactly as the live one does and stops before
    # running FreeCAD's command, so this is the real `view` door with the
    # real choices from the tree on it.
    _dbus = Bus()
    _dvals, _derrs = [], []
    _dbus.subscribe(lambda m: _dvals.append(m.data.get("values"))
                    if m.kind == RESULT else None)
    _dbus.subscribe(lambda m: _derrs.append(m.text) if m.kind == ERROR else None)
    _deng = Engine(_dbus, REGISTRY, dry=True)
    _vstep = REGISTRY.get("view").steps[0].id
    _deng.submit("view iso")
    _deng.submit("view isometric")
    check("`view iso` reaches the choice it names, and iso is not isometric",
          ([v.get(_vstep) for v in _dvals], _deng.state, _derrs),
          (["iso", "isometric"], "idle", []))
    _deng.submit("view is")
    check("  a prefix two choices answer to is still ambiguous",
          (len([e for e in _derrs if "expected one of" in e]), _deng.state),
          (1, "collecting"))
    _deng.cancel()
    # The fault, put back: the matcher without its exact tier.
    import fccli.engine as _emod
    _old_mc = _emod.match_choice
    try:
        _emod.match_choice = lambda choices, text: [
            c for c in choices if c.lower().startswith(text.lower())]
        _dvals.clear(); _derrs.clear()
        _deng.submit("view iso")
        check("  and the prefix-only matcher put back makes it unreachable",
              (_dvals, len([e for e in _derrs if "expected one of" in e]),
               _deng.state), ([], 1, "collecting"))
    finally:
        _emod.match_choice = _old_mc
    _deng.cancel()

    # --- GH #72: a token that will not parse at a step used to cancel the
    # command and run the verb it named, inside one submitted line, and
    # the line reported the escape target's success as its own. Two verbs
    # of the shape that did it: `loft standard` ran `standard_views`.
    from fccli.grammar import (Registry as _R72, Step as _S72, Verb as _V72,
                               CHOICE as _CH72, SELECTION as _SEL72,
                               QUANTITY as _Q72, POINT as _P72)
    from fccli.bus import PROMPT as _PROMPT72
    _ran72 = []
    _reg72 = _R72()
    _reg72.add(_V72(name="loftish", transactional=False,
                    steps=[_S72(id="transition", kind=_CH72,
                                prompt="Transition",
                                choices=["transformed", "rotated"])],
                    emit=lambda v: _ran72.append("loftish")))
    _reg72.add(_V72(name="standard_views", steps=[], transactional=False,
                    emit=lambda v: _ran72.append("standard_views")))
    _bus72 = Bus()
    _msg72 = []
    _bus72.subscribe(lambda m: _msg72.append((m.kind, m.text)))
    _eng72 = Engine(_bus72, _reg72)
    _eng72.submit("loftish standard")
    check("a verb name mid-line is refused, and starts nothing",
          (_ran72, _eng72.state,
           _eng72.verb.name if _eng72.verb else None),
          ([], "collecting", "loftish"))
    check("  the refusal names the command it did not start, and the step",
          [t for k, t in _msg72 if k == ERROR],
          ["'standard' is the command 'standard_views', and a command does "
           "not start inside a line -- loftish is still asking for "
           "Transition"])
    check("  and nothing was cancelled",
          [t for k, t in _msg72 if "cancelled" in t], [])
    # The same token at a prompt is the interactive escape, which stays:
    # a person typing a new verb to abandon the one they are in the middle
    # of sees the switch happen and can undo it.
    _msg72.clear()
    _eng72.submit("standard")
    check("  the same token at a prompt still abandons and starts",
          (_ran72, _eng72.state,
           [t for k, t in _msg72 if k == "info"]),
          (["standard_views"], "idle", ["loftish cancelled"]))
    # The two doors are two functions, and the prompt one is the one that
    # escapes: fed the same token at the same step of the same command,
    # `_feed_text` restarts where `_start`'s own walk refuses.
    _ran72.clear(); _msg72.clear()
    _eng72.submit("loftish")
    _eng72._feed_text("standard", step=_eng72.current_step())
    check("  the prompt door, called directly, still escapes",
          (_ran72, [t for k, t in _msg72 if "cancelled" in t]),
          (["standard_views"], ["loftish cancelled"]))
    # A refused line stops where it was refused. The tokens after the bad
    # one were answers to the command it refused, and a verb that learned
    # its steps by starting runs as soon as any value lands -- which is
    # how `loft standard` came back live as a loft with no sections in it
    # and an invalid Loft in the document.
    _ran72b = []
    _reg72.add(_V72(name="paneled", steps=[], transactional=False,
                    open=lambda eng: [
                        _S72(id="sections", kind=_CH72, prompt="Sections",
                             choices=["one", "two"]),
                        _S72(id="transition", kind=_CH72,
                             prompt="Transition",
                             choices=["transformed", "rotated"])],
                    emit=lambda v: _ran72b.append("paneled")))
    _msg72.clear()
    _eng72.submit("paneled one transformed")
    check("  a verb that learned its steps runs on the values it was given",
          (_ran72b, _eng72.state), (["paneled"], "idle"))
    _ran72b.clear(); _msg72.clear()
    _eng72.submit("paneled standard one")
    check("  but a refused token stops the line before anything runs",
          (_ran72b, _eng72.state, _eng72.values,
           len([t for k, t in _msg72 if k == ERROR])),
          ([], "collecting", {}, 1))
    _eng72.cancel()
    # The error and the prompt under it are one reply, so they have to
    # agree, and reading only the errors is how a disagreement hid. The
    # message named the step the token was *aimed at* while `_announce`
    # reported the pending one, and a selection step fills itself from
    # what is already selected -- so live, `loft standard` answered "still
    # asking for List of sections" over "still wants Maximum Degree".
    # Worse, that adoption runs a verb whose only step is the selection:
    # the line is refused and the command happens anyway.
    _seldoc72 = App.newDocument("refused72")
    _selobj72 = _seldoc72.addObject("Part::Box", "Widget")
    _seldoc72.recompute()

    class _Sel72:
        def getSelection(self):
            return [_selobj72]

    class _Gui72:
        Selection = _Sel72()

    _reg72.add(_V72(name="tally", transactional=False,
                    steps=[_S72(id="objects", kind=_SEL72,
                                prompt="What to count"),
                           _S72(id="times", kind=_Q72, prompt="How many")],
                    emit=lambda v: _ran72b.append("tally")))
    _reg72.add(_V72(name="zap", transactional=False,
                    steps=[_S72(id="objects", kind=_SEL72,
                                prompt="What to zap")],
                    emit=lambda v: _ran72b.append("zap")))
    _reply72 = []
    _stop72 = _bus72.subscribe(
        lambda m: _reply72.append(m.text)
        if m.kind in (ERROR, _PROMPT72) else None)
    _real_gui72 = sys.modules.get("FreeCADGui")
    sys.modules["FreeCADGui"] = _Gui72()
    try:
        _ran72b.clear(); _reply72.clear()
        _eng72.submit("tally standard")
        check("  the refusal and the prompt under it name the same step",
              _reply72,
              ["'standard' is the command 'standard_views', and a command "
               "does not start inside a line -- tally is still asking for "
               "What to count",
               "What to count"])
        check("    and what was selected was not adopted on the way out",
              (_eng72.state, _eng72.values, _ran72b),
              ("collecting", {}, []))
        _eng72.cancel()
        _ran72b.clear(); _reply72.clear()
        _eng72.submit("zap standard")
        check("  a refused line does not run the verb on what was selected",
              (_ran72b, _eng72.state), ([], "collecting"))
        _eng72.cancel()
        _ran72b.clear()
        _eng72.submit("zap")
        check("    while a line nobody refused still fills it from the "
              "selection", (_ran72b, _eng72.state), (["zap"], "idle"))
        # The other way the two lines can disagree, with no selection in
        # it: a token is aimed at the step whose *kind* it matches, so
        # `r1` reads as a relative point and is judged against the point
        # step, while the choice step is what the command is still asking
        # for. The step judged and the step announced are two questions.
        _reg72.add(_V72(name="r1x", steps=[], transactional=False,
                        emit=lambda v: _ran72b.append("r1x")))
        _reg72.add(_V72(name="aimed", transactional=False,
                        steps=[_S72(id="mode", kind=_CH72,
                                    prompt="Which mode",
                                    choices=["fast", "slow"]),
                               _S72(id="where", kind=_P72, prompt="Where")],
                        emit=lambda v: _ran72b.append("aimed")))
        _ran72b.clear(); _reply72.clear()
        _eng72.submit("aimed r1")
        check("  a token aimed past the head names the step being asked for",
              _reply72,
              ["'r1' is the command 'r1x', and a command does not start "
               "inside a line -- aimed is still asking for Which mode",
               "Which mode"])
        check("    and nothing ran", (_ran72b, _eng72.state),
              ([], "collecting"))
        _eng72.cancel()
    finally:
        _stop72()
        if _real_gui72 is None:
            sys.modules.pop("FreeCADGui", None)
        else:
            sys.modules["FreeCADGui"] = _real_gui72
    App.closeDocument(_seldoc72.Name)

    # --- GH #57: a command that ran to completion over an object FreeCAD
    # computed and rejected reported success and said nothing. A Part::Cut
    # with no operands is the smallest thing FreeCAD marks Invalid.
    _doc57 = App.newDocument("rejected")

    def _cut57(_v):
        obj = _doc57.addObject("Part::Cut", "Cut")
        _doc57.recompute()
        return obj

    def _box57(_v):
        obj = _doc57.addObject("Part::Box", "Box")
        _doc57.recompute()
        return obj

    _reg57 = _R72()
    _reg57.add(_V72(name="goodbox", steps=[], emit=_box57))
    _reg57.add(_V72(name="badcut", steps=[], emit=_cut57))
    _bus57 = Bus()
    _msg57 = []
    _bus57.subscribe(lambda m: _msg57.append((m.kind, m.text)))
    _eng57 = Engine(_bus57, _reg57)
    _eng57.submit("goodbox")
    check("a command whose object computes clean reports only the result",
          ([t for k, t in _msg57 if k == RESULT],
           [t for k, t in _msg57 if k == ERROR]), (["goodbox"], []))
    _msg57.clear()
    _eng57.submit("badcut")
    check("a command that left an object FreeCAD rejected says so",
          [t for k, t in _msg57 if k == ERROR],
          ["badcut: FreeCAD computed Cut and marked it invalid -- "
           "the command ran, the result is not usable"])
    check("  and the result stands beside it, the line having run",
          [t for k, t in _msg57 if k == RESULT], ["badcut"])
    # The delta, which is what makes the reading fair: one bad object does
    # not make every line after it a failure.
    _msg57.clear()
    _eng57.submit("goodbox")
    check("  a later clean line is not charged with what it found",
          [t for k, t in _msg57 if k == ERROR], [])
    _msg57.clear()
    _eng57.submit("badcut")
    check("  and a second one is charged with its own",
          [t for k, t in _msg57 if k == ERROR],
          ["badcut: FreeCAD computed Cut001 and marked it invalid -- "
           "the command ran, the result is not usable"])
    # A verb that switched documents leaves nothing to compare against.
    # The document it switched *to* has two invalid objects in it by now,
    # and they have been there since before this line was typed -- so a
    # reading that ignored which document it was in would charge a verb
    # that made nothing with both of them.
    _other57 = App.newDocument("other57")
    _reg57.add(_V72(name="goback", steps=[], transactional=False,
                    emit=lambda v: App.setActiveDocument(_doc57.Name)))
    _msg57.clear()
    _eng57.submit("goback")
    check("  a line that switched documents is charged with neither's",
          ([t for k, t in _msg57 if k == ERROR], App.ActiveDocument.Name),
          ([], _doc57.Name))
    App.closeDocument(_other57.Name)
    App.closeDocument(_doc57.Name)

    print("\n5an. a count reaches the object, and the prompt says only what "
          "the step takes (GH #78, #56, #71)")
    from fccli.grammar import (Option as _O78, Step as _St78, Verb as _V78,
                               Registry as _R78, QUANTITY as _Q78,
                               TEXT as _T78, whole_number as _whole)
    from fccli import factory as _f78, panels as _p78, properties as _pr78
    from fccli import units as _u78

    # --- GH #78, the reading. Every number this program parses is a float
    # and FreeCAD's integer setter refuses one, so the two are told apart
    # in one place and both callers ask it.
    check("a whole number is the integer it stands for",
          [_whole(v) for v in (4, 4.0, -3.0, 0.0, 1e-12)],
          [4, 4, -3, 0, 0])
    check("  and a fraction stands for no integer",
          [_whole(v) for v in (4.5, 0.1, -2.25, "no", None)],
          [None, None, None, None, None])
    check("  a conversion's last few ulps are still whole",
          _whole(float(4 * 25.4) / 25.4), 4)
    check("the counting property types are the scalar ones",
          (_pr78.counts("App::PropertyInteger"),
           _pr78.counts("App::PropertyIntegerConstraint"),
           _pr78.counts("App::PropertyIntegerList"),
           _pr78.counts("App::PropertyLength")),
          (True, True, False, False))

    # --- GH #78, the step. A count is in nothing, so a bare number takes
    # no unit from the schema, and a fraction is refused before an object
    # exists to carry the wrong number.
    _int_param = {"name": "Occurrences", "kind": "quantity",
                  "doc": "How many", "property_type": "App::PropertyInteger"}
    _len_param = {"name": "Length", "kind": "quantity", "doc": "How long",
                  "property_type": "App::PropertyLength", "unit": "mm"}
    _int_step = _f78._step_from_param(_int_param)
    check("a step over an integer property counts and is in nothing",
          (_int_step.integral, _int_step.unit), (True, ""))
    check("  and one over a length is unchanged",
          (_f78._step_from_param(_len_param).integral,
           _f78._step_from_param(_len_param).unit), (False, "mm"))

    _reg78 = _R78()
    _made78 = {}
    _reg78.add(_V78(name="pattern", transactional=False,
                    steps=[_f78._step_from_param(_len_param),
                           _f78._step_from_param(_int_param)],
                    emit=lambda v: _made78.update(v) or None))
    _bus78 = Bus()
    _msg78 = []
    _bus78.subscribe(lambda m: _msg78.append((m.kind, m.text)))
    _eng78 = Engine(_bus78, _reg78)
    _eng78.submit("pattern 100 4")
    check("a count typed at the step arrives as an int, not a float",
          (_made78.get("Occurrences"), type(_made78.get("Occurrences")).__name__),
          (4, "int"))
    check("  and echoes back without a unit, so the line replays",
          [t for k, t in _msg78 if k == RESULT], ["pattern 100.00mm 4"])
    _msg78.clear()
    _made78.clear()
    _eng78.submit("pattern 100 4.5")
    check("  a fraction at a count is refused at the prompt",
          ([t for k, t in _msg78 if k == ERROR], _eng78.state, _made78),
          (["Occurrences counts -- 4.5 is not a whole number"],
           "collecting", {}))
    # And the line stops there rather than running without it. Every step
    # the factory generates is optional, so `_only_optional_left` found
    # nothing outstanding and ran the command with the refused count
    # simply absent -- the fraction reported and a pattern of two built.
    check("    and the line it was on stops rather than running short",
          ([t for k, t in _msg78 if k == RESULT],
           getattr(_eng78.current_step(), "id", None)), ([], "Occurrences"))
    _eng78.cancel()
    # And it is refused because the *step* counts, not because 4.5 is odd:
    # the same value at the length lands.
    _msg78.clear()
    _made78.clear()
    _eng78.submit("pattern 4.5 4")
    check("    while the same fraction at a measurement lands",
          ([t for k, t in _msg78 if k == ERROR], _made78.get("Length")),
          ([], 4.5))

    # The schema is what made the unit matter. `parse_quantity` appends the
    # preferred length to a bare number, so under ImperialBuilding a typed
    # 4 was 4in -- 101.6 -- and no rounding could turn that back into four
    # instances.
    _was78 = _u78.current_name()
    _u78.set_schema("ImperialBuilding")
    try:
        _made78.clear()
        _eng78.submit("pattern 100 4")
        check("  a count is a count under a schema that is not millimetres",
              (_made78.get("Occurrences"), _u78.preferred("length")), (4, "in"))
        # The fault, put back: the factory's mm default over a count.
        _old_counts = _f78.counts
        try:
            _f78.counts = lambda ptype: False
            _mm_step = _f78._step_from_param(_int_param)
            _reg78.add(_V78(name="unpatterned", transactional=False,
                            steps=[_f78._step_from_param(_len_param), _mm_step],
                            emit=lambda v: _made78.update(v) or None))
            _made78.clear()
            _msg78.clear()
            _eng78.submit("unpatterned 100 4")
            check("    and the mm default put back makes four into 101.6",
                  (_mm_step.unit, _made78.get("Occurrences")), ("mm", 101.6))
        finally:
            _f78.counts = _old_counts
    finally:
        _u78.set_schema(_was78)

    # --- GH #78, the write. The swallow made a property FreeCAD refused
    # indistinguishable from one it took.
    _doc78 = App.newDocument("counts78")
    _emit78 = _f78._emit_type(
        "PartDesign::LinearPattern",
        [{"name": "Occurrences", "kind": "quantity",
          "property_type": "App::PropertyInteger"},
         {"name": "Length", "kind": "quantity",
          "property_type": "App::PropertyLength", "unit": "mm"}])
    _msg78.clear()
    _obj78 = _emit78({"Occurrences": 4.0, "Length": 100.0,
                      "_flags": {}, "_engine": _eng78})
    check("the write coerces a whole float onto an integer property",
          (_obj78.Occurrences, [t for k, t in _msg78 if k == ERROR]), (4, []))
    _bad78 = _f78._emit_type(
        "Part::Cylinder",
        [{"name": "Radius", "kind": "quantity",
          "property_type": "App::PropertyLength", "unit": "mm"},
         {"name": "NoSuchProperty", "kind": "quantity",
          "property_type": "App::PropertyLength", "unit": "mm"}])
    _msg78.clear()
    _cyl78 = _bad78({"Radius": 7.0, "NoSuchProperty": 3.0,
                     "_flags": {}, "_engine": _eng78})
    _said78 = [t for k, t in _msg78 if k == ERROR]
    check("  a write FreeCAD refuses is said out loud, not swallowed",
          (len(_said78), ["NoSuchProperty" in t for t in _said78]),
          (1, [True]))
    check("    and costs only itself -- the rest of the line landed",
          (float(_cyl78.Radius),
           ["the rest of the line landed" in t for t in _said78]),
          (7.0, [True]))
    _msg78.clear()
    _frac78 = _emit78({"Occurrences": 4.5, "Length": 100.0,
                       "_flags": {}, "_engine": _eng78})
    check("  a fraction that reached the write is refused, never truncated",
          (_frac78.Occurrences, [t for k, t in _msg78 if k == ERROR]),
          (2, [f"{_frac78.Name}: Occurrences counts, and 4.5 is not a whole "
               "number -- the rest of the line landed"]))
    # The fault, put back: the bare `except Exception: pass`.
    _old_report = _f78._report_refused
    try:
        _f78._report_refused = lambda engine, obj, refused: None
        _quiet78 = _f78._emit_type(
            "Part::Cylinder",
            [{"name": "NoSuchProperty", "kind": "quantity",
              "property_type": "App::PropertyLength", "unit": "mm"}])
        _msg78.clear()
        _quiet78({"NoSuchProperty": 3.0, "_flags": {}, "_engine": _eng78})
        check("    and the swallow put back says nothing at all",
              [t for k, t in _msg78 if k == ERROR], [])
    finally:
        _f78._report_refused = _old_report
    App.closeDocument(_doc78.Name)

    # --- GH #56. One bracket held two meanings, and on a height step the
    # settable one read as a hint about the height.
    _hint_step = _St78("Height", _Q78, "The height of the cylinder")
    check("a step with nothing on it renders no tail",
          _hint_step.prompt_hint(), "")
    _hint_step.options = [_O78("Angle", "the sweep", None, sets=True)]
    check("a property the command will also set is named after the prompt",
          _hint_step.prompt_hint(), "  ·  also angle")
    _hint_step.options = [_O78("Close", "close the wire", None),
                          _O78("Undo", "drop the last point", None)]
    check("  what you may type instead of answering keeps the bracket",
          _hint_step.prompt_hint(), " [Close/Undo]")
    _hint_step.options = [_O78("Close", "", None),
                          _O78("Angle", "", None, sets=True),
                          _O78("Growth", "", None, sets=True)]
    check("  and a step with both keeps them apart",
          _hint_step.prompt_hint(), " [Close]  ·  also angle, growth")
    check("    while `options` stays the whole pool, for completion",
          _hint_step.option_names(), ["Close", "Angle", "Growth"])
    # The verb the issue was found on, through the real tree.
    _cyl_verb = REGISTRY.get("cylinder")
    _cyl_height = [s for s in _cyl_verb.steps if s.id == "Height"][0]
    check("the cylinder's height no longer reads as an angle",
          f"{_cyl_height.prompt}{_cyl_height.prompt_hint()}: ",
          "The height of the cylinder  ·  also angle: ")

    # Both renderers read the composed hint rather than joining the names,
    # so the dock and the socket cannot drift apart.
    _hint_seen = []
    _bus56 = Bus()
    _bus56.subscribe(lambda m: _hint_seen.append(m.data.get("hint"))
                     if m.kind == PROMPT else None)
    _reg56 = _R78()
    _step56 = _St78("Height", _Q78, "The height of the cylinder",
                    options=[_O78("Angle", "the sweep", None, sets=True)])
    _reg56.add(_V78(name="cyl56", steps=[_step56], transactional=False,
                    emit=lambda v: None))
    Engine(_bus56, _reg56).submit("cyl56")
    check("  the prompt message carries it composed",
          _hint_seen, ["  ·  also angle"])

    # --- GH #71. The panel's own instruction line named a word the step
    # would not take: `cancel` was read as a failed assignment and the
    # panel stayed up.
    _panel_step = _p78.steps_from([])[0]
    check("a panel step offers both words its instruction line names",
          _panel_step.option_names(), ["done", "cancel"])
    check("  and every word in either sentence is one of them",
          sorted({w for w in ("done", "cancel")
                  if w in _p78.OFFER and w in _p78.WAYS_OUT}),
          ["cancel", "done"])
    check("  the refusal names the way out rather than half of it",
          _p78._assign(None, _panel_step, "justaword"),
          "'justaword' is not an assignment -- name=value, `done` to apply, "
          "or `cancel` to abandon")

    _bus71 = Bus()
    _msg71 = []
    _bus71.subscribe(lambda m: _msg71.append((m.kind, m.text, m.data)))
    _reg71 = _R78()
    _aborted71 = []
    _reg71.add(_V78(name="fillet71", steps=[], transactional=False,
                    open=lambda e: (e.flags.__setitem__("panel", True)
                                    or _p78.steps_from([])),
                    abort=lambda e: _aborted71.append(True),
                    emit=lambda v: _aborted71.append("committed")))
    _eng71 = Engine(_bus71, _reg71)
    _eng71.submit("fillet71")
    check("the panel step is what the engine is asking for",
          (_eng71.state, _eng71.current_step().id), ("collecting", "set"))
    _msg71.clear()
    _eng71.submit("cancel")
    check("  a typed `cancel` abandons the panel, as the line promised",
          (_eng71.state, _aborted71, [t for k, t, _ in _msg71 if k == ERROR]),
          ("idle", [True], []))
    check("    and says so once, not twice",
          ([t for k, t, _ in _msg71 if k == INFO],
           len([d for k, _, d in _msg71 if k == PROMPT])),
          (["fillet71 cancelled"], 1))
    check("    with nothing recorded to replay",
          [d.get("replay") for k, _, d in _msg71 if k == RESULT], [])
    # A field genuinely named `cancel` is still reachable: an option is
    # matched against the whole raw line, and every assignment has an `=`.
    _eng71.submit("fillet71")
    _msg71.clear()
    _eng71.submit("cancel=5")
    check("  a field named cancel is still addressable, the panel still up",
          (_eng71.state, len(_aborted71)), ("collecting", 1))
    _eng71.cancel()

    print("\n5ao. a client that vanishes, a toggle with no button, a "
          "selection that was not taken (GH #60, #61, #73, #67)")

    # --- GH #60. The server outlives a client that leaves mid-command.
    # A command that pumps the event loop runs the disconnect while the
    # socket's own _read frame is still on the stack, and deleting it
    # there left Qt a notifier armed on freed memory.
    from fccli import server as _srv60

    class _FakeSignal:
        def __init__(self):
            self.connected = True

        def disconnect(self):
            if not self.connected:
                raise RuntimeError("not connected")
            self.connected = False

    class _FakeSock:
        def __init__(self):
            self.readyRead = _FakeSignal()
            self.disconnected = _FakeSignal()
            self.closed = False
            self.deleted = 0
            self.written = []

        def close(self):
            self.closed = True

        def deleteLater(self):
            self.deleted += 1

        def write(self, data):
            if self.deleted:
                raise RuntimeError("write to a deleted socket")
            self.written.append(data)

        def flush(self):
            pass

    class _Floor60:
        def __init__(self):
            self.released = []
            self.holder = None

        def release(self, who):
            self.released.append(who)

    class _Session60:
        def __init__(self):
            self.floor = _Floor60()

    def _server60():
        server = _srv60.Server(None)
        server.session = _Session60()
        return server

    _s60 = _server60()
    _sock60 = _FakeSock()
    _s60._clients[_sock60] = {"name": "client:1", "buffer": b"",
                              "subscribed": True, "resume": "r1"}
    _s60._drop(_sock60)
    check("a dropped client is unhooked and closed before it is deleted",
          (_sock60.readyRead.connected, _sock60.disconnected.connected,
           _sock60.closed, _sock60.deleted),
          (False, False, True, 1))
    check("  and its floor is let go",
          _s60.session.floor.released, ["client:1"])

    # The crash shape: dropped from inside its own dispatch. The deletion
    # waits for the read to unwind, so nothing frees the socket under Qt.
    _s61 = _server60()
    _sock61 = _FakeSock()
    _s61._clients[_sock61] = {"name": "client:1", "buffer": b"",
                              "subscribed": False, "resume": "r1"}
    _s61._reading.add(_sock61)
    _s61._drop(_sock61)
    check("  dropped mid-read, it is silenced at once",
          (_sock61.readyRead.connected, _sock61.closed), (False, True))
    check("    and not deleted while the read is on the stack",
          _sock61.deleted, 0)
    _s61._reading.discard(_sock61)
    _s61._bury()
    check("    the deletion lands when the read unwinds", _sock61.deleted, 1)

    # A pumped loop can be several reads deep, and the outer one may be
    # the frame holding the socket being buried.
    _s62 = _server60()
    _sock62, _other62 = _FakeSock(), _FakeSock()
    _s62._clients[_sock62] = {"name": "client:1", "buffer": b"",
                              "subscribed": False, "resume": "r1"}
    _s62._reading.update({_sock62, _other62})
    _s62._drop(_sock62)
    _s62._reading.discard(_other62)
    _s62._bury()
    check("    an inner read finishing does not bury the outer one's socket",
          _sock62.deleted, 0)
    _s62._reading.discard(_sock62)
    _s62._bury()
    check("      it is buried when the last read ends", _sock62.deleted, 1)

    # And the reply is never written to a client that left mid-command.
    _s63 = _server60()
    _sock63 = _FakeSock()
    _info63 = {"name": "client:1", "buffer": b"", "subscribed": False,
               "resume": "r1"}
    _s63._clients[_sock63] = _info63
    _sock63.readAll = lambda: b'{"op": "ping"}\n'
    _dispatched63 = []

    def _dispatch63(info, request):
        _dispatched63.append(request)
        _s63._drop(_sock63)                 # the client leaves mid-command
        return {"kind": "pong"}

    _s63._dispatch = _dispatch63
    _s63._read(_sock63)
    check("  a reply is not written to a client that left mid-command",
          (len(_dispatched63), _sock63.written), (1, []))
    check("    and the socket it left behind is deleted once, cleanly",
          _sock63.deleted, 1)

    # The checks above hand `_reading` its contents, so they pin when
    # `_bury` waits and prove nothing about anything ever reading. With
    # `_read` not recording the frame at all, every one of them still
    # passed -- and so did the socket suite's 360-client storm, because a
    # race made likely is not a race made certain. This drives the real
    # `_read`, drops the socket from inside its own dispatch, and asks
    # where the burial is at each edge of the frame.
    _s64 = _server60()
    _sock64 = _FakeSock()
    _s64._clients[_sock64] = {"name": "client:1", "buffer": b"",
                              "subscribed": False, "resume": "r1"}
    _sock64.readAll = lambda: b'{"op": "ping"}\n'
    _during64 = {}

    def _dispatch64(info, request):
        _during64["armed"] = _sock64 in _s64._reading
        _s64._drop(_sock64)                 # the disconnect a pumped loop runs
        _during64["doomed"] = list(_s64._doomed)
        _during64["deleted"] = _sock64.deleted
        return {"kind": "pong"}

    _s64._dispatch = _dispatch64
    _serve64 = _s64._serve
    _after64 = {}

    def _watch64(sock, info):
        _serve64(sock, info)
        _after64["doomed"] = list(_s64._doomed)
        _after64["deleted"] = sock.deleted

    _s64._serve = _watch64
    _s64._read(_sock64)
    check("  a read records its own frame while it is on the stack",
          _during64.get("armed"), True)
    check("    so the drop inside it defers rather than deleting",
          (_during64.get("doomed"), _during64.get("deleted")),
          ([_sock64], 0))
    check("    and is still deferred when the dispatch returns",
          (_after64.get("doomed"), _after64.get("deleted")),
          ([_sock64], 0))
    check("      the finally is what buries it",
          (_s64._doomed, _s64._reading, _sock64.deleted), ([], set(), 1))

    # --- GH #61. A checkable command with no QAction takes FreeCAD down
    # inside Gui::Command::_invoke; the command line refuses instead.
    from fccli import panels as _p61
    _old61 = _p61._ACTIONLESS
    try:
        _p61._ACTIONLESS = frozenset({"Std_ToggleToolBarLock"})
        _refusal61 = None
        try:
            # Broad: unguarded, this reaches FreeCAD, and what comes back
            # should read as a failed check rather than end the suite.
            _p61.run_command("Std_ToggleToolBarLock")
        except Exception as exc:
            _refusal61 = str(exc)
        check("a toggle with no button is refused, not run",
              _refusal61 is not None and "takes FreeCAD down" in _refusal61,
              True)
        check("  and the refusal names the command",
              _refusal61 is not None
              and _refusal61.startswith("Std_ToggleToolBarLock"), True)
        _ran61 = []
        import FreeCADGui as _Gui61
        _oldrun61 = getattr(_Gui61, "runCommand", None)
        _Gui61.runCommand = lambda name: _ran61.append(name)
        try:
            _p61.run_command("Part_Box")
            check("  every other command still goes straight through",
                  _ran61, ["Part_Box"])
        finally:
            if _oldrun61 is None:
                del _Gui61.runCommand
            else:
                _Gui61.runCommand = _oldrun61
    finally:
        _p61._ACTIONLESS = _old61

    # --- GH #73. select holds what it claims. A selection gate takes
    # every addSelection and answers nothing, so the only way to know a
    # name landed is to ask afterwards.
    from fccli import shell as _sh73

    class _Gated:
        """FreeCAD's selection with a gate on: it accepts and keeps none."""

        def __init__(self, gate=True):
            self.gate = gate
            self.held = []
            self.cleared = 0

        def clearSelection(self):
            self.cleared += 1
            self.held = []

        def addSelection(self, doc, name, sub=""):
            if not self.gate:
                self.held.append((name, sub))

        def isSelected(self, obj, sub=""):
            return (obj.Name, sub) in self.held

    class _Obj73:
        def __init__(self, name):
            self.Name = self.Label = name

            class _Doc:
                Name = "verify"
            self.Document = _Doc()

    _box73 = _Obj73("Box")
    check("a gate takes the selection and keeps none",
          _sh73._is_selected(_Gated(), _box73, ""), False)
    check("  an ungated selection is held",
          (lambda s: (s.addSelection("verify", "Box"),
                      _sh73._is_selected(s, _box73, ""))[1])(_Gated(False)),
          True)
    check("  FreeCAD that cannot say is not read as a fault",
          _sh73._is_selected(object(), _box73, ""), True)

    # The verb itself, over a document that is really open: with a gate
    # on, `select Box` used to answer `= select Box` and select nothing.
    _doc73 = App.newDocument("gate73")
    _doc73.addObject("App::FeaturePython", "Box")
    _sel73 = _Gated()

    class _Gui73:
        Selection = _sel73

    from fccli import engine as _eng73mod
    _oldgui73, _oldresolve73 = _sh73._gui, _eng73mod._resolve_names
    try:
        _sh73._gui = lambda: _Gui73
        _eng73mod._resolve_names = lambda name: [_box73]
        _fault73 = None
        try:
            _sh73._emit_select({"names": "Box", "_engine": None})
        except RuntimeError as exc:
            _fault73 = str(exc)
        check("  select over a gate is a fault, not a claim",
              (_fault73 or "").startswith("FreeCAD would not select Box"),
              True)
        check("    and it names the antidote",
              "no_selection_filters" in (_fault73 or ""), True)
        check("    leaving no half-selection behind for the next command",
              (_sel73.held, _sel73.cleared >= 2), ([], True))
        _sel73.gate = False
        _sh73._emit_select({"names": "Box", "_engine": None})
        check("  with no gate it selects and says so",
              _sel73.held, [("Box", "")])
    finally:
        _sh73._gui, _eng73mod._resolve_names = _oldgui73, _oldresolve73
        App.closeDocument("gate73")

    # --- GH #67. A call that asks the client to wait needs a cap past
    # the wait it asked for.
    import importlib.machinery as _m67
    import importlib.util as _u67
    _l67 = _m67.SourceFileLoader(
        "_fccli_socket_test",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "run_socket_test.py"))
    _mod67 = _u67.module_from_spec(_u67.spec_from_loader("_fccli_socket_test",
                                                         _l67))
    _l67.exec_module(_mod67)
    check("the boot call's cap outlasts the timeout it passes",
          _mod67.cap(("start", "--headless", "--timeout", "90")), 120)
    check("  a short wait does not shrink the floor",
          _mod67.cap(("exec", "box 1 1 1")), 60)
    check("    --wait counts the same way",
          _mod67.cap(("exec", "--wait", "45", "pad 5")), 75)
    check("    a value that is not a number leaves the floor standing",
          _mod67.cap(("start", "--timeout", "soon")), 60)
    check("      and the boot call the suite makes is capped past its ask",
          _mod67.cap(("start", "--headless",
                      "--timeout", str(_mod67.BOOT_TIMEOUT)))
          > _mod67.BOOT_TIMEOUT, True)

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
