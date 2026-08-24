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


def _internal_unit(unit):
    """The unit a stored value is in. parse_quantity hands back FreeCAD's
    internal value -- millimetres for any length, degrees for any angle
    -- whatever unit the step names, so a step in inches stores 76.2 for
    3in and must not be rendered as 76.2in."""
    try:
        kind = Units.Quantity(1, unit).Unit
        if kind == Units.Unit("mm"):
            return "mm"
        if kind == Units.Unit("deg"):
            return "deg"
    except Exception:
        pass
    return unit


def _as_quantity(value, unit):
    try:
        return Units.Quantity(value, _internal_unit(unit))
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


def format_typed(quantity):
    """Render a stored Quantity so it can be typed back in.

    A property that holds a Quantity is a value somebody entered, so it
    belongs on the same side of the line as the echo: whatever is printed
    has to parse back to what is stored. Its UserString does not. Under
    ImperialBuilding a 100 mm Length reads as 3" + 7/8", which is a syntax
    error, and 1234.5 mm reads as 4' 5/8", which parses 0.575 mm off --
    the quiet one.
    """
    try:
        value = float(quantity.Value)
    except Exception:
        return None
    text = _schema_form(quantity, value) or _converted_form(quantity, value)
    if text:
        return text
    try:
        target = quantity.getUserPreferred()[2]
        return _internal_form(float(quantity.getValueAs(target)), target)
    except Exception:
        return _internal_form(value, "")


def format_measure(value, unit):
    """Render a measurement FreeCAD computed rather than one somebody typed.

    A volume or an area is read and never typed back, so it does not have
    to survive the round-trip that format_quantity insists on -- and
    insisting costs precision: the full conversion of a cylinder's volume
    is 5.02654824574ml where FreeCAD itself says 5.03 ml, honouring the
    Decimals preference the rest of the GUI uses.
    """
    try:
        import FreeCAD as App
        return App.Units.Quantity(value, unit).UserString
    except Exception:
        return format_quantity(value, unit)


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
