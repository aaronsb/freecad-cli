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
        line = raw.split("#", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
        if line:
            lines.append(line)
    return front, lines


def _steps(front):
    from .patches import _build_step
    out = []
    for raw in front.get("steps") or []:
        if not isinstance(raw, dict) or "id" not in raw:
            raise ValueError(f"a step needs an id: {raw!r}")
        step = _build_step(raw)
        if step is not None:
            out.append(step)
    return out


def _typed(steps, values):
    """Each answer as the text a person would have typed for it."""
    out = {}
    for step in steps:
        v = values.get(step.id)
        if v is None:
            v = step.default
        if v is None:
            out[step.id] = ""
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
    that still wants input. The lines are not recorded in history."""
    errors = []
    stop = engine.bus.subscribe(
        lambda m: errors.append(m.text) if m.kind == _bus.ERROR else None)
    engine.suppress_record += 1
    try:
        for n, raw in enumerate(lines, 1):
            line = substitute(raw, typed)
            errors.clear()
            engine.submit(line)
            if errors:
                raise RuntimeError(f"{label} stopped at line {n}: {line}")
            if engine.state != "idle":
                wanted = engine.current_step()
                engine.cancel()
                raise RuntimeError(
                    f"{label} stopped at line {n}: {line} -- still wants "
                    f"{wanted.prompt if wanted else 'input'}")
    finally:
        engine.suppress_record -= 1
        stop()
    return len(lines)


def run_macro(path):
    """FreeCAD's Python tier, run the way its macro manager runs a file."""
    try:
        import FreeCADGui as Gui
        Gui.doCommand(f"exec(open({path!r}, encoding='utf-8').read())")
        return
    except Exception:
        pass            # no GUI console to run it through; run it here
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
        sitting = registry.get(name)
        if sitting is not None and getattr(sitting, "script", None) != path:
            notes.append(f"bin/{f}: {name} is taken by another verb")
            continue
        try:
            verb = build(name, path)
        except Exception as exc:
            notes.append(f"bin/{f}: {exc}")
            continue
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
    line = " ".join([verb.name] + list(args))
    # Borrow the registry for the length of one run, so the script's
    # declared steps are collected the way any verb's are.
    registry = engine.registry
    sitting = registry.get(verb.name)
    if sitting is not None and getattr(sitting, "script", None) != real:
        verb.name = f"_{verb.name}"
        line = " ".join([verb.name] + list(args))
    registry.add(verb)
    try:
        errors = []
        stop = engine.bus.subscribe(
            lambda m: errors.append(m.text) if m.kind == _bus.ERROR else None)
        try:
            engine.submit(line)
        finally:
            stop()
        if engine.state != "idle":
            wanted = engine.current_step()
            engine.cancel()
            raise RuntimeError(f"{virtual} wants {wanted.prompt if wanted else 'more'}; "
                               f"give it inline")
        if errors:
            raise RuntimeError(errors[-1])
    finally:
        if sitting is None or getattr(sitting, "script", None) == real:
            registry.remove(verb.name) if hasattr(registry, "remove") else None
        else:
            registry.remove(verb.name) if hasattr(registry, "remove") else None
            registry.add(sitting)
    return None
