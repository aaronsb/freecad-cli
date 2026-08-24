# SPDX-License-Identifier: LGPL-2.1-or-later

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
import unicodedata

from . import bus as _bus
from .grammar import (CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT,
                      Option, Registry, Step, Verb)
from . import curation
from .families import families
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


def _clean_doc(meta, tid):
    """FreeCAD's tooltip, minus the label and command name stuck to it.

    The harvested tooltip runs the menu label into the tooltip text and the
    command name onto the end -- "PadExtrudes the selected sketch ... to the
    bodyPartDesign_Pad" -- because the QAction concatenates them.
    """
    text = (meta or {}).get("tooltip") or ""
    label = (meta or {}).get("label") or ""
    command = (meta or {}).get("name") or ""
    if command and text.endswith(command):
        text = text[: -len(command)]
    if label and text.startswith(label):
        text = text[len(label):]
    text = text.strip(" -\u2014.")
    if not text:
        return f"Create a {tid}."
    return text[0].upper() + text[1:] + ("" if text.endswith(".") else ".")


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
        doc=_clean_doc(meta, entry["type"]),
        gui_command=meta.get("name"),
        creates=entry["type"], generated=True,
    )


# ---------------------------------------------------------------- tier 0

def build_command_verb(command):
    """Every registered command, as a verb.

    It runs the command, and if a task panel opens it reads that panel and
    offers its parameters as prompts rather than leaving them to a mouse.
    Nothing is written per command: a panel names its own fields, so the
    same three callables drive Transform, Mirror, Offset, Cross-sections,
    Placement and Primitives without knowing any of them.

    A command that opens nothing, or opens something with no named input
    in it, has already run by the time open() returns -- which is what
    every one of these did before.
    """
    name = command["name"]
    label = command.get("label") or name
    from .panels import _abort_panel, _emit_panel, _open_panel
    return Verb(name=_slug(label), steps=[],
                open=_open_panel(name),
                emit=_emit_panel,
                abort=_abort_panel,
                doc=command.get("tooltip") or label,
                gui_command=name, generated=True,
                # A panel keeps its own undo and puts everything back on
                # Cancel. A transaction wrapped around one would nest.
                transactional=False)


def _claimed(registry, name):
    """Whether a verb somebody wrote by hand already owns this name.

    Asked of the verb rather than of where its emit came from: every
    generated command verb now shares one emit with the hand-written panel
    verbs, so the module stopped answering this question.
    """
    sitting = registry.get(name)
    return sitting is not None and not getattr(sitting, "generated", False)


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


# ------------------------------------------------------------ families

def _emit_family(members):
    """Run whichever member of the family was chosen."""
    def emit(values):
        import FreeCADGui as Gui
        target = values.get("target")
        entry = members.get(target)
        if entry is None:
            raise RuntimeError(
                f"{target!r} is not one of: {', '.join(sorted(members))}")
        Gui.runCommand(entry["command"])
        return None
    return emit


def _label(text):
    """A label as a person reads it.

    FreeCAD's menu text carries Qt mnemonic markers -- "&Box Zoom", "&5
    Bottom" -- which mean something to a menu and nothing on a command
    line.
    """
    return (text or "").replace("&", "").strip()


def build_family_verb(name, members):
    """One verb for a family FreeCAD spread across many commands.

    Each member stays reachable as its own tier 0 verb; this adds the door
    that can be asked what is behind it.
    """
    choices = sorted(members)
    labels = ", ".join(_label(members[c]["label"]) for c in choices[:4])
    return Verb(
        name=name,
        steps=[Step("target", CHOICE, f"{name.capitalize()} what",
                    choices=choices)],
        emit=_emit_family(members),
        doc=f"{len(choices)} commands FreeCAD spreads apart: {labels}...",
        family=name, generated=True,
    )


def _slug(text):
    # Fold accents to their base letter first. Stripping them instead left
    # FreeCAD's "Bezier Curve" verb named b_zier_curve, which is not a name
    # anyone would guess or type.
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[&.]", "", text).strip().lower()
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

    # What FreeCAD promotes and what it groups, for completion to order by
    # and for `man` to cite. Read from the same descriptor the verbs are.
    curation.load(descriptor)

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
        if _claimed(registry, verb.name):
            # A hand-written verb already owns this name, and it is the
            # better one: it can pick points. Keep the generated version
            # reachable under a qualified name.
            if _qualify(verb, tid, registry):
                counts["shadowed"] = counts.get("shadowed", 0) + 1
            else:
                counts["skipped"] += 1
            continue
        registry.add(verb)
        origins[verb.name] = tid
        counts["tier1"] += 1

    for verb, entry, patch, tid in patched:
        verb = patches.apply(verb, entry, patch)
        if _claimed(registry, verb.name):
            if _qualify(verb, tid, registry):
                counts["shadowed"] = counts.get("shadowed", 0) + 1
            else:
                counts["skipped"] += 1
            continue
        sitting = registry.get(verb.name)
        if sitting is not None and sitting is not verb:
            if _qualify(sitting, origins.get(sitting.name), registry):
                counts["displaced"] = counts.get("displaced", 0) + 1
        registry.add(verb)
        counts["patched"] += 1
        counts["tier1"] += 1

    # Families sit between the generated verbs and the bare launchers: they
    # make a spread-out group discoverable without displacing anything
    # anyone wrote.
    if tier0:
        for name, members in families(descriptor["commands"]).items():
            if _claimed(registry, name) or registry.get(name) is not None:
                counts["family_shadowed"] = counts.get("family_shadowed", 0) + 1
                continue
            registry.add(build_family_verb(name, members))
            counts["families"] = counts.get("families", 0) + 1

    # Verbs an addon declared outright win over everything generated: the
    # author knows what their FeaturePython object is, and FreeCAD's type
    # registry does not.
    for verb in patches.build_declared():
        registry.add(verb)
        counts["declared"] = counts.get("declared", 0) + 1

    counts["total"] = len(registry.names())
    if report is not None:
        report(counts)
    return counts
