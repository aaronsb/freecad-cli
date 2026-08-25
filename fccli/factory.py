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

import html
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
# The command tree, compiled (ADR-100). fccli/lib/commands is the source;
# tools/compile_dictionary.py writes this and the lint keeps them equal.
DICTIONARY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "dictionary.json")

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


def load_dictionary(path=DICTIONARY):
    """The compiled tree, or None when there is none.

    A file that will not parse is reported and treated as absent: a
    broken dictionary costs its overrides, never the 1111 verbs.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        try:
            import FreeCAD as App
            App.Console.PrintWarning(f"[fccli] {path}: {exc}\n")
        except Exception:
            pass
        return None


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

def build_command_verb(command, entry=None):
    """Every registered command, as a verb.

    ``entry`` is the command's compiled file (ADR-100): the authored
    fields a person set, and the page `man` shows. The verb's name is the
    file's `verb` when it has one and the slugged label otherwise; the
    one-line doc stays the harvested tooltip, which is what a one-liner
    is for, and the body becomes the manual.

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
    entry = entry or {}
    from .panels import _abort_panel, _emit_panel, _open_panel
    return Verb(name=entry.get("verb") or _slug(label), steps=[],
                open=_open_panel(name),
                emit=_emit_panel,
                abort=_abort_panel,
                doc=command.get("tooltip") or label,
                aliases=list(entry.get("aliases") or []),
                manual=entry.get("doc") or "",
                requires=list(entry.get("requires") or []),
                panel=entry.get("panel"),
                gui_command=name, generated=True)


_TAG = re.compile(r"<[^>]+>")
_PLACEHOLDER = re.compile(r"%\d")


def _plain(text, mnemonic=False):
    """getInfo text as the harvest cleans it: no tags, no entities, one
    line. An addon's tooltip is the one population the harvest never
    measured, and it is where <br>, &amp; and newlines live.

    Menu text carries a Qt mnemonic marker, and Qt spells a literal
    ampersand there as &&; a tooltip is prose and keeps its &.

    One departure from clean(): a tag becomes a space, not nothing. The
    harvest's tooltips were plain and needed unglue() for the rich-text
    fallback; an addon's toolTip is the rich-text case from the start.
    """
    text = html.unescape(_TAG.sub(" ", text or ""))
    if mnemonic:
        text = text.replace("&&", "\0").replace("&", "").replace("\0", "&")
    return " ".join(text.split()).strip()


def runtime_commands(known):
    """Commands FreeCAD has registered that the descriptor never saw.

    The descriptor is harvested once, on one machine. An addon installed
    after that registers its commands with FreeCAD at startup and got no
    verb from it until somebody regenerated the descriptor with the addon
    present -- layer 2 of ADR-600, true only by accident of timing.

    Named the way the harvest would have named them: menuText with the
    mnemonic dropped, unless it still holds a placeholder, in which case
    the command name stands in. Placement is unknown, so they rank as
    registry and claim a short name only if nobody else has.

    Empty when there is no GUI to ask, or no listCommands on the one there
    is -- which is the offscreen suite's FreeCADGui.
    """
    try:
        import FreeCADGui as Gui
        names = set(Gui.listCommands())
    except Exception:
        return []
    out = []
    for name in sorted(names - set(known)):
        info = {}
        try:
            command = Gui.Command.get(name)
            info = (command.getInfo() if command else None) or {}
        except Exception:
            pass
        # A Qt placeholder is %1, %2; a percent sign on its own is prose.
        label = _plain(info.get("menuText"), mnemonic=True)
        if not label or _PLACEHOLDER.search(label):
            label = name
        tooltip = _plain(info.get("toolTip"))
        if _PLACEHOLDER.search(tooltip):
            tooltip = ""
        if not tooltip:
            # Never the command name: nothing should hand a reader
            # documentation that ends in the thing it documents.
            tooltip = label if label != name else name.replace("_", " ")
        out.append({"name": name, "label": label, "tooltip": tooltip,
                    "toolbar": None, "menu": None})
    return out


def register_runtime(registry, descriptor=None):
    """Give a verb to every command FreeCAD has that nothing here does yet.

    Called once by register_all and again whenever a workbench activates:
    an addon that registers its commands in its workbench's Initialize()
    has none at startup and all of them the first time somebody opens it.
    Idempotent -- a command the descriptor knows, or that already reaches
    a verb, is skipped, so the second call costs a set difference and
    registers only what is new. The descriptor's own commands are its
    business either way: the nine of #19 are not rescued here.

    Returns how many were registered.
    """
    descriptor = descriptor if descriptor is not None else load_descriptor()
    known = set((descriptor or {}).get("commands", {}))
    known |= {getattr(registry.get(n), "gui_command", None)
              for n in registry.names()}
    added = 0
    for command in runtime_commands(known):
        verb = build_command_verb(command)
        if registry.get(verb.name) is None:
            registry.add(verb)
        elif not _qualify_command(verb, command["name"], registry):
            continue
        added += 1
    return added


def _make_room(registry, name, origins, counts):
    """A typed verb is taking `name`. Re-home whatever generated verb
    holds it rather than add over it.

    The tier-1 loops used to add without asking, which is how nine
    descriptor commands reached no verb at all (#19): their launcher's
    slugged label -- box, pipe, helix, fillet -- was also a typed verb's
    name. A launcher is qualified the way a contested tier-0 name is; a
    typed verb from another type is module-qualified as before.
    """
    sitting = registry.get(name)
    if sitting is None or not getattr(sitting, "generated", False):
        return
    if sitting.name != name:
        return                  # `name` was one of its aliases; leave it
    command = getattr(sitting, "gui_command", None)
    if sitting.open is not None and command:
        if _qualify_command(sitting, command, registry):
            counts["displaced"] = counts.get("displaced", 0) + 1
    elif _qualify(sitting, origins.get(sitting.name), registry):
        counts["displaced"] = counts.get("displaced", 0) + 1


def _free_aliases(verb, registry, reserved, counts):
    """Drop an authored alias that would take a name already in use.

    Registry.add writes aliases unconditionally, so a file's `aliases:
    [w]` took `w` from save, and `[view]` took the name the view family
    was about to claim -- 41 commands lost their door to one alias.
    """
    kept = []
    for alias in verb.aliases:
        if registry.get(alias) is not None or alias in reserved:
            counts["aliases_dropped"] = counts.get("aliases_dropped", 0) + 1
            continue
        kept.append(alias)
    verb.aliases = kept


def _claimed(registry, name):
    """Whether a verb somebody wrote by hand already owns this name.

    Asked of the verb rather than of where its emit came from: every
    generated command verb now shares one emit with the hand-written panel
    verbs, so the module stopped answering this question.
    """
    sitting = registry.get(name)
    return sitting is not None and not getattr(sitting, "generated", False)


def _by_prominence(commands):
    """Commands in the order they should get to claim a short name.

    Two commands whose labels slug the same both want the plain name, and
    whoever is registered first takes it. Left to the descriptor's own
    order that is alphabetical, which decides by accident: `compound` went
    to CAM_Compound over Part_Compound, and `material` to Arch_Material
    over the BIM_Material that sits in a toolbar, because C sorts before P
    and A before B.

    FreeCAD already says which of the two it considers the front door, by
    putting one in a toolbar or a menu and leaving the other reachable
    only from code. That is the same signal curation.py ranks completions
    by. Sorting on it first costs nothing and settles every one of these
    the way a person would: in all twenty cases the command that loses a
    contested name under alphabetical order is the one FreeCAD surfaces.

    Stable within a rank, so the descriptor's sorted order still decides
    genuine ties and the result does not move between regenerations.
    """
    return sorted(commands,
                  key=lambda c: (c.get("toolbar") is None,
                                 c.get("menu") is None))


def _qualify_command(verb, command, registry):
    """Re-home a command verb whose name another command already took.

    Two commands whose labels slug the same are ordinary -- Sketcher and
    Draft both have a Grid, Sketcher and Std both have a Copy. The loser
    used to be dropped without a word, which cost 90 commands their verb
    before this function existed and would have cost 43 more when the
    harvest started reading real labels for commands with no QAction:
    `Sketcher_Grid` had been reachable as `sketcher_grid` precisely
    because it had no label to collide with.

    So the loser keeps the prefix its command name already carries, which
    is the name it had. Whoever wins the short name is decided by the
    descriptor's own order -- arbitrary, but stable, and the other one is
    reachable either way.

    Three-way collisions are real: Sketcher_CreateSlot wants `slot`, which
    CAM_Slot has, and then `sketcher_slot`, which Sketcher_CompSlot has.
    The command's own name is unique by construction, so slugging that is
    the fallback and there is always one left. Nothing is dropped.
    """
    for candidate in _candidate_names(verb.name, command):
        if registry.get(candidate) is None:
            verb.name = candidate
            registry.add(verb)
            return candidate
    return None


def _candidate_names(name, command):
    """Names to try for a command verb, least qualified first.

    The last resort counts, because even the command's own slug can be
    taken: Sketcher_Dimension wants `dimension`, then `sketcher_dimension`
    -- which is where Sketcher_CompDimensionTools already landed by this
    same route. A suffix is ugly and it is reachable, which beats the
    command having no verb at all.
    """
    stem = command.split("_", 1)[0].lower() if "_" in command else ""
    if stem:
        yield f"{stem}_{name}"
    full = _slug(command)
    if full != name:
        yield full
    for n in range(2, 10):
        yield f"{full}_{n}"


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

def _emit_family(members, default=None):
    """Run whichever member of the family was chosen.

    A bare `zoom` finishes on the one optional step without visiting the
    prompt, so the default is applied here rather than by the engine.
    """
    def emit(values):
        import FreeCADGui as Gui
        target = values.get("target") or default
        entry = members.get(target)
        if entry is None:
            raise RuntimeError(
                f"{target!r} is not one of: {', '.join(sorted(set(members)))}")
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


def build_family_verb(name, members, meta=None):
    """One verb for a family FreeCAD spread across many commands.

    Each member stays reachable as its own tier 0 verb; this adds the door
    that can be asked what is behind it. ``meta`` -- a family declared in
    ``_families.yaml`` -- gives it aliases, a default choice and a doc,
    which is what a curated family like `zoom` needs over a derived one.
    """
    meta = meta or {}
    choices = sorted(set(members))
    default = meta.get("default")
    # Count commands, not spellings: `also` gives one command several
    # choice keys, and "39 commands" for 36 of them reads wrong.
    ncommands = len({m["command"] for m in members.values()})
    labels = ", ".join(_label(members[c]["label"]) for c in choices[:4])
    return Verb(
        name=name,
        steps=[Step("target", CHOICE, f"{name.capitalize()} what",
                    choices=choices, optional=default is not None,
                    default=default)],
        emit=_emit_family(members, default),
        aliases=list(meta.get("aliases") or []),
        doc=meta.get("doc")
            or f"{ncommands} commands FreeCAD spreads apart: {labels}...",
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
                 patches=None, report=None, dictionary=None):
    """Compose every tier into one registry.

    Later tiers win: a patched verb replaces the generated one, which
    replaces the bare command launcher.

    ``dictionary`` is the compiled command tree (ADR-100); None loads the
    shipped one, and {} runs without any, which the tests use to measure
    what the tree changes.
    """
    descriptor = descriptor if descriptor is not None else load_descriptor()
    if descriptor is None:
        return {"error": "no descriptor; run tools/generate_descriptor.py"}
    dictionary = dictionary if dictionary is not None else (load_dictionary() or {})
    entries = dictionary.get("commands", {})

    # What FreeCAD promotes and what it groups, for completion to order by
    # and for `man` to cite. Read from the same descriptor the verbs are,
    # and demoted where a command file says rank: registry.
    curation.load(descriptor, dictionary)

    patches = patches if patches is not None else load_patches()
    counts = {"tier0": 0, "tier1": 0, "patched": 0, "skipped": 0}
    by_type = {l["type"]: {**descriptor["commands"].get(n, {}), "name": n}
               for n, l in descriptor.get("links", {}).items()}

    # Names the families will want, so no authored alias takes one first.
    from .families import overrides_of
    over, exclude = overrides_of(dictionary)
    family_names = set(families(descriptor["commands"], overrides=over,
                                exclude=exclude)) if tier0 else set()
    # And the typed verbs', which register after tier 0 and would land on
    # top of an alias with that name.
    reserved = family_names | set(descriptor.get("verbs", {}))

    if tier0:
        for command in _by_prominence(descriptor["commands"].values()):
            verb = build_command_verb(command, entries.get(command["name"]))
            _free_aliases(verb, registry, reserved, counts)
            if registry.get(verb.name) is None:
                registry.add(verb)
                counts["tier0"] += 1
            elif _qualify_command(verb, command["name"], registry):
                counts["tier0"] += 1
                counts["qualified"] = counts.get("qualified", 0) + 1
            else:
                counts["unreachable"] = counts.get("unreachable", 0) + 1

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
        _make_room(registry, verb.name, origins, counts)
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
        _make_room(registry, verb.name, origins, counts)
        registry.add(verb)
        counts["patched"] += 1
        counts["tier1"] += 1

    # Commands FreeCAD has that the descriptor never saw. After every tier
    # that reads the descriptor, so a runtime command qualifies around a
    # name a typed verb holds rather than being overwritten by it -- the
    # tier-1 loops add without asking, and a runtime verb registered
    # before them was counted, then erased.
    if tier0:
        counts["runtime"] = register_runtime(registry, descriptor)

    # Families sit between the generated verbs and the bare launchers: they
    # make a spread-out group discoverable without displacing anything
    # anyone wrote.
    if tier0:
        from .families import meta_of
        for name, members in families(descriptor["commands"], overrides=over,
                                      exclude=exclude).items():
            verb = build_family_verb(name, members, meta_of(dictionary, name))
            _free_aliases(verb, registry, set(), counts)
            if _claimed(registry, name) or registry.get(name) is not None:
                counts["family_shadowed"] = counts.get("family_shadowed", 0) + 1
                continue
            registry.add(verb)
            counts["families"] = counts.get("families", 0) + 1

    # Verbs an addon declared outright win over everything generated: the
    # author knows what their FeaturePython object is, and FreeCAD's type
    # registry does not.
    for verb in patches.build_declared():
        sitting = registry.get(verb.name)
        if sitting is not None and sitting is not verb:
            # Re-home whatever generated verb held the name rather than
            # erase it -- a launcher for the very command the addon
            # declared a better verb for is the usual case.
            command = getattr(sitting, "gui_command", None)
            if getattr(sitting, "generated", False) and command:
                _qualify_command(sitting, command, registry)
        registry.add(verb)
        counts["declared"] = counts.get("declared", 0) + 1

    counts["authored"] = sum(1 for e in entries.values()
                             if set(e) - {"file", "doc"})
    counts["total"] = len(registry.names())
    if report is not None:
        report(counts)
    return counts
