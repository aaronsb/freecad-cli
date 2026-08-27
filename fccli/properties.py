# SPDX-License-Identifier: LGPL-2.1-or-later

"""Which of an object's properties are worth saying out loud.

A FreeCAD object carries far more properties than describe it. Part::Box
has 18 and three of them are the box: the rest are placement plumbing,
attachment offsets, view provenance and internals FreeCAD hides from its
own property editor.

The filter used to live in tools/harvest_types.py, where it decided what a
generated verb asks for. `describe` needs the same answer at runtime, and
two copies would drift into a command that reads back something other than
what it accepts. One definition, imported by both.

Dropping 68% of the properties is what makes either surface usable.
"""

# Groups that hold plumbing rather than the shape of the thing.
NOISE_GROUPS = {"Attachment", "Base", ""}

# Property types that hold a count rather than a measurement. FreeCAD's
# setter for one of these takes an int and refuses a float outright --
# `type must be int, dict or tuple, not float` -- so a value the command
# line parsed has to be turned back into an integer before it is written,
# and a step that asks for one carries no unit (GH #78, ADR-203).
#
# The list and set forms are left out on purpose: they hold a sequence
# rather than a number, the harvest reads them as text steps, and nothing
# here would know what to make of one.
COUNTING = {
    "App::PropertyInteger",
    "App::PropertyIntegerConstraint",
    "App::PropertyPercent",
}


def counts(property_type):
    """Whether a property holds a count rather than a measurement."""
    return property_type in COUNTING


# The one property type an option can set by being named and nothing else.
# `App::PropertyBool` is what the harvest reads as a flag, and the ~398 of
# them are the whole of what `True` is a sensible value for. Not one of the
# 105 options the command tree declares is one: they are 60-odd angles, a
# dozen enumerations, some lengths and two link-subs, and every one of them
# was being set to True -- 1 degree onto an Angle whose default is 360
# (GH #81, ADR-204).
def is_flag(property_type):
    """Whether naming this property is the whole of setting it."""
    return property_type == "App::PropertyBool"


# What a link property's setter takes. A selection step's value is always a
# list of objects -- `_resolve_names` and `current_selection` both hand one
# back -- and only half of these take a list. The other half raised, and the
# raise was swallowed until GH #78 took the `except Exception: pass` out of
# the write, so 93 PropertyLinkSub and 51 PropertyLink parameters over 82
# generated verbs collected a value and never received one (GH #80).
#
# Confirmed against FreeCAD 1.1 rather than read off the docs:
#
#   PropertyLink     = [box]          TypeError: must be DocumentObject or None
#   PropertyLink     = box            takes it
#   PropertyLinkSub  = [box]          ValueError: Expect input sequence of size 2
#   PropertyLinkSub  = (box, [])      takes it, and reads back as (box, [])
#   PropertyLinkList = [box, box2]    takes it
#
# So `(obj, [])` is FreeCAD's own spelling of "this link is the whole
# object", not a workaround for one.
ONE = "one"
ONE_SUB = "one_sub"
MANY = "many"

# The X-prefixed forms link across documents and take the same shapes. They
# are here for completeness rather than because the harvest produces them:
# `KIND_BY_PROPERTY` maps the four unprefixed types and nothing else, so an
# XLink reaches a text step today. When a reconcile teaches the harvest
# about them, the write is already right.
LINKS = {
    "App::PropertyLink": ONE,
    "App::PropertyXLink": ONE,
    "App::PropertyLinkSub": ONE_SUB,
    "App::PropertyXLinkSub": ONE_SUB,
    "App::PropertyLinkList": MANY,
    "App::PropertyXLinkList": MANY,
    "App::PropertyLinkSubList": MANY,
    "App::PropertyXLinkSubList": MANY,
}


def links(property_type):
    """The shape a link property's setter takes, or None if it is no link."""
    return LINKS.get(property_type)


def link_value(property_type, value):
    """A selection step's value, in the shape this property takes.

    Returns ``(value, complaint)``. The complaint is what to say when the
    selection cannot be spent on this property at all; the value is then
    meaningless and the caller writes nothing.

    Picking the first of several for a single link is exactly what GH #78
    was about, so a count that does not fit is named and refused rather
    than trimmed.

    Subnames are where this grows. A selection carries whole objects
    today, so the sub forms get `[]`; the day `current_selection` keeps
    what `getSelectionEx` knows, the pair is built here and nothing else
    moves.
    """
    shape = LINKS.get(property_type)
    if shape is None or shape is MANY:
        # Not a link, or one of the list forms, which take the list the
        # step already holds.
        return value, None
    picked = list(value) if isinstance(value, (list, tuple)) else [value]
    picked = [o for o in picked if o is not None]
    if not picked:
        return None, None                # no link is what None means here
    if len(picked) > 1:
        names = ", ".join(getattr(o, "Label", str(o)) for o in picked)
        return None, (f"takes one object and {len(picked)} are selected "
                      f"({names}) -- name the one you mean")
    return (picked[0] if shape is ONE else (picked[0], [])), None


# Individual properties that survive the group filter and still say nothing
# a person asked for.
NOISE_PROPS = {
    "Shape", "ShapeMaterial", "Label", "Label2", "Visibility",
    "ExpressionEngine", "AddSubShape", "SuppressedShape", "Suppressed",
    "BaseFeature", "_Body", "Group", "Proxy",
}


def is_noise(obj, prop):
    """Whether a property should be left out.

    Hidden is asked of FreeCAD rather than listed here: a property the
    property editor will not show is not one to read out either, and which
    those are depends on the object.
    """
    if prop in NOISE_PROPS:
        return True
    try:
        if obj.getGroupOfProperty(prop) in NOISE_GROUPS:
            return True
        if "Hidden" in (obj.getEditorMode(prop) or []):
            return True
    except Exception:
        return True
    return False


def useful(obj, props=None):
    """The properties of an object that describe it, in declaration order."""
    names = props if props is not None else getattr(obj, "PropertiesList", [])
    return [p for p in names if not is_noise(obj, p)]
