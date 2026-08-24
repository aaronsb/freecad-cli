"""Spike verification. Runs offscreen, no FreeCAD GUI required.

    QT_QPA_PLATFORM=offscreen python3 tests/test_spike.py

Proves the four things the design rests on:
  1. bare keys reach the command line while another widget holds focus
  2. real editors keep their keys (focus guard)
  3. digits route by step, not by policy
  4. typed values and simulated picks land in one state machine, and the
     result replays as text
"""

import os
import sys

sys.path[:0] = [
    "/usr/lib/freecad/lib",
    "/usr/lib/freecad/Mod/Draft",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import FreeCAD as App  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from fccli.bus import Bus, ERROR, LIVE, RESULT  # noqa: E402
from fccli.engine import Engine  # noqa: E402
from fccli.grammar import REGISTRY  # noqa: E402
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
    console = Console(engine, window)
    editor = QtWidgets.QLineEdit(window)        # stands in for Python console
    for w in (viewport, console, editor):
        layout.addWidget(w)
    window.show()

    console.submitted.connect(engine.submit)
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
    bus.subscribe(lambda m: console.commit_history(m.data.get("replay", ""))
                  if m.kind == RESULT else None)

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
    engine.submit("circle 0,0,0 9.525")
    check("imperial building renders fractions",
          results[-1], 'circle 0,0,0 3/8"')
    check("a bare number now means in", U.preferred(), "in")
    engine.submit("box 0,0,0 3/8in 1ft 25.4")
    check("mixed input unifies on output",
          results[-1], 'box 0,0,0 3/8" 1\' 1"')
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
