# SPDX-License-Identifier: LGPL-2.1-or-later

"""Where the session is, for the prompt (ADR-300).

A shell prompt shows the path, the branch and the dirty flag because the
next command depends on them. FreeCAD's equivalents are the workbench,
the active Body or Part, the object in edit, whether the document is
dirty, and what is selected. One snapshot, one renderer, read by both
terminals from the same STATE message.

    PartDesign Body › Sketch* [2] /plinth >

A field that is empty is left out; with nothing to say the prompt is
`> ` as it always was.
"""

SUFFIXES = ("Workbench", "WB")

# What a command file's `requires` (ADR-100) means, said to a person.
REQUIRES = {
    "document": "a document",
    "body": "an active Body",
    "sketch-edit": "a sketch in edit mode",
    "selection": "something selected",
    "selection:face": "a face selected",
    "selection:edge": "an edge selected",
    "selection:vertex": "a vertex selected",
    "selection:solid": "a solid selected",
    "selection:sketch": "a sketch selected",
    "selection:mesh": "a mesh selected",
}


def workbench():
    """The active workbench's short name, or None without a GUI."""
    try:
        import FreeCADGui as Gui
        name = Gui.activeWorkbench().name()
    except Exception:
        return None
    for suffix in SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
    return name or None


def _label(obj):
    return getattr(obj, "Label", None) or getattr(obj, "Name", None)


def active():
    """The active container chain and the object in edit, as labels."""
    chain = []
    try:
        import FreeCADGui as Gui
        gdoc = Gui.ActiveDocument
        if gdoc is None:
            return chain
        view = getattr(gdoc, "ActiveView", None)
        for kind in ("part", "pdbody"):
            try:
                obj = view.getActiveObject(kind) if view is not None else None
            except Exception:
                obj = None
            if obj is not None and _label(obj) not in chain:
                chain.append(_label(obj))
        try:
            editing = gdoc.getInEdit()
        except Exception:
            editing = None
        if editing is not None:
            obj = getattr(editing, "Object", None)
            if obj is not None and _label(obj) not in chain:
                chain.append(_label(obj))
    except Exception:
        pass
    return chain


def selected():
    try:
        import FreeCADGui as Gui
        return len(Gui.Selection.getSelection())
    except Exception:
        return 0


def snapshot(session=None):
    from . import dirty as _dirty
    try:
        is_dirty = bool(_dirty.is_dirty())
    except Exception:
        is_dirty = False
    return {
        "workbench": workbench(),
        "active": active(),
        "dirty": is_dirty,
        "selection": selected(),
        "cwd": getattr(session, "cwd", "/") if session is not None else "/",
    }


def segment(ctx):
    """The context as the prompt shows it. Empty when there is nothing."""
    parts = []
    if ctx.get("workbench"):
        parts.append(ctx["workbench"])
    if ctx.get("active"):
        parts.append(" › ".join(ctx["active"]))
    if ctx.get("dirty"):
        if parts:
            parts[-1] += "*"
        else:
            parts.append("*")
    if ctx.get("selection"):
        parts.append(f"[{ctx['selection']}]")
    cwd = ctx.get("cwd") or "/"
    if cwd != "/":
        parts.append(cwd)
    return " ".join(parts)


def prompt(ctx):
    seg = segment(ctx)
    return f"{seg} > " if seg else "> "


def reason(requires):
    """Why a command cannot run here, from its file's requires."""
    if not requires:
        return "is not available here"
    return "needs " + ", ".join(REQUIRES.get(r, r) for r in requires)
