# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read an object out as text.

FreeCAD has no command that does this. Std_Properties opens the property
panel, Std_ProjectInfo is a document-level dialog, Mesh_BoundingBox is
mesh-only and Std_Measure is a tool you aim. All of them are surfaces you
have to look at.

A screen reader cannot read a property grid or a viewport. It reads a
terminal. Together with the socket client, this is the piece that makes a
document inspectable without sight -- and the same text is what an agent
needs to reason about a document it did not build.

Nothing here is written per type. The properties come from the object, the
filter is the one generated verbs already use, and the numbers are rendered
through FreeCAD's unit schema, so a document reads in whatever units its
owner works in.
"""

from . import units as _units
from .properties import useful

# Placement is plumbing as a parameter and identity as a fact, so it is
# read directly rather than through the property filter that drops it.
PLACEMENT_EPSILON = 1e-9


def _quantity(value, unit):
    """A value somebody typed, rendered the way the command line renders it."""
    try:
        return _units.format_quantity(value, unit)
    except Exception:
        return f"{value:g}{unit or ''}"


def _measured(value, unit):
    """A value FreeCAD computed.

    Held to FreeCAD's own rendering rather than to a round-trip, because
    nothing types a bounding box back in. Under an imperial schema the
    difference is 5/8" against 0.62992126in.
    """
    try:
        return _units.format_measure(value, unit)
    except Exception:
        return _quantity(value, unit)


def _vector(vec, unit="mm"):
    return ", ".join(_quantity(getattr(vec, axis), unit) for axis in "xyz")


def _value(obj, prop):
    """One property as text, with its unit if FreeCAD gave it one."""
    value = getattr(obj, prop, None)
    if value is None:
        return None
    kind = ""
    try:
        kind = obj.getTypeIdOfProperty(prop)
    except Exception:
        pass
    if hasattr(value, "Value") and hasattr(value, "UserString"):
        return value.UserString                     # already a Quantity
    if hasattr(value, "x") and hasattr(value, "y"):
        return _vector(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        unit = "mm" if "Length" in kind or "Distance" in kind else ""
        return _quantity(value, unit) if unit else f"{value:g}"
    if isinstance(value, (list, tuple)):
        return f"{len(value)} items" if len(value) != 1 else "1 item"
    text = str(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _shape_facts(obj):
    """What the built shape measures, when there is one.

    A boolean result has no parametric properties worth reading -- its
    dimensions live in the shape, not in the feature.
    """
    shape = getattr(obj, "Shape", None)
    if shape is None or getattr(shape, "isNull", lambda: True)():
        return []
    out = []
    try:
        box = shape.BoundBox
        out.append(("bounding box",
                    f"{_measured(box.XLength, 'mm')} x "
                    f"{_measured(box.YLength, 'mm')} x "
                    f"{_measured(box.ZLength, 'mm')}"))
        out.append(("  from", f"{_measured(box.XMin, 'mm')}, "
                              f"{_measured(box.YMin, 'mm')}, "
                              f"{_measured(box.ZMin, 'mm')}"))
    except Exception:
        pass
    for label, attr, unit in (("volume", "Volume", "mm^3"),
                              ("surface area", "Area", "mm^2")):
        try:
            value = getattr(shape, attr, None)
            if value:
                out.append((label, _measured(value, unit)))
        except Exception:
            pass
    for label, attr in (("vertices", "Vertexes"), ("edges", "Edges"),
                        ("faces", "Faces")):
        try:
            count = len(getattr(shape, attr, []) or [])
            if count:
                out.append((label, str(count)))
        except Exception:
            pass
    return out


def _placement_facts(obj):
    placement = getattr(obj, "Placement", None)
    if placement is None:
        return []
    out = [("position", _vector(placement.Base))]
    try:
        angle = placement.Rotation.Angle
        if abs(angle) > PLACEMENT_EPSILON:
            axis = placement.Rotation.Axis
            out.append(("rotation",
                        f"{_quantity(angle * 180.0 / 3.141592653589793, 'deg')}"
                        f" about {axis.x:g}, {axis.y:g}, {axis.z:g}"))
        else:
            out.append(("rotation", "none"))
    except Exception:
        pass
    return out


def sections(obj, verb_for=None):
    """Everything worth saying about one object, as (heading, [(k, v)]).

    ``verb_for`` maps a type id to the verb that builds it, so a description
    can end by naming the command that would make another.
    """
    ident = [("label", getattr(obj, "Label", "") or ""),
             ("name", getattr(obj, "Name", "") or ""),
             ("type", getattr(obj, "TypeId", "") or "")]
    verb = verb_for(getattr(obj, "TypeId", "")) if verb_for else None
    if verb:
        ident.append(("made by", verb))
    state = [s for s in (getattr(obj, "State", []) or []) if s != "Up-to-date"]
    if state:
        ident.append(("state", ", ".join(state)))

    params = []
    for prop in useful(obj):
        text = _value(obj, prop)
        if text is not None and text != "":
            params.append((prop, text))

    out = [("IDENTITY", ident)]
    placement = _placement_facts(obj)
    if placement:
        out.append(("PLACEMENT", placement))
    if params:
        out.append(("PROPERTIES", params))
    shape = _shape_facts(obj)
    if shape:
        out.append(("SHAPE", shape))

    children = [c.Label for c in (getattr(obj, "Group", None) or [])]
    if children:
        out.append(("CONTAINS", [(f"{len(children)} objects",
                                  ", ".join(children[:12]))]))
    parents = [p.Label for p in (getattr(obj, "InList", None) or [])]
    if parents:
        out.append(("USED BY", [("", ", ".join(parents[:12]))]))
    return out


def summary(obj):
    """One line, for listing several objects at once."""
    label = getattr(obj, "Label", "") or getattr(obj, "Name", "?")
    type_id = (getattr(obj, "TypeId", "") or "").split("::")[-1]
    shape = getattr(obj, "Shape", None)
    size = ""
    try:
        if shape is not None and not shape.isNull():
            box = shape.BoundBox
            size = (f"  {_measured(box.XLength, 'mm')} x "
                    f"{_measured(box.YLength, 'mm')} x "
                    f"{_measured(box.ZLength, 'mm')}")
    except Exception:
        pass
    return f"{label}  <{type_id}>{size}"
