"""Build verbs from the generated descriptor.

Three tiers, in rising order of how much someone had to write by hand:

  tier 0   every registered command, as a zero-step verb that runs it.
           Free, complete, and no schema involved.
  tier 1   every parametric type, as a verb whose steps come from the type's
           own properties. Generated. Needs no command link, because the
           type names itself and carries its parameters.
  tier 2   the same verbs after patches -- ordering, point collapsing,
           aliases, custom construction.

The command registry contributes labels, icons and grouping to tier 1 where
a trustworthy link exists. It is a garnish, not a dependency: linking a
command to a type cannot be done reliably by machine, and the reframe that
makes this work is that tier 1 never needed it.
"""

import json
import os
import re

from . import bus as _bus
from .grammar import (CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT,
                      Option, Registry, Step, Verb)
from .patches import load_patches

DESCRIPTOR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "descriptor.json")

KIND_MAP = {
    "quantity": QUANTITY, "point": POINT, "choice": CHOICE,
    "selection": SELECTION, "text": TEXT, "path": PATH,
}

# Types that exist to exercise FreeCAD's own machinery.
NOISE_TYPES = re.compile(r"^(App::FeatureTest|Test::|App::Origin|"
                         r"App::(Placement|Material)?Object(Python)?$)")


def load_descriptor(path=DESCRIPTOR):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- tier 1

def _step_from_param(param):
    """One property becomes one getter."""
    kind = KIND_MAP.get(param["kind"])
    if kind is None:
        return None                      # flags become options, not steps
    prompt = param.get("doc") or param["name"]
    step = Step(param["name"], kind, prompt.rstrip("."),
                optional=True,
                unit=param.get("unit", "mm"))
    if kind == CHOICE:
        step.choices = param.get("choices", [])
    return step


def _options_from_flags(params):
    """Booleans read better as inline keywords than as prompts."""
    out = []
    for p in params:
        if p["kind"] != "flag":
            continue
        out.append(Option(p["name"], p.get("doc", "") or p["name"],
                          _flag_setter(p["name"])))
    return out


def _flag_setter(name):
    def action(engine):
        engine.flags[name] = True
        return False
    return action


def _emit_type(tid, params):
    """Construct the object and write every collected property onto it."""
    def emit(values):
        import FreeCAD as App
        doc = App.ActiveDocument or App.newDocument()
        obj = doc.addObject(tid, tid.split("::")[-1])
        flags = values.get("_flags", {})
        for p in params:
            got = values.get(p["name"])
            if got is None and p["name"] not in flags:
                continue
            try:
                setattr(obj, p["name"],
                        True if got is None else got)
            except Exception:
                pass
        doc.recompute()
        try:
            import FreeCADGui as Gui
            if Gui.ActiveDocument is not None:
                Gui.ActiveDocument.update()
            Gui.updateGui()
        except Exception:
            pass
        return obj
    return emit


def build_type_verb(name, entry, meta=None):
    params = entry["params"]
    steps = [s for s in (_step_from_param(p) for p in params) if s is not None]
    if not steps:
        return None
    options = _options_from_flags(params)
    if options:
        steps[-1].options = list(steps[-1].options) + options
    meta = meta or {}
    return Verb(
        name=name,
        steps=steps,
        emit=_emit_type(entry["type"], params),
        doc=meta.get("tooltip") or f"Create a {entry['type']}.",
        gui_command=meta.get("name"),
    )


# ---------------------------------------------------------------- tier 0

def build_command_verb(command):
    """A zero-step verb that just runs the command, dialogs and all."""
    name = command["name"]

    def emit(values):
        import FreeCADGui as Gui
        Gui.runCommand(name)
        return None

    label = command.get("label") or name
    return Verb(name=_slug(label), steps=[], emit=emit,
                doc=command.get("tooltip") or label,
                gui_command=name)


def _qualify(verb, tid, registry):
    """Re-home a generated verb whose name a patch is taking."""
    if not tid:
        return None
    new_name = f"{tid.split('::')[0].lower()}_{verb.name}"
    if registry.get(new_name) is not None:
        return None
    verb.name = new_name
    registry.add(verb)
    return new_name


def _slug(text):
    text = re.sub(r"[&.]", "", text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unnamed"


# -------------------------------------------------------------- assembly

def register_all(registry: Registry, descriptor=None, tier0=True,
                 patches=None, report=None):
    """Compose every tier into one registry.

    Later tiers win: a patched verb replaces the generated one, which
    replaces the bare command launcher.
    """
    descriptor = descriptor if descriptor is not None else load_descriptor()
    if descriptor is None:
        return {"error": "no descriptor; run tools/generate_descriptor.py"}

    patches = patches if patches is not None else load_patches()
    counts = {"tier0": 0, "tier1": 0, "patched": 0, "skipped": 0}
    by_type = {l["type"]: {**descriptor["commands"].get(n, {}), "name": n}
               for n, l in descriptor.get("links", {}).items()}

    if tier0:
        for command in descriptor["commands"].values():
            verb = build_command_verb(command)
            if registry.get(verb.name) is None:
                registry.add(verb)
                counts["tier0"] += 1

    # Two passes. A patch may rename a verb onto a name the generator
    # already produced from another type -- Part::Box patched to "cube"
    # lands on Mesh::Cube -- so patched verbs are registered last and
    # displace whatever generated verb was sitting there, which moves to a
    # module-qualified name rather than disappearing.
    plain, patched = [], []
    for name, entry in descriptor.get("verbs", {}).items():
        tid = entry["type"]
        if NOISE_TYPES.match(tid):
            counts["skipped"] += 1
            continue
        patch = patches.for_type(tid)
        if patch and patch.get("skip"):
            counts["skipped"] += 1
            continue
        target = patch.get("verb", name) if patch else name
        verb = build_type_verb(target, entry, by_type.get(tid))
        if verb is None:
            counts["skipped"] += 1
            continue
        (patched if patch else plain).append((verb, entry, patch, tid))

    origins = {}
    for verb, entry, _patch, tid in plain:
        registry.add(verb)
        origins[verb.name] = tid
        counts["tier1"] += 1

    for verb, entry, patch, tid in patched:
        verb = patches.apply(verb, entry, patch)
        sitting = registry.get(verb.name)
        if sitting is not None and sitting is not verb:
            if _qualify(sitting, origins.get(sitting.name), registry):
                counts["displaced"] = counts.get("displaced", 0) + 1
        registry.add(verb)
        counts["patched"] += 1
        counts["tier1"] += 1

    counts["total"] = len(registry.names())
    if report is not None:
        report(counts)
    return counts
