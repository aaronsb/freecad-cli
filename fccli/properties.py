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
