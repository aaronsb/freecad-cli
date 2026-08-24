# SPDX-License-Identifier: LGPL-2.1-or-later

"""Scripts: a file of command lines, run as one verb (ADR-601).

A `.fccli` file is YAML frontmatter and a body of lines the parser
already accepts. The frontmatter declares what the script asks for, in
the step syntax `PATCH["verbs"]` uses, and the body refers to the answers
as `$id`::

    ---
    doc: A square plinth with a cylinder on it.
    steps:
      - {id: size, kind: quantity, prompt: Plinth size, unit: mm}
      - {id: height, kind: quantity, prompt: Height, unit: mm, default: 20}
    ---
    box 0,0,0 $size $size $height
    cylinder $size/4 $height

A script in `/bin` registers as a verb by file name, so it completes,
prompts for its arguments, and replays from history like any verb.
Elsewhere it runs by path -- `run plinth/tower 20` or `./tower 20` --
with its arguments inline.

The runner feeds the body to the engine one line at a time and stops at
the first error, or at a line that still wants input. The call is one
history line; the lines inside are not recorded. A script is not undone
as a unit: each line remains the FreeCAD undo step it is today.

`.FCMacro` is the Python tier, run the way FreeCAD's macro manager runs
one. This format is experimental, as the ADR says.
"""

import os
import re

from . import bus as _bus
from . import root as _root
from .grammar import POINT, QUANTITY, Verb
from .parsing import format_point, format_quantity

FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
VAR = re.compile(r"\$\{(\w+)\}|\$(\w+)")
COMMENT = re.compile(r"(^|\s)#.*$")
MAX_DEPTH = 8
EXT = ".fccli"
MACRO = ".FCMacro"


def parse(text):
    """(frontmatter dict, body lines) of a script. Comments and blank
    lines are dropped; a line is a command line."""
    front = {}
    m = FRONT.match(text)
    if m:
        import yaml
        front = yaml.safe_load(m.group(1)) or {}
        if not isinstance(front, dict):
            raise ValueError("frontmatter is not a mapping")
        text = text[m.end():]
    lines = []
    for raw in text.splitlines():
        # A comment starts a line or follows whitespace; a # inside an
        # argument -- a file called a#b.FCStd -- is the argument's.
        line = COMMENT.sub("", raw).strip()
        if line:
            lines.append(line)
    return front, lines


def _steps(front):
    from .patches import KINDS, _build_step
    out = []
    for raw in front.get("steps") or []:
        if not isinstance(raw, dict) or "id" not in raw:
            raise ValueError(f"a step needs an id: {raw!r}")
        if raw.get("kind", "text") not in KINDS:
            raise ValueError(f"step {raw['id']}: kind {raw.get('kind')!r} is "
                             f"not one of {sorted(KINDS)}")
        if raw.get("optional") and raw.get("default") is None:
            # An unanswered optional would substitute nothing and shift
            # every argument after it on the line.
            raise ValueError(f"step {raw['id']}: optional needs a default")
        step = _build_step(raw)
        if step is not None:
            out.append(step)
    return out


def _typed(steps, values):
    """Each answer as the text it arrived as.

    The engine keeps the typed form of every answer (`_typed`), and that
    is what goes into the line: a person who typed `2in` gets `2in`. A
    default the engine filled in arrives as its bare number and is
    written in the step's own unit. A value with no typed form -- one an
    option set -- is rendered as the parser would print it.
    """
    typed = values.get("_typed") or {}
    out = {}
    for step in steps:
        v = values.get(step.id)
        text = typed.get(step.id)
        if isinstance(text, list):
            text = " ".join(text)
        if v is None or (v == step.default and step.default is not None
                         and text in (None, str(step.default))):
            d = step.default
            out[step.id] = ("" if d is None else
                            f"{d}{step.unit}" if step.kind == QUANTITY
                            and isinstance(d, (int, float)) else str(d))
        elif text is not None:
            out[step.id] = text
        elif step.kind == POINT and hasattr(v, "x"):
            out[step.id] = format_point(v)
        elif step.kind == QUANTITY and isinstance(v, (int, float)):
            out[step.id] = format_quantity(v, step.unit)
        elif isinstance(v, list):
            out[step.id] = ",".join(getattr(o, "Label", str(o)) for o in v)
        else:
            out[step.id] = str(v)
    return out


def substitute(line, typed):
    def one(m):
        key = m.group(1) or m.group(2)
        if key not in typed:
            raise RuntimeError(f"${key} is not one of this script's arguments")
        return typed[key]
    return VAR.sub(one, line)


def run_lines(engine, lines, typed, label):
    """Feed lines to the engine, stopping at the first error or at a line
    that still wants input. The lines are not recorded in history, and
    the script call stays what an empty Enter repeats."""
    if engine.script_depth >= MAX_DEPTH:
        raise RuntimeError(f"{label}: scripts {MAX_DEPTH} deep; one is "
                           f"running itself")
    errors = []
    stop = engine.bus.subscribe(
        lambda m: errors.append(m.text) if m.kind == _bus.ERROR else None)
    hint = engine.repeat_hint
    engine.suppress_record += 1
    engine.script_depth += 1
    try:
        for n, raw in enumerate(lines, 1):
            try:
                line = substitute(raw, typed)
            except RuntimeError as exc:
                raise RuntimeError(f"{label} line {n}: {exc}")
            errors.clear()
            engine.submit(line)
            # A line can error and still be collecting -- a bad value at
            # the second of three steps -- so the prompt is closed first.
            wanted = engine.current_step() if engine.state != "idle" else None
            if engine.state != "idle":
                engine.cancel()
            if errors:
                raise RuntimeError(f"{label} stopped at line {n}: {line}")
            if wanted is not None:
                raise RuntimeError(
                    f"{label} stopped at line {n}: {line} -- still wants "
                    f"{wanted.prompt}")
    finally:
        # Counters first: cancel() reaches the picker, which is the one
        # call here that could raise, and a raise must not leave history
        # recording off for the session.
        engine.script_depth -= 1
        engine.suppress_record -= 1
        engine.repeat_hint = hint
        stop()
        if engine.state != "idle":
            engine.cancel()
    return len(lines)


def run_macro(path):
    """FreeCAD's Python tier, run the way its macro manager runs a file.

    Through the GUI's console when there is one, so it shows there; as
    Python here when there is none. A macro that raises is one failure,
    reported once: the two are chosen by whether a console exists, never
    by whether the macro succeeded.
    """
    runner = None
    try:
        import FreeCADGui as Gui
        if getattr(Gui, "getMainWindow", None) and Gui.getMainWindow() is not None:
            runner = Gui.doCommand
    except Exception:
        runner = None
    if runner is not None:
        runner(f"exec(open({path!r}, encoding='utf-8').read())")
        return
    with open(path, encoding="utf-8") as fh:
        code = compile(fh.read(), path, "exec")
    exec(code, {"__name__": "__main__", "__file__": path})


def build(name, path):
    """A verb from a script file. Read now for its declaration, read
    again at each run for its lines, so an edit takes effect next time."""
    with open(path, encoding="utf-8") as fh:
        front, _lines = parse(fh.read())
    steps = _steps(front)

    def emit(values):
        engine = values.get("_engine")
        with open(path, encoding="utf-8") as fh:
            _front, lines = parse(fh.read())
        typed = _typed(steps, values)
        return run_lines(engine, lines, typed, name)

    return Verb(name=front.get("verb") or name, steps=steps, emit=emit,
                aliases=list(front.get("aliases") or []),
                doc=front.get("doc") or f"Runs {os.path.basename(path)}.",
                transactional=False, script=path)


def register(registry, base=None):
    """Every script in /bin, as a verb by file name. A taken name is
    skipped and said, never displaced. Returns (added, notes)."""
    base = base or _root.root()
    bin_dir = os.path.join(base, "bin")
    added, notes = [], []
    if not os.path.isdir(bin_dir):
        return added, notes
    for f in sorted(os.listdir(bin_dir)):
        if not f.endswith(EXT):
            continue
        name = f[: -len(EXT)]
        path = os.path.join(bin_dir, f)
        try:
            verb = build(name, path)
        except Exception as exc:
            notes.append(f"bin/{f}: {exc}")
            continue
        # The name it will register under, and every alias: each must be
        # free or already this script's. Registry.add would take them.
        sitting = registry.get(verb.name)
        if sitting is not None and getattr(sitting, "script", None) != path:
            notes.append(f"bin/{f}: {verb.name} is taken by another verb")
            continue
        kept = []
        for alias in verb.aliases:
            other = registry.get(alias)
            if other is not None and getattr(other, "script", None) != path:
                notes.append(f"bin/{f}: alias {alias} is taken; dropped")
                continue
            kept.append(alias)
        verb.aliases = kept
        registry.add(verb)
        added.append(verb.name)
    return added, notes


def run_path(engine, cwd, path, args):
    """Run a script or macro by path, arguments inline."""
    virtual = _root.resolve(cwd, path)
    real = _root.real(virtual)
    if not os.path.isfile(real):
        raise RuntimeError(f"{virtual}: no such file")
    if real.endswith(MACRO):
        if args:
            raise RuntimeError("a macro takes no arguments here")
        run_macro(real)
        return None
    if not real.endswith(EXT):
        raise RuntimeError(f"{virtual}: not a script (.fccli) or macro (.FCMacro)")
    verb = build(os.path.basename(real)[: -len(EXT)], real)
    verb.aliases = []               # a transient claims no alias
    registry = engine.registry
    sitting = registry.get(verb.name)
    transient = None
    if sitting is not None and getattr(sitting, "script", None) == real:
        # This file is already a bin verb: run that one, add nothing.
        verb = sitting
    else:
        if sitting is not None:
            verb.name = f"_{verb.name}"     # a name nothing else has
        transient = verb
        registry.add(transient)
    line = " ".join([verb.name] + list(args))
    hint = engine.repeat_hint
    errors = []
    stop = engine.bus.subscribe(
        lambda m: errors.append(m.text) if m.kind == _bus.ERROR else None)
    # The run call is the history line; the transient's own result is not.
    engine.suppress_record += 1
    try:
        engine.submit(line)
        wanted = engine.current_step() if engine.state != "idle" else None
        if engine.state != "idle":
            engine.cancel()
        if errors:
            raise RuntimeError(errors[-1])
        if wanted is not None:
            raise RuntimeError(f"{virtual} wants {wanted.prompt}; give it inline")
    finally:
        engine.suppress_record -= 1
        engine.repeat_hint = hint
        stop()
        if transient is not None:
            registry.remove(transient.name)
    return None
