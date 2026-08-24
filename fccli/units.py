# SPDX-License-Identifier: LGPL-2.1-or-later

"""Unit display, driven by FreeCAD's own schema and converter.

FreeCAD already knows how to render 9.525mm as 3/8" -- that is the
ImperialBuilding schema, and the status bar uses it. Everything here goes
through FreeCAD's API rather than a parallel notion of units:

    Quantity.getUserPreferred()   the schema's rendering, its preferred unit,
                                  and the factor -- all three, from FreeCAD
    Quantity.getValueAs(unit)     the converter. No arithmetic here.

The catch is that the schema's rendering is for reading, not re-parsing: it
is rounded to two decimals, contains spaces, and its compound imperial form
(``3" + 7/8"``) does not parse back at all. The echoed line is also the line
Up recalls, so every rendering is round-tripped before it is used and falls
back to a precise conversion when it does not survive.
"""

import FreeCAD as App
from FreeCAD import Units

EPSILON = 1e-7
PARAM = "User parameter:BaseApp/Preferences/Units"


def schemas():
    return list(Units.listSchemas())


def current_index():
    try:
        return App.ParamGet(PARAM).GetInt("UserSchema", 0)
    except Exception:
        return 0


def current_name():
    names = schemas()
    index = current_index()
    return names[index] if 0 <= index < len(names) else names[0]


def set_schema(name_or_index):
    """Point both FreeCAD and this session at a schema."""
    names = schemas()
    if isinstance(name_or_index, int):
        index = name_or_index
    else:
        wanted = str(name_or_index).lower().replace(" ", "").replace("_", "")
        index = next((i for i, n in enumerate(names)
                      if n.lower() == wanted), None)
        if index is None:
            index = next((i for i, n in enumerate(names)
                          if n.lower().startswith(wanted)), None)
    if index is None or not 0 <= index < len(names):
        raise ValueError(f"unknown schema: {name_or_index}")
    Units.setSchema(index)
    App.ParamGet(PARAM).SetInt("UserSchema", index)
    return names[index]


def preferred(kind="length"):
    """The unit FreeCAD would display right now. What Tab appends."""
    probe = "1 deg" if kind == "angle" else "1 mm"
    try:
        return Units.Quantity(probe).getUserPreferred()[2]
    except Exception:
        return "deg" if kind == "angle" else "mm"


# ---------------------------------------------------------------- rendering

def _round_trips(text, value):
    try:
        return abs(Units.Quantity(text).Value - value) < EPSILON
    except Exception:
        return False


def _as_quantity(value, unit):
    try:
        return Units.Quantity(value, unit)
    except Exception:
        return None


def _schema_form(quantity, value):
    """FreeCAD's own rendering, if it survives being read back."""
    try:
        shown = quantity.getUserPreferred()[0]
    except Exception:
        return None
    packed = shown.replace(" ", "")
    return packed if _round_trips(packed, value) else None


def _converted_form(quantity, value):
    """The value in the schema's preferred unit, converted by FreeCAD."""
    try:
        target = quantity.getUserPreferred()[2]
        converted = float(quantity.getValueAs(target))
    except Exception:
        return None
    for digits in (6, 9, 12, 15):
        text = f"{converted:.{digits}g}{target}"
        if _round_trips(text, value):
            return text
    return None


def _internal_form(value, unit):
    def n(x):
        s = f"{x:.10g}"
        return "0" if s in ("-0", "-0.0") else s
    return f"{n(value)}{unit}" if unit else n(value)


def format_quantity(value, unit="mm"):
    """Render a stored value for the echo, in the configured schema.

    Order: FreeCAD's own rendering when it round-trips, then FreeCAD's
    conversion into the preferred unit, then the raw internal value.
    """
    if not unit:
        return _internal_form(value, "")
    quantity = _as_quantity(value, unit)
    if quantity is None:
        return _internal_form(value, unit)
    return (_schema_form(quantity, value)
            or _converted_form(quantity, value)
            or _internal_form(value, unit))
