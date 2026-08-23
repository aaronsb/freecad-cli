"""Shell builtins.

Document and application verbs that a terminal user reaches for without
thinking: save, open, close, clear. They exist as first-class verbs because
the GUI equivalents route through modal dialogs -- Save on an unnamed
document opens a file chooser, and saving over an existing file asks for
confirmation. A command line that has already been given the path should not
stop to ask for it again.

Every one of these takes the path as an argument when it has somewhere to
put it, and falls back to FreeCAD's own command (dialog included) when it
does not.
"""

import os

import FreeCAD as App

from . import bus as _bus
from .grammar import PATH, TEXT, Step, Verb, REGISTRY
from .verbs import DIRTY, is_dirty, mark_clean


def _gui():
    try:
        import FreeCADGui as Gui
        return Gui
    except ImportError:
        return None


def _expand(path):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def _run(command):
    """Fall back to FreeCAD's own command, dialog and all."""
    gui = _gui()
    if gui is None:
        raise RuntimeError(f"{command} needs the GUI")
    gui.runCommand(command)


def _say(values, text):
    engine = values.get("_engine")
    if engine is not None:
        engine.bus.emit(_bus.INFO, text)


# ---------------------------------------------------------------- documents

def _emit_save(v):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("no active document")
    path = v.get("path")
    if path:
        doc.saveAs(_expand(path))
    elif doc.FileName:
        doc.save()
    else:
        _run("Std_SaveAs")          # unnamed: FreeCAD asks where
        return doc
    mark_clean(doc)
    _say(v, f"saved {doc.FileName}")
    return doc


def _emit_open(v):
    path = _expand(v["path"])
    if not os.path.exists(path):
        raise RuntimeError(f"no such file: {path}")
    doc = App.openDocument(path)
    mark_clean(doc)
    _say(v, f"opened {doc.Name}")
    return doc


def _emit_new(v):
    name = v.get("name") or "Unnamed"
    doc = App.newDocument(name)
    mark_clean(doc)
    _say(v, f"new document {doc.Name}")
    return doc


def _emit_close(v):
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("no active document")
    name = doc.Name
    if is_dirty(doc) and not v["_flags"].get("force"):
        raise RuntimeError(
            f"{name} has unsaved changes -- save first, or close! to discard")
    # closeDocument discards without prompting. The refusal above is the
    # confirmation, so the modal never appears.
    mark_clean(name=name)
    App.closeDocument(name)
    _say(v, f"closed {name}")
    return None


def _emit_clear(v):
    engine = v.get("_engine")
    if engine is not None:
        engine.bus.emit(_bus.CLEAR)
    return None


def _emit_undo(v):
    doc = App.ActiveDocument
    if doc is not None:
        doc.undo()
    return None


def _emit_redo(v):
    doc = App.ActiveDocument
    if doc is not None:
        doc.redo()
    return None


def _emit_fit(v):
    gui = _gui()
    if gui is not None:
        gui.SendMsgToActiveView("ViewFit")
    return None


def _emit_delete(v):
    gui = _gui()
    doc = App.ActiveDocument
    if gui is None or doc is None:
        raise RuntimeError("no active document")
    names = [o.Name for o in gui.Selection.getSelection()]
    if not names:
        raise RuntimeError("nothing selected")
    for name in names:
        doc.removeObject(name)
    doc.recompute()
    _say(v, f"deleted {len(names)}")
    return None


# -------------------------------------------------------------------- verbs

REGISTRY.add(Verb(
    name="save", aliases=["w"], gui_command="Std_Save",
    doc="Save the active document. With a path, save there without asking.",
    steps=[Step("path", PATH, "Save as (Enter for the current file)",
                optional=True)],
    emit=_emit_save,
))

REGISTRY.add(Verb(
    name="open", aliases=["e"], gui_command="Std_Open",
    doc="Open a document by path.",
    steps=[Step("path", PATH, "File to open")],
    emit=_emit_open,
))

REGISTRY.add(Verb(
    name="new", gui_command="Std_New",
    doc="Create a document.",
    steps=[Step("name", TEXT, "Document name", optional=True)],
    emit=_emit_new,
))

REGISTRY.add(Verb(
    name="close", aliases=["q"], gui_command="Std_CloseActiveWindow",
    doc="Close the active document. Refuses if unsaved; close! discards.",
    steps=[], emit=_emit_close,
))

REGISTRY.add(Verb(
    name="clear", aliases=["cls"],
    doc="Wipe the command line scrollback.",
    steps=[], emit=_emit_clear,
))

REGISTRY.add(Verb(
    name="undo", aliases=["u"], gui_command="Std_Undo",
    doc="Undo the last document transaction.",
    steps=[], emit=_emit_undo,
))

REGISTRY.add(Verb(
    name="redo", gui_command="Std_Redo",
    doc="Redo the last undone transaction.",
    steps=[], emit=_emit_redo,
))

REGISTRY.add(Verb(
    name="fit", aliases=["zoom", "zf"], gui_command="Std_ViewFitAll",
    doc="Zoom to fit everything in the view.",
    steps=[], emit=_emit_fit,
))

REGISTRY.add(Verb(
    name="delete", aliases=["del"], gui_command="Std_Delete",
    doc="Delete the selected objects.",
    steps=[], emit=_emit_delete,
))


def _emit_quit(v):
    """Leave FreeCAD.

    Closing the application prompts once per modified document. quit lists
    what is unsaved and refuses; quit! discards it. Same shape as close, so
    the answer to "save changes?" is given on the command line rather than
    in a modal that blocks every other key.
    """
    dirty = [n for n in App.listDocuments() if n in DIRTY]
    if dirty and not v["_flags"].get("force"):
        raise RuntimeError(
            "unsaved: " + ", ".join(dirty) + " -- save first, or quit! to discard")
    for name in list(App.listDocuments()):
        mark_clean(name=name)
        try:
            App.closeDocument(name)
        except Exception:
            pass
    gui = _gui()
    if gui is not None:
        from .qt import QtWidgets
        QtWidgets.QApplication.instance().quit()
    return None


def _emit_help(v):
    """List the verbs, so the command language is discoverable from itself."""
    engine = v.get("_engine")
    if engine is None:
        return None
    topic = v.get("topic")
    if topic:
        verb = REGISTRY.get(topic)
        if verb is None:
            raise RuntimeError(f"unknown command: {topic}")
        alias = f"  ({', '.join(verb.aliases)})" if verb.aliases else ""
        engine.bus.emit(_bus.INFO, f"{verb.name}{alias} -- {verb.doc}")
        for i, step in enumerate(verb.steps, 1):
            opts = (f"   [{'/'.join(step.option_names())}]"
                    if step.options else "")
            tail = "  (optional)" if step.optional else ""
            engine.bus.emit(_bus.INFO,
                            f"  {i}. {step.prompt} <{step.kind}>{opts}{tail}")
        return None
    for name in REGISTRY.names():
        verb = REGISTRY.get(name)
        alias = f" ({verb.aliases[0]})" if verb.aliases else ""
        engine.bus.emit(_bus.INFO, f"  {name + alias:<18} {verb.doc}")
    return None


REGISTRY.add(Verb(
    name="quit", aliases=["exit", "qa"],
    doc="Leave FreeCAD. Refuses on unsaved work; quit! discards it.",
    steps=[], emit=_emit_quit,
))

REGISTRY.add(Verb(
    name="help", aliases=["?", "h"],
    doc="List the commands, or describe one.",
    steps=[Step("topic", TEXT, "Command to describe", optional=True)],
    emit=_emit_help,
))
