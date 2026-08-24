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
    name="fit", transactional=False, aliases=["zoom", "zf"], gui_command="Std_ViewFitAll",
    doc="Zoom to fit everything in the view.",
    steps=[], emit=_emit_fit,
))

REGISTRY.add(Verb(
    name="delete", aliases=["del"], gui_command="Std_Delete",
    doc="Delete the selected objects.",
    steps=[], emit=_emit_delete,
))


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

    say = lambda text: engine.bus.emit(_b.INFO, text)
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
        say(f"unknown command: {token}")
        if near:
            say("  did you mean: " + ", ".join(near))
        return None
    if len(hits) > 1:
        say(f"ambiguous: {token} matches " + ", ".join(hits))
        return None

    verb = engine.registry.get(hits[0])
    say(f"{verb.name} -- {verb.doc}")

    result = seen["result"]
    if result is not None:
        # An argument can be rejected and the command still complete, when
        # what it was rejected for was optional. Say so rather than
        # reporting a clean run.
        for text in seen["errors"]:
            say(f"  ignored: {text}")
        say(f"  would run:  {result.data['replay']}")
        values = result.data.get("values") or {}
        for step in verb.steps:
            if step.id in values:
                say(f"    {step.id:<12} {_show(values[step.id])}")
        flags = [k for k, on in (result.data.get("flags") or {}).items()
                 if on and k != "force"]
        if flags:
            say("    options      " + ", ".join(flags))
        if verb.creates:
            say(f"  would create: {verb.creates}")
        say("  nothing was run.")
        return None

    if seen["errors"]:
        for text in seen["errors"]:
            say(f"  rejected: {text}")
        return None

    prompt = seen["prompt"]
    if prompt is not None:
        remaining = [st.id for st in shadow.verb.steps[shadow.step_index:]] \
            if shadow.verb else []
        say(f"  incomplete -- still wants: {prompt.text}")
        if len(remaining) > 1:
            say("    then: " + ", ".join(remaining[1:]))
        say("  valid so far, nothing was run.")
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
    import difflib
    return difflib.get_close_matches(token.lower(), registry.names(),
                                     n=limit, cutoff=0.6)


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
            mark = "*" if name == current else " "
            engine.bus.emit(_bus.INFO, f"  {mark} {name}")
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
    say = lambda line: engine.bus.emit(_bus.INFO, line)

    say(f"NAME")
    alias = f"  ({', '.join(verb.aliases)})" if verb.aliases else ""
    say(f"    {verb.name}{alias} -- {verb.doc}")

    say("SYNOPSIS")
    parts = [verb.name]
    for step in verb.steps:
        token = f"<{step.id}>"
        parts.append(f"[{token}]" if step.optional else token)
        if step.repeat:
            parts.append("...")
    say("    " + " ".join(parts))

    if verb.steps:
        say("ARGUMENTS")
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
                say(f"       one of: {', '.join(step.choices)}")
            for opt in step.options:
                say(f"       option {opt.name}: {opt.doc}")

    if verb.gui_command:
        say("GUI")
        say(f"    {verb.gui_command}")
    say("SEE ALSO")
    say("    man     (list every command)")
    return None


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


ALIAS_PATH = os.path.join(os.path.expanduser("~"), ".local", "share",
                          "FreeCAD", "fccli", "aliases")


def load_aliases():
    """Read the user's aliases and attach them to their verbs."""
    try:
        with open(ALIAS_PATH, encoding="utf-8") as fh:
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


def _save_aliases(pairs):
    try:
        os.makedirs(os.path.dirname(ALIAS_PATH), exist_ok=True)
        with open(ALIAS_PATH, "w", encoding="utf-8") as fh:
            fh.write("# fccli aliases -- <name>=<command>\n")
            for name, target in sorted(pairs.items()):
                fh.write(f"{name}={target}\n")
    except OSError:
        pass


def _user_aliases():
    """Everything in the alias file, as name -> command."""
    pairs = {}
    try:
        with open(ALIAS_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, target = line.partition("=")
                if name.strip() and target.strip():
                    pairs[name.strip()] = target.strip()
    except OSError:
        pass
    return pairs


def _emit_alias(v):
    """Shell-style aliases. Bare lists them; name plus target defines one.

    Everyone arrives with some other tool's abbreviations in their fingers,
    and every verb here is a name someone might want to spell differently.
    """
    engine = v.get("_engine")
    name, target = v.get("name"), v.get("command")
    pairs = _user_aliases()
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
    _save_aliases(pairs)
    _say(v, f"{name} -> {verb.name}")
    return None


def _emit_unalias(v):
    name = v["name"]
    pairs = _user_aliases()
    if name not in pairs:
        raise RuntimeError(f"no alias {name}")
    verb = REGISTRY.get(pairs[name])
    if verb is not None and name in verb.aliases:
        verb.aliases.remove(name)
    del pairs[name]
    _save_aliases(pairs)
    REGISTRY.reindex()
    _say(v, f"removed {name}")
    return None


def _emit_history(v):
    """Show the ring. clear wipes the screen; this is what survives it."""
    engine = v.get("_engine")
    if engine is None:
        return None
    engine.bus.emit(_bus.INFO, "@@history@@")
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


ALIAS_PATH = os.path.join(os.path.expanduser("~"), ".local", "share",
                          "FreeCAD", "fccli", "aliases")


def load_aliases():
    """Read the user's aliases and attach them to their verbs."""
    try:
        with open(ALIAS_PATH, encoding="utf-8") as fh:
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


def _save_aliases(pairs):
    try:
        os.makedirs(os.path.dirname(ALIAS_PATH), exist_ok=True)
        with open(ALIAS_PATH, "w", encoding="utf-8") as fh:
            fh.write("# fccli aliases -- <name>=<command>\n")
            for name, target in sorted(pairs.items()):
                fh.write(f"{name}={target}\n")
    except OSError:
        pass


def _user_aliases():
    """Everything in the alias file, as name -> command."""
    pairs = {}
    try:
        with open(ALIAS_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, _, target = line.partition("=")
                if name.strip() and target.strip():
                    pairs[name.strip()] = target.strip()
    except OSError:
        pass
    return pairs


def _emit_alias(v):
    """Shell-style aliases. Bare lists them; name plus target defines one.

    Everyone arrives with some other tool's abbreviations in their fingers,
    and every verb here is a name someone might want to spell differently.
    """
    engine = v.get("_engine")
    name, target = v.get("name"), v.get("command")
    pairs = _user_aliases()
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
    _save_aliases(pairs)
    _say(v, f"{name} -> {verb.name}")
    return None


def _emit_unalias(v):
    name = v["name"]
    pairs = _user_aliases()
    if name not in pairs:
        raise RuntimeError(f"no alias {name}")
    verb = REGISTRY.get(pairs[name])
    if verb is not None and name in verb.aliases:
        verb.aliases.remove(name)
    del pairs[name]
    _save_aliases(pairs)
    REGISTRY.reindex()
    _say(v, f"removed {name}")
    return None


def _emit_history(v):
    """Show the ring. clear wipes the screen; this is what survives it."""
    engine = v.get("_engine")
    if engine is None:
        return None
    engine.bus.emit(_bus.INFO, "@@history@@")
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
    name="check", transactional=False, aliases=["whatif", "dry", "ck"],
    doc="Validate a command without running it.",
    steps=[Step("line", TEXT, "Command to check", raw=True)],
    emit=_emit_check,
))

REGISTRY.add(Verb(
    name="units", transactional=False,
    doc="Show or set the unit schema, e.g. units imperialbuilding",
    steps=[Step("schema", TEXT, "Unit schema", optional=True)],
    emit=_emit_units,
))

REGISTRY.add(Verb(
    name="man", transactional=False, aliases=["help", "?", "h"],
    doc="List the commands, or describe one in full.",
    steps=[Step("topic", TEXT, "Manual page", optional=True)],
    emit=_emit_man,
))

REGISTRY.add(Verb(
    name="alias", transactional=False,
    doc="List your aliases, or define one: alias b box",
    steps=[Step("name", TEXT, "Alias", optional=True),
           Step("command", TEXT, "Command it stands for", optional=True)],
    emit=_emit_alias,
))

REGISTRY.add(Verb(
    name="unalias", transactional=False,
    doc="Remove one of your aliases.",
    steps=[Step("name", TEXT, "Alias to remove")],
    emit=_emit_unalias,
))

REGISTRY.add(Verb(
    name="history", transactional=False, aliases=["hist"],
    doc="List recalled commands. clear wipes the screen, not this.",
    steps=[], emit=_emit_history,
))

REGISTRY.add(Verb(
    name="quit", transactional=False, aliases=["exit", "qa"],
    doc="Leave FreeCAD. Refuses on unsaved work; quit! discards it.",
    steps=[], emit=_emit_quit,
))

