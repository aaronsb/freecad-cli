# SPDX-License-Identifier: LGPL-2.1-or-later

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
from . import curation as _curation
from . import engine as _engine_mod
from . import describe as _describe
from . import shortcuts as _shortcuts
from . import paths as _paths
from .grammar import (CHOICE, PATH, QUANTITY, TEXT, Option, Step, Verb,
                      REGISTRY)
from .dirty import dirty_documents, is_dirty, mark_clean


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


ZOOM_TARGETS = {
    "extents": ("Std_ViewFitAll", "everything in the document"),
    "all": ("Std_ViewFitAll", "everything in the document"),
    "selection": ("Std_ViewFitSelection", "just what is selected"),
    "in": ("Std_ViewZoomIn", "closer"),
    "out": ("Std_ViewZoomOut", "further away"),
    "window": ("Std_ViewBoxZoom", "a box you drag in the viewport"),
}

VIEW_TARGETS = {
    "front": "Std_ViewFront", "back": "Std_ViewRear", "rear": "Std_ViewRear",
    "top": "Std_ViewTop", "bottom": "Std_ViewBottom",
    "left": "Std_ViewLeft", "right": "Std_ViewRight",
    "iso": "Std_ViewIsometric", "isometric": "Std_ViewIsometric",
    "axonometric": "Std_ViewIsometric",
}


def _emit_fit(v):
    """Zoom, with a target rather than only fit-all.

    FreeCAD spreads these across Std_ViewFitAll, Std_ViewFitSelection,
    Std_ViewZoomIn, Std_ViewZoomOut and Std_ViewBoxZoom -- five commands
    with no shared name. One verb with a choice reads better and is
    completable.
    """
    gui = _gui()
    if gui is None:
        raise RuntimeError("zoom needs the GUI")
    target = (v.get("target") or "extents").lower()
    if target in ZOOM_TARGETS:
        command, _doc = ZOOM_TARGETS[target]
        if target in ("extents", "all"):
            gui.SendMsgToActiveView("ViewFit")
        else:
            gui.runCommand(command)
        return None
    if target in VIEW_TARGETS:
        gui.runCommand(VIEW_TARGETS[target])
        return None
    raise RuntimeError(
        f"zoom where? one of: {', '.join(sorted(ZOOM_TARGETS))}, "
        f"{', '.join(sorted(set(VIEW_TARGETS)))}")


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
    name="save", transactional=False, aliases=["w"], gui_command="Std_Save",
    doc="Save the active document. With a path, save there without asking.",
    steps=[Step("path", PATH, "Save as (Enter for the current file)",
                optional=True)],
    emit=_emit_save,
))

REGISTRY.add(Verb(
    name="open", transactional=False, aliases=["e"], gui_command="Std_Open",
    doc="Open a document by path.",
    steps=[Step("path", PATH, "File to open")],
    emit=_emit_open,
))

REGISTRY.add(Verb(
    name="new", transactional=False, gui_command="Std_New",
    doc="Create a document.",
    steps=[Step("name", TEXT, "Document name", optional=True)],
    emit=_emit_new,
))

REGISTRY.add(Verb(
    name="close", transactional=False, aliases=["q"], gui_command="Std_CloseActiveWindow",
    doc="Close the active document. Refuses if unsaved; close! discards.",
    steps=[], emit=_emit_close,
))

REGISTRY.add(Verb(
    name="clear", transactional=False, aliases=["cls"],
    doc="Wipe the command line scrollback.",
    steps=[], emit=_emit_clear,
))

REGISTRY.add(Verb(
    name="undo", transactional=False, aliases=["u"], gui_command="Std_Undo",
    doc="Undo the last document transaction.",
    steps=[], emit=_emit_undo,
))

REGISTRY.add(Verb(
    name="redo", transactional=False, gui_command="Std_Redo",
    doc="Redo the last undone transaction.",
    steps=[], emit=_emit_redo,
))

REGISTRY.add(Verb(
    name="zoom", transactional=False, aliases=["fit", "zf"],
    gui_command="Std_ViewFitAll",
    doc="Zoom the view: extents, selection, in, out, window, or a named view.",
    steps=[Step("target", CHOICE, "Zoom to", optional=True,
                default="extents",
                choices=sorted(ZOOM_TARGETS) + sorted(set(VIEW_TARGETS)))],
    emit=_emit_fit,
))

REGISTRY.add(Verb(
    name="delete", aliases=["del"], gui_command="Std_Delete",
    doc="Delete the selected objects.",
    steps=[], emit=_emit_delete,
))


SHOT_DIR = _paths.data("shots")


def _shot_path(given):
    """Where the image goes. A given path wins; otherwise a numbered file."""
    if given:
        path = _expand(given)
        if not os.path.splitext(path)[1]:
            path += ".png"
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        return path
    os.makedirs(SHOT_DIR, exist_ok=True)
    doc = App.ActiveDocument
    stem = (doc.Name if doc is not None else "freecad").lower()
    n = 1
    while True:
        path = os.path.join(SHOT_DIR, f"{stem}-{n:03d}.png")
        if not os.path.exists(path):
            return path
        n += 1


def _emit_shortcuts(v):
    """List, import or drop FreeCAD's key chords as aliases.

    A command rather than something that happens on first load: it changes
    what a hundred words mean, and that should be asked for and reversible.
    """
    engine = v.get("_engine")
    if engine is None:
        return None

    def say(text, role="info"):
        engine.bus.emit(_bus.INFO, text, role=role)

    what = (v.get("what") or "list").strip().lower()
    mine, imported = _read_aliases()
    from .factory import load_descriptor
    accepted, rejected = _shortcuts.proposals(
        REGISTRY, load_descriptor(), mine)

    if what == "list":
        say(f"{len(accepted)} chords could become aliases", "head")
        for row in _columns([f"{a}={verb}" for a, verb in
                             sorted(accepted.items())][:60], width=68):
            say(f"  {row}", "quiet")
        if rejected:
            # `shortcuts why`. The hint used to name `shortcuts import
            # --why`, and the CHOICE step takes `import` and discards the
            # rest -- so somebody trying to read why a chord was skipped
            # changed what a hundred and sixty words mean instead.
            say(f"{len(rejected)} skipped -- shortcuts why says which",
                "quiet")
        say("shortcuts import adds them; shortcuts drop removes them again")
        return None

    if what == "why":
        say(f"{len(rejected)} chords were skipped", "head")
        for alias, reason in sorted(rejected.items()):
            say(f"  {alias:<8} {reason}")
        return None

    if what == "import":
        fresh = []
        for alias, name in accepted.items():
            verb = REGISTRY.get(name)
            if verb is None or alias in verb.aliases:
                continue
            verb.aliases.append(alias)
            REGISTRY.add(verb)
            mine[alias] = name
            imported.add(alias)
            fresh.append(alias)
        REGISTRY.reindex()
        _save_aliases(mine, imported)
        shown = ", ".join(sorted(fresh)[:3])
        say(f"imported {len(fresh)} chords"
            + (f" -- {shown} and the rest now type" if fresh else ""))
        return None

    if what == "drop":
        dropped = 0
        for alias in sorted(imported):
            if alias not in mine:
                continue
            verb = REGISTRY.get(mine[alias])
            if verb is not None and alias in verb.aliases:
                verb.aliases.remove(alias)
            mine.pop(alias, None)
            dropped += 1
        REGISTRY.reindex()
        _save_aliases(mine, set())
        say(f"dropped {dropped} imported chords"
            + ("" if dropped else " -- nothing was imported"))
        return None

    raise RuntimeError(f"shortcuts takes list, why, import or drop")


def _emit_describe(v):
    """Read an object out, or list what the document holds.

    Bare, it summarises every object. Given a label it describes one in
    full. Nothing is written per type: the properties come off the object,
    the filter is the one generated verbs use, and every number goes
    through the unit schema.
    """
    engine = v.get("_engine")
    doc = App.ActiveDocument
    if engine is None:
        return None
    if doc is None:
        raise RuntimeError("no active document")

    def say(text, role="info"):
        engine.bus.emit(_bus.INFO, text, role=role)

    target = (v.get("object") or "").strip()
    if not target:
        gui = _gui()
        # Gui exists without Selection under freecadcmd, so ask for the
        # attribute rather than for the module.
        selection = getattr(gui, "Selection", None) if gui else None
        picked = list(selection.getSelection()) if selection else []
        if picked:
            objects = picked
        else:
            if not doc.Objects:
                say(f"{doc.Label} is empty", "quiet")
                return None
            say(f"{doc.Label} -- {len(doc.Objects)} objects", "head")
            for obj in doc.Objects:
                say("  " + _describe.summary(obj))
            say("  describe <label> reads one out in full", "quiet")
            return None
    else:
        # engine._resolve_names is the same lookup a selection step does,
        # so both surfaces answer to a name identically -- and describe
        # gets `describe A,B` out of sharing it.
        objects = _engine_mod._resolve_names(target)
        if not objects:
            names = [o.Label for o in doc.Objects]
            hint = _did_you_mean_from(names, target)
            raise RuntimeError(
                f"no object called {target!r}"
                + (f" -- did you mean {hint}?" if hint else ""))

    for obj in objects:
        for heading, rows in _describe.sections(obj, verb_for=_verb_for_type):
            say(heading, "head")
            for key, value in rows:
                say(f"    {key:<16} {value}" if key else f"    {value}")
    return None


_BY_TYPE = None


def _verb_for_type(type_id):
    """The verb that builds this type, when the type says which.

    Only when exactly one verb claims it. A Draft line, a Draft point and
    anything else Draft wraps are all Part::FeaturePython, so picking the
    first claimant in registry order reported every Draft line as made by
    point. A type that several verbs build does not identify one, and
    saying nothing is the honest answer.

    Built once. This was a linear scan of the whole registry -- 1258 verbs
    -- for every object described.
    """
    global _BY_TYPE
    if _BY_TYPE is None:
        curated = _curation.current()
        claims = {}
        for name in REGISTRY.names():
            creates = REGISTRY.get(name).creates
            if creates:
                claims.setdefault(creates, []).append(name)
        _BY_TYPE = {}
        for creates, names in claims.items():
            # A verb somebody wrote answers for the type over one the
            # factory generated for it -- `box` over the re-homed
            # `part_box`, which ranks PROMOTED just the same. Where that
            # leaves more than one, nothing about the type says which:
            # line and point are both hand-written and both build a
            # Part::FeaturePython.
            written = [n for n in names if _curation.authored(REGISTRY.get(n))]
            best = written or names
            if len(best) == 1:
                _BY_TYPE[creates] = best[0]
    return _BY_TYPE.get(type_id) if type_id else None


def _closest(names, token, limit=1):
    """Closest names to a token, so a typo suggests its fix."""
    import difflib
    return difflib.get_close_matches(token.lower(), list(names),
                                     n=limit, cutoff=0.6)


def _did_you_mean_from(names, token):
    hit = _closest(names, token)
    return hit[0] if hit else None


def _emit_screenshot(v):
    """Save a picture of the model, and say where it went.

    The path is the point: whoever asked -- a person scrolling back, or an
    agent driving the session over the socket -- needs to be able to open
    the file without guessing its name.

    Default is the 3D view through FreeCAD's own saveImage. The window
    option grabs the whole application instead, which needs real hardware
    GL: a widget grab of an OpenGL viewport on a virtual display comes back
    as flat colour.
    """
    gui = _gui()
    if gui is None:
        raise RuntimeError("screenshot needs the GUI")
    path = _shot_path(v.get("path"))
    flags = v["_flags"]
    width = int(v.get("width") or 1600)
    height = int(v.get("height") or 1100)

    if flags.get("Window"):
        window = gui.getMainWindow()
        if window is None:
            raise RuntimeError("no main window")
        if not window.grab().save(path):
            raise RuntimeError(f"could not write {path}")
    else:
        doc = gui.ActiveDocument
        view = doc.activeView() if doc is not None else None
        if view is None:
            raise RuntimeError("no 3D view -- open a document first")
        if flags.get("Fit"):
            gui.SendMsgToActiveView("ViewFit")
        background = "Transparent" if flags.get("Transparent") else "Current"
        view.saveImage(path, width, height, background)

    if not os.path.exists(path):
        raise RuntimeError(f"nothing was written to {path}")
    size = os.path.getsize(path) // 1024
    _say(v, f"{path} ({size} KB)")
    return path


def _emit_scope(v):
    """Narrow what Tab offers to one corner of FreeCAD.

    Typing c and pressing Tab against 1250 launchers is not discovery, it
    is a wall. Scoping to a domain makes the same key useful again, and the
    domains are read off what each verb already carries rather than tagged
    by hand.
    """
    from .completion import domains, domain_of
    engine = v.get("_engine")
    if engine is None:
        return None
    session = getattr(engine, "session", None)
    wanted = v.get("domain")

    if not wanted:
        current = getattr(session, "scope", None)
        counts = domains(engine.registry)
        engine.bus.emit(
            _bus.INFO,
            f"scoped to {current}" if current else "not scoped -- all "
            f"{len(engine.registry.names())} commands complete", role="head")
        for name, count in sorted(counts.items(), key=lambda kv: -kv[1])[:20]:
            mark = "*" if current and name.lower() == current.lower() else " "
            engine.bus.emit(_bus.INFO, f"  {mark} {name:<16} {count:>4}",
                            role="ok" if mark == "*" else "quiet")
        engine.bus.emit(_bus.INFO, "use <domain> to narrow, use off to clear",
                        role="quiet")
        return None

    if wanted.lower() in ("off", "none", "all", "clear"):
        if session is not None:
            session.scope = None
        _say(v, "scope cleared")
        return None

    counts = domains(engine.registry)
    match = next((d for d in counts if d.lower() == wanted.lower()), None)
    if match is None:
        match = next((d for d in counts if d.lower().startswith(wanted.lower())),
                     None)
    if match is None:
        raise RuntimeError(
            f"no domain {wanted!r}. Try: " +
            ", ".join(sorted(counts, key=lambda d: -counts[d])[:8]))
    if session is not None:
        session.scope = match
    _say(v, f"scoped to {match} -- {counts[match]} commands complete here")
    return None


def _emit_commands(v):
    """What is in a domain, or what the domains are."""
    from .completion import domains, domain_of
    engine = v.get("_engine")
    if engine is None:
        return None
    wanted = v.get("domain")
    counts = domains(engine.registry)
    if not wanted:
        engine.bus.emit(_bus.INFO,
                        f"{len(counts)} domains, "
                        f"{sum(counts.values())} commands", role="head")
        for name, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            engine.bus.emit(_bus.INFO, f"  {name:<16} {count:>4}", role="quiet")
        return None
    match = next((d for d in counts if d.lower().startswith(wanted.lower())),
                 None)
    if match is None:
        raise RuntimeError(f"no domain {wanted!r}")
    names = sorted(n for n in engine.registry.names()
                   if domain_of(engine.registry.get(n)) == match)
    engine.bus.emit(_bus.INFO, f"{match} -- {len(names)} commands",
                    role="head")
    for i in range(0, len(names), 4):
        engine.bus.emit(_bus.INFO,
                        "  " + "".join(f"{n:<22}" for n in names[i:i + 4]),
                        role="quiet")
    return None


def _emit_check(v):
    """Resolve and validate a command without running it.

    A shadow engine over the same registry parses the line through exactly
    the code path the live one uses, then stops before emitting. So what
    check accepts is what would actually run -- it is the same grammar, not
    a second implementation of it that can drift.

    Nothing is created, no transaction opens, and no document is required.
    """
    from . import bus as _b
    from .engine import Engine

    engine = v.get("_engine")
    # The step repeats, so the rest of the line arrives as tokens.
    line = str(v.get("line") or "").strip()
    if engine is None:
        return None
    if not line:
        raise RuntimeError("check what?")

    def say(text, role="info"):
        engine.bus.emit(_b.INFO, text, role=role)
    seen = {"errors": [], "result": None, "prompt": None}
    shadow_bus = _b.Bus()

    def collect(msg):
        if msg.kind == _b.ERROR:
            seen["errors"].append(msg.text)
        elif msg.kind == _b.RESULT:
            seen["result"] = msg
        elif msg.kind == _b.PROMPT and not msg.data.get("idle"):
            seen["prompt"] = msg

    shadow_bus.subscribe(collect)
    shadow = Engine(shadow_bus, engine.registry, picker=None, dry=True)
    shadow.submit(line)

    token = line.split()[0]
    hits = engine.registry.resolve_prefix(token.rstrip("!"))
    if not hits:
        near = _did_you_mean(engine.registry, token)
        say(f"unknown command: {token}", "bad")
        if near:
            say("  did you mean: " + ", ".join(near), "head")
        return None
    if len(hits) > 1:
        say(f"ambiguous: {token} matches " + ", ".join(hits), "warn")
        return None

    verb = engine.registry.get(hits[0])
    say(f"{verb.name} -- {verb.doc}", "head")

    result = seen["result"]
    if result is not None:
        # An argument can be rejected and the command still complete, when
        # what it was rejected for was optional. Say so rather than
        # reporting a clean run.
        for text in seen["errors"]:
            say(f"  ignored: {text}", "warn")
        say(f"  would run:  {result.data['replay']}", "ok")
        values = result.data.get("values") or {}
        for step in verb.steps:
            if step.id in values:
                say(f"    {step.id:<12} {_show(values[step.id])}", "value")
        flags = [k for k, on in (result.data.get("flags") or {}).items()
                 if on and k != "force"]
        if flags:
            say("    options      " + ", ".join(flags), "value")
        if verb.creates:
            say(f"  would create: {verb.creates}", "ok")
        say("  nothing was run.", "quiet")
        return None

    if seen["errors"]:
        for text in seen["errors"]:
            say(f"  rejected: {text}", "bad")
        return None

    prompt = seen["prompt"]
    if prompt is not None:
        remaining = [st.id for st in shadow.verb.steps[shadow.step_index:]] \
            if shadow.verb else []
        say(f"  incomplete -- still wants: {prompt.text}", "warn")
        if len(remaining) > 1:
            say("    then: " + ", ".join(remaining[1:]), "quiet")
        say("  valid so far, nothing was run.", "quiet")
    return None


def _show(value):
    if isinstance(value, list):
        return ", ".join(_show(v) for v in value)
    if hasattr(value, "x"):
        from .parsing import format_point
        return format_point(value)
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _did_you_mean(registry, token, limit=4):
    """Closest verb names, so a typo suggests its fix."""
    return _closest(registry.names(), token, limit)


def _emit_units(v):
    """Show or set the unit schema.

    This is FreeCAD's own setting, not a second one -- switching here moves
    the whole application, so the command line and the property editor agree
    on what 3/8" means.
    """
    from . import units as U
    engine = v.get("_engine")
    wanted = v.get("schema")
    if not wanted:
        if engine is None:
            return None
        current = U.current_name()
        engine.bus.emit(_bus.INFO,
                        f"{current} -- a bare number means {U.preferred()}")
        for name in U.schemas():
            active = name == current
            engine.bus.emit(_bus.INFO, f"  {'*' if active else ' '} {name}",
                            role="ok" if active else "quiet")
        return None
    name = U.set_schema(wanted)
    _say(v, f"{name} -- a bare number now means {U.preferred()}")
    return None


def _emit_man(v):
    """The manual. Bare, it lists what exists; given a topic, it describes
    one thing in full -- every step with its kind, unit and choices, the
    inline options, and the command it maps to.

    Most of that is generated from FreeCAD's own property documentation, so
    a verb nobody hand-wrote still has a page worth reading.
    """
    engine = v.get("_engine")
    if engine is None:
        return None
    topic = v.get("topic")
    if not topic:
        return _list_verbs(engine)
    verb = REGISTRY.get(topic)
    if verb is None:
        raise RuntimeError(f"no manual entry for {topic}")
    def say(line, role="info"):
        engine.bus.emit(_bus.INFO, line, role=role)

    say("NAME", "head")
    alias = f"  ({', '.join(verb.aliases)})" if verb.aliases else ""
    say(f"    {verb.name}{alias} -- {verb.doc}")

    say("SYNOPSIS", "head")
    parts = [verb.name]
    for step in verb.steps:
        token = f"<{step.id}>"
        parts.append(f"[{token}]" if step.optional else token)
        if step.repeat:
            parts.append("...")
    say("    " + " ".join(parts), "ok")

    if verb.steps:
        say("ARGUMENTS", "head")
        for i, step in enumerate(verb.steps, 1):
            unit = f" in {step.unit}" if step.kind == "quantity" and step.unit else ""
            flags = []
            if step.optional:
                flags.append("optional")
            if step.repeat:
                flags.append(f"repeats, min {step.min_count}")
            tail = f"   [{', '.join(flags)}]" if flags else ""
            say(f"    {i}. {step.id} <{step.kind}{unit}>{tail}")
            if step.prompt and step.prompt != step.id:
                say(f"       {step.prompt}")
            if step.choices:
                say("       one of:")
                groups = _curation.current().choice_groups(verb.name, verb)
                if groups:
                    for heading, names in groups:
                        say(f"         {heading or 'ungrouped'}", "head")
                        for row in _columns(names, width=64):
                            say(f"           {row}", "quiet")
                else:
                    for row in _columns(step.choices):
                        say(f"       {row}", "quiet")
            for opt in step.options:
                say(f"       option {opt.name}: {opt.doc}")

    curated = _curation.current()
    if verb.gui_command:
        say("GUI", "head")
        say(f"    {verb.gui_command}")
        toolbar, menu = curated.placement(verb.gui_command)
        if toolbar:
            say(f"    toolbar   {toolbar}", "quiet")
        if menu:
            say(f"    menu      {menu}", "quiet")

    say("SEE ALSO", "head")
    # What FreeCAD put beside this one. A toolbar is somebody's answer to
    # "what goes with what", and it is a better answer than a guess from
    # the names would be.
    near = curated.neighbours(REGISTRY, verb)
    if near:
        say(f"    {', '.join(near)}", "ok")
    say("    man     (list every command)")
    return None


def _columns(items, width=72, gap=2):
    """Lay a list out down columns that fit the width.

    A family can have forty members, and forty names joined by commas is one
    line nobody reads -- least of all in a dock somebody has dragged to six
    lines tall.
    """
    items = [str(i) for i in items]
    if not items:
        return []

    def fits(columns):
        """Column widths for a candidate count, or None if too wide."""
        height = -(-len(items) // columns)          # ceiling division
        widths = []
        for start in range(0, len(items), height):
            column = items[start:start + height]
            widths.append(max(len(i) for i in column) + gap)
        return widths if sum(widths) - gap <= width else None

    # Widest layout that still fits. One column always does.
    for columns in range(min(len(items), width // 2), 1, -1):
        widths = fits(columns)
        if widths:
            break
    else:
        return items

    height = -(-len(items) // len(widths))
    grid = [items[i:i + height] for i in range(0, len(items), height)]
    rows = []
    for r in range(height):
        cells = [column[r].ljust(widths[c])
                 for c, column in enumerate(grid) if r < len(column)]
        rows.append("".join(cells).rstrip())
    return rows


def _list_verbs(engine):
    """The index. Hand-written verbs first: they are the ones with grammar."""
    from .verbs import REGISTRY as _R
    hand, generated = [], []
    for name in REGISTRY.names():
        verb = REGISTRY.get(name)
        (generated if verb.emit.__module__.endswith("factory") else hand
         ).append(verb)
    engine.bus.emit(_bus.INFO, f"{len(hand)} hand-written commands:")
    for verb in hand:
        alias = f" ({verb.aliases[0]})" if verb.aliases else ""
        engine.bus.emit(_bus.INFO, f"  {verb.name + alias:<18} {verb.doc}")
    if generated:
        engine.bus.emit(
            _bus.INFO,
            f"and {len(generated)} generated from FreeCAD's registries. "
            "man <name> describes any of them.")
    return None


ALIAS_PATH = _paths.data("aliases")


def load_aliases():
    """Read the user's aliases and attach them to their verbs."""
    try:
        with open(_paths.readable(ALIAS_PATH, "aliases"),
                  encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()
                     and not ln.startswith("#")]
    except OSError:
        return 0
    count = 0
    for line in lines:
        name, _, target = line.partition("=")
        verb = REGISTRY.get(target.strip())
        if verb is None or not name.strip():
            continue
        if name.strip() not in verb.aliases:
            verb.aliases.append(name.strip())
            REGISTRY.add(verb)      # re-index the alias table
            count += 1
    return count


# What `shortcuts import` wrote, marked so `shortcuts drop` can find it
# again. Without it drop had to guess, and its guess -- "does this look
# like a key chord" -- is true of any alias of two or more letters, so it
# deleted everything the operator had ever written.
CHORD_MARK = "\t# chord"


def _save_aliases(pairs, imported=()):
    imported = set(imported)
    try:
        _paths.ensure(ALIAS_PATH)
        with open(ALIAS_PATH, "w", encoding="utf-8") as fh:
            fh.write("# fccli aliases -- <name>=<command>\n")
            for name, target in sorted(pairs.items()):
                mark = CHORD_MARK if name in imported else ""
                fh.write(f"{name}={target}{mark}\n")
    except OSError:
        pass


def _read_aliases():
    """The alias file, as (name -> command, names `shortcuts import` wrote)."""
    pairs, imported = {}, set()
    try:
        with open(_paths.readable(ALIAS_PATH, "aliases"),
                  encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                marked = line.endswith(CHORD_MARK)
                if marked:
                    line = line[:-len(CHORD_MARK)]
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, target = line.partition("=")
                name, target = name.strip(), target.strip()
                if name and target:
                    pairs[name] = target
                    if marked:
                        imported.add(name)
    except OSError:
        pass
    return pairs, imported


def _user_aliases():
    """Everything in the alias file, as name -> command."""
    return _read_aliases()[0]


def _emit_alias(v):
    """Shell-style aliases. Bare lists them; name plus target defines one.

    Everyone arrives with some other tool's abbreviations in their fingers,
    and every verb here is a name someone might want to spell differently.
    """
    engine = v.get("_engine")
    name, target = v.get("name"), v.get("command")
    pairs, imported = _read_aliases()
    if not name:
        if engine is None:
            return None
        builtin = [(a, verb) for verb in
                   (REGISTRY.get(n) for n in REGISTRY.names())
                   for a in verb.aliases if a not in pairs]
        engine.bus.emit(_bus.INFO, f"{len(pairs)} of your own:")
        for k, t in sorted(pairs.items()):
            engine.bus.emit(_bus.INFO, f"  {k:<12} {t}")
        engine.bus.emit(_bus.INFO,
                        f"and {len(builtin)} built in (man <name> shows them)")
        return None
    if not target:
        raise RuntimeError(f"alias {name}=? -- give a command to alias to")
    verb = REGISTRY.get(target)
    if verb is None:
        raise RuntimeError(f"unknown command: {target}")
    if REGISTRY.get(name) is not None and REGISTRY.get(name).name != verb.name:
        raise RuntimeError(f"{name} is already {REGISTRY.get(name).name}")
    if name not in verb.aliases:
        verb.aliases.append(name)
        REGISTRY.add(verb)
    pairs[name] = verb.name
    # Writing one by hand makes it the operator's, whatever import called
    # it before. Everyone else's mark survives.
    _save_aliases(pairs, imported - {name})
    _say(v, f"{name} -> {verb.name}")
    return None


def _emit_unalias(v):
    name = v["name"]
    pairs, imported = _read_aliases()
    if name not in pairs:
        raise RuntimeError(f"no alias {name}")
    verb = REGISTRY.get(pairs[name])
    if verb is not None and name in verb.aliases:
        verb.aliases.remove(name)
    del pairs[name]
    _save_aliases(pairs, imported - {name})
    REGISTRY.reindex()
    _say(v, f"removed {name}")
    return None


def _emit_history(v):
    """Show the ring, trim it, or empty it.

    clear wipes the screen; this is what survives that. The two are
    different enough to be different words.
    """
    engine = v.get("_engine")
    if engine is None:
        return None
    session = getattr(engine, "session", None)
    arg = (v.get("what") or "").strip().lower()

    if arg in ("clear", "wipe", "forget"):
        if session is not None:
            session.history.forget()
        _say(v, "history forgotten")
        return None

    limit = None
    if arg:
        if not arg.isdigit():
            raise RuntimeError("history takes a count, or the word clear")
        limit = int(arg)
    engine.bus.emit(_bus.INFO, f"@@history@@{limit or ''}")
    return None


def _emit_quit(v):
    """Leave FreeCAD.

    Closing the application prompts once per modified document. quit lists
    what is unsaved and refuses; quit! discards it. Same shape as close, so
    the answer to "save changes?" is given on the command line rather than
    in a modal that blocks every other key.
    """
    dirty = dirty_documents()
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
    name="shortcuts", transactional=False,
    doc="Offer FreeCAD's key chords as aliases: A,X becomes ax.",
    steps=[Step("what", CHOICE, "Do what", optional=True,
                choices=["list", "why", "import", "drop"])],
    emit=_emit_shortcuts,
))

REGISTRY.add(Verb(
    name="describe", transactional=False, aliases=["desc", "what"],
    doc="Read an object out as text. Bare, it lists what the document holds.",
    steps=[Step("object", TEXT, "Object", optional=True,
                completes="objects")],
    emit=_emit_describe,
))

REGISTRY.add(Verb(
    name="screenshot", transactional=False, aliases=["shot", "capture"],
    doc="Save a picture of the model and print the path.",
    steps=[
        Step("path", PATH, "Where to save it", optional=True),
        Step("width", QUANTITY, "Width in pixels", unit="", optional=True,
             options=[Option("Window", "grab the whole application window"),
                      Option("Fit", "zoom to fit before capturing"),
                      Option("Transparent", "transparent background")]),
        Step("height", QUANTITY, "Height in pixels", unit="", optional=True),
    ],
    emit=_emit_screenshot,
))

REGISTRY.add(Verb(
    name="use", transactional=False, aliases=["scope"],
    doc="Narrow what Tab offers to one domain. 'use off' clears it.",
    steps=[Step("domain", TEXT, "Domain", optional=True,
                completes="domains")],
    emit=_emit_scope,
))

REGISTRY.add(Verb(
    name="commands", transactional=False, aliases=["cmds"],
    doc="List the domains, or the commands in one.",
    steps=[Step("domain", TEXT, "Domain", optional=True,
                completes="domains")],
    emit=_emit_commands,
))

REGISTRY.add(Verb(
    name="check", transactional=False, aliases=["whatif", "dry", "ck"],
    doc="Validate a command without running it.",
    steps=[Step("line", TEXT, "Command to check", raw=True,
                completes="verbs")],
    emit=_emit_check,
))

REGISTRY.add(Verb(
    name="units", transactional=False,
    doc="Show or set the unit schema, e.g. units imperialbuilding",
    steps=[Step("schema", TEXT, "Unit schema", optional=True,
                completes="schemas")],
    emit=_emit_units,
))

REGISTRY.add(Verb(
    name="man", transactional=False, aliases=["help", "?", "h"],
    doc="List the commands, or describe one in full.",
    steps=[Step("topic", TEXT, "Manual page", optional=True,
                completes="verbs")],
    emit=_emit_man,
))

REGISTRY.add(Verb(
    name="alias", transactional=False,
    doc="List your aliases, or define one: alias b box",
    steps=[Step("name", TEXT, "Alias", optional=True),
           Step("command", TEXT, "Command it stands for", optional=True,
                completes="verbs")],
    emit=_emit_alias,
))

REGISTRY.add(Verb(
    name="unalias", transactional=False,
    doc="Remove one of your aliases.",
    steps=[Step("name", TEXT, "Alias to remove", completes="aliases")],
    emit=_emit_unalias,
))

REGISTRY.add(Verb(
    name="history", transactional=False, record=False, aliases=["hist"],
    doc="List recalled commands, or 'history clear' to forget them.",
    steps=[Step("what", TEXT, "A count, or clear", optional=True)],
    emit=_emit_history,
))

REGISTRY.add(Verb(
    name="quit", transactional=False, aliases=["exit", "qa"],
    doc="Leave FreeCAD. Refuses on unsaved work; quit! discards it.",
    steps=[], emit=_emit_quit,
))

