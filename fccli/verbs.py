"""The seed verb set.

Six verbs chosen to exercise every shape the grammar has to support:
a fixed point sequence, a repeating step with options and a terminator,
a point followed by a quantity, mixed numeric steps, and a selection.
A grammar that handles these handles a hundred.
"""

import FreeCAD as App

from .grammar import CHOICE, POINT, QUANTITY, SELECTION, Option, Step, Verb, REGISTRY


def _doc():
    return App.ActiveDocument or App.newDocument()


from .dirty import (TRACKER, dirty_documents, is_dirty,  # noqa: F401
                    mark_clean, mark_dirty)

DIRTY = TRACKER.names


def _recompute(obj):
    _doc().recompute()
    _refresh_view()
    return obj


def _refresh_view():
    """Push the new geometry to the screen now.

    A recompute alone leaves the 3D view stale until some other event pumps
    the GUI, so a command can look like it did nothing until the next click.
    """
    try:
        import FreeCADGui as Gui
        if Gui.ActiveDocument is not None:
            Gui.ActiveDocument.update()
        Gui.updateGui()
    except Exception:
        pass


# ---------------------------------------------------------------- emitters

def _emit_line(v):
    import Draft
    return _recompute(Draft.make_line(v["start"], v["end"]))


def _emit_polyline(v):
    import Draft
    pts = [v["start"]] + list(v.get("next", []))
    return _recompute(Draft.make_wire(pts, closed=v["_flags"].get("close", False)))


def _emit_circle(v):
    import Draft
    pl = App.Placement(v["center"], App.Rotation())
    r = v["radius"] / 2.0 if v["_flags"].get("diameter") else v["radius"]
    return _recompute(Draft.make_circle(r, placement=pl))


def _emit_box(v):
    import Part
    obj = _doc().addObject("Part::Box", "Box")
    obj.Length, obj.Width, obj.Height = v["length"], v["width"], v["height"]
    obj.Placement = App.Placement(v["corner"], App.Rotation())
    return _recompute(obj)


def _emit_move(v):
    delta = v["to"].sub(v["frm"])
    for obj in v["objects"]:
        obj.Placement.Base = obj.Placement.Base.add(delta)
    return _recompute(v["objects"][0] if v["objects"] else None)


def _emit_point(v):
    import Draft
    p = v["at"]
    return _recompute(Draft.make_point(p.x, p.y, p.z))


# ------------------------------------------------------------- step options

def _close(engine):
    engine.flags["close"] = True
    return True  # the verb is finished


def _undo_last(engine):
    step = engine.current_step()
    pts = engine.values.get(step.id, [])
    if pts:
        pts.pop()
        if engine.replay:
            engine.replay.pop()
    return False


def _diameter(engine):
    engine.flags["diameter"] = True
    return False


# ------------------------------------------------------------------- verbs

REGISTRY.add(Verb(
    name="line", aliases=["l"], gui_command="Draft_Line",
    doc="Draw a line between two points.",
    steps=[
        Step("start", POINT, "Start of line"),
        Step("end", POINT, "End of line", relative_to="start"),
    ],
    emit=_emit_line,
))

REGISTRY.add(Verb(
    name="polyline", aliases=["pl", "pline", "wire"], gui_command="Draft_Wire",
    doc="Draw a connected sequence of segments. Enter finishes.",
    steps=[
        Step("start", POINT, "Start of polyline"),
        Step("next", POINT, "Next point", repeat=True, min_count=1,
             relative_to="start",
             options=[
                 Option("Close", "close the wire and finish", _close),
                 Option("Undo", "remove the last point", _undo_last),
             ]),
    ],
    emit=_emit_polyline,
))

REGISTRY.add(Verb(
    name="circle", aliases=["ci", "c"], gui_command="Draft_Circle",
    doc="Draw a circle from a centre and a radius.",
    steps=[
        Step("center", POINT, "Centre of circle"),
        Step("radius", QUANTITY, "Radius",
             options=[Option("Diameter", "read the value as a diameter", _diameter)]),
    ],
    emit=_emit_circle,
))

REGISTRY.add(Verb(
    name="box", aliases=["bx"], gui_command="Part_Box",
    doc="Create a box from a corner and three dimensions.",
    steps=[
        Step("corner", POINT, "Corner of box"),
        Step("length", QUANTITY, "Length"),
        Step("width", QUANTITY, "Width"),
        Step("height", QUANTITY, "Height"),
    ],
    emit=_emit_box,
))

REGISTRY.add(Verb(
    name="move", aliases=["mv", "m"], gui_command="Draft_Move",
    doc="Move the selection by the vector between two points.",
    steps=[
        Step("objects", SELECTION, "Select objects to move"),
        Step("frm", POINT, "Move from"),
        Step("to", POINT, "Move to", relative_to="frm"),
    ],
    emit=_emit_move,
))

REGISTRY.add(Verb(
    name="point", aliases=["pt"], gui_command="Draft_Point",
    doc="Place a single point.",
    steps=[Step("at", POINT, "Point location")],
    emit=_emit_point,
))
from . import shell  # noqa: F401,E402  -- registers the shell builtins
