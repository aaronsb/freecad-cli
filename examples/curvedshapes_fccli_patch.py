"""Example: command-line support for a third-party addon.

CurvedShapes is a real installed addon and a good worked example, because it
is the ordinary case rather than the easy one. Its four commands already work
through tier 0 -- they are registered, labelled, and grouped under a "Curved
Shapes" toolbar, so `curved_array` runs the tool exactly as clicking the
button would. What it gets from tier 1 is nothing, because its objects are
``Part::FeaturePython`` with a Python proxy and FreeCAD's type registry never
sees a ``CurvedShapes::`` type to generate from.

So the verbs are declared outright. Copy this file to::

    ~/.local/share/FreeCAD/v1-1/Mod/CurvedShapes/fccli_patch.py

or, to try it without touching the addon::

    ~/.local/share/FreeCAD/fccli/patches/curvedshapes.py
"""

import FreeCAD as App


def _selection(values, key, count=None):
    """Objects the user selected, with a readable failure."""
    picked = values.get(key) or []
    if isinstance(picked, str):
        picked = [picked]
    resolved = []
    doc = App.ActiveDocument
    for item in picked:
        obj = getattr(item, "Name", None) and item or (
            doc and (doc.getObject(str(item))
                     or next((o for o in doc.Objects if o.Label == str(item)),
                             None)))
        if obj is None:
            raise RuntimeError(f"no such object: {item}")
        resolved.append(obj)
    if count is not None and len(resolved) != count:
        raise RuntimeError(f"{key} wants {count} object(s), got {len(resolved)}")
    return resolved


def make_curved_array(values):
    import CurvedShapes
    base = _selection(values, "base", 1)[0]
    hull = _selection(values, "hull")
    obj = CurvedShapes.makeCurvedArray(
        Base=base,
        Hullcurves=hull,
        Items=int(values.get("items") or 4),
        Twist=float(values.get("twist") or 0.0),
        Surface=values["_flags"].get("Surface", False),
        Solid=values["_flags"].get("Solid", False),
    )
    App.ActiveDocument.recompute()
    return obj


def make_curved_segment(values):
    import CurvedShapes
    shapes = _selection(values, "shapes", 2)
    obj = CurvedShapes.makeCurvedSegment(
        Shape1=shapes[0], Shape2=shapes[1],
        Hullcurves=_selection(values, "hull"),
        Items=int(values.get("items") or 4),
        Surface=values["_flags"].get("Surface", False),
        Solid=values["_flags"].get("Solid", False),
    )
    App.ActiveDocument.recompute()
    return obj


PATCH = {
    "key": "CurvedShapes",
    "verbs": {
        "curved_array": {
            "aliases": ["carr"],
            "doc": "Array a shape along one or more hull curves.",
            "gui_command": "CurvedArray",
            "steps": [
                {"id": "base", "kind": "selection", "prompt": "Base shape"},
                {"id": "hull", "kind": "selection", "prompt": "Hull curves",
                 "optional": True},
                {"id": "items", "kind": "quantity", "prompt": "Items",
                 "unit": "", "default": 4},
                {"id": "twist", "kind": "quantity", "prompt": "Twist",
                 "unit": "deg", "optional": True,
                 "options": ["Surface", "Solid"]},
            ],
            "emit": make_curved_array,
        },
        "curved_segment": {
            "aliases": ["cseg"],
            "doc": "Interpolate a surface between two shapes.",
            "gui_command": "CurvedSegment",
            "steps": [
                {"id": "shapes", "kind": "selection",
                 "prompt": "Two shapes to interpolate between"},
                {"id": "hull", "kind": "selection", "prompt": "Hull curves",
                 "optional": True},
                {"id": "items", "kind": "quantity", "prompt": "Items",
                 "unit": "", "default": 4, "options": ["Surface", "Solid"]},
            ],
            "emit": make_curved_segment,
        },
    },
}
