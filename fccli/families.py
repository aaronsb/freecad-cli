# SPDX-License-Identifier: LGPL-2.1-or-later

"""Collapse families of commands into one verb with a choice.

FreeCAD spreads a single idea across many commands with no shared name.
Zooming is Std_ViewFitAll, Std_ViewFitSelection, Std_ViewZoomIn,
Std_ViewZoomOut and Std_ViewBoxZoom. Sketcher constraints are two dozen
Sketcher_Constrain* commands. As tier 0 verbs each is reachable and none is
discoverable: there is nothing to complete and no way to ask what the
alternatives are.

The family is in the names. Splitting Module_CamelCaseRest gives a leading
word shared by everything in the family and a remainder that distinguishes
one member from another, so `view front`, `view top`, `constrain
coincident` fall out of the registry rather than being written down.

Nothing here names a command. A patch can rename a family, suppress one, or
hand-write a better verb over the top -- which is what `zoom` is.
"""

import re

CAMEL = re.compile(r"[A-Z][a-z0-9]*|[A-Z]+(?![a-z])")

# Below this, a shared leading word is a coincidence rather than a family.
MIN_MEMBERS = 3

# A head shorter than this is CamelCase splitting an acronym apart --
# Sketcher_BSplineDegree becomes B + Spline + Degree, and "b" is not a verb.
MIN_HEAD = 2

# Leading words that name a module, a workbench, or FreeCAD's own UI
# machinery rather than an action a person would type.
NOT_ACTIONS = {
    "std", "part", "draft", "sketcher", "arch", "bim", "cam", "fem", "mesh",
    "points", "surface", "techdraw", "spreadsheet", "assembly", "material",
    "test", "web", "start", "help",
    "comp",         # FreeCAD's composite toolbar buttons, not a concept
    "extension",    # TechDraw's own grouping prefix
}


def words(text):
    return CAMEL.findall(text) or ([text] if text else [])


def slug(parts):
    return "_".join(p.lower() for p in parts if p)


def split_command(name):
    """Std_ViewFitAll -> ("Std", ["View", "Fit", "All"])."""
    module, _, rest = name.partition("_")
    if not rest:
        return None, []
    return module, words(rest)


def families(commands, min_members=MIN_MEMBERS, overrides=None,
             exclude=None):
    """Group commands by the action word they share.

    ``commands`` maps a command name to its harvested metadata. Returns
    ``{verb_name: {choice: {command, label}}}``.

    ``overrides`` maps a command to ``(family, choice)`` from its command
    file (ADR-100): it goes there instead of where its name would put it.
    A file that says ``family: false`` arrives here as ``(None, None)``
    and joins no family. ``exclude`` is the set
    of leading words that are not actions; the shipped list lives in
    ``lib/commands/std/_families.yaml`` and NOT_ACTIONS is the fallback
    when no dictionary was loaded.
    """
    overrides = overrides or {}
    exclude = NOT_ACTIONS if exclude is None else {e.lower() for e in exclude}
    groups = {}
    for name, meta in commands.items():
        if name in overrides:
            family, choice, also = overrides[name]
            if family and choice:
                member = {
                    "command": name,
                    "label": (meta or {}).get("label") or name,
                    "module": name.partition("_")[0] if "_" in name else "",
                }
                fam = groups.setdefault(slug([family]), {})
                for spelling in [choice] + list(also or []):
                    fam[slug([spelling])] = member
            continue
        module, parts = split_command(name)
        if len(parts) < 2:
            continue
        head, tail = parts[0], parts[1:]
        if len(head) < MIN_HEAD or head.lower() in exclude or not tail:
            continue
        groups.setdefault(slug([head]), {})[slug(tail)] = {
            "command": name,
            "label": (meta or {}).get("label") or name,
            "module": module,
        }
    return {verb: members for verb, members in groups.items()
            if len(members) >= min_members}


def overrides_of(dictionary):
    """(overrides, exclude) as families() wants them, from a compiled
    dictionary. Both None when there is none."""
    if not dictionary:
        return None, None
    over = {}
    for name, entry in dictionary.get("commands", {}).items():
        if "family" in entry or "choice" in entry:
            fam = entry.get("family")
            over[name] = ((None, None, None) if fam is False
                          else (fam, entry.get("choice"), entry.get("also")))
    exclude = (dictionary.get("families") or {}).get("exclude")
    return over, exclude


def meta_of(dictionary, name):
    """A curated family's aliases, default and doc, from _families.yaml."""
    verbs = ((dictionary or {}).get("families") or {}).get("verbs") or {}
    return verbs.get(name) or {}


def report(commands, limit=12):
    found = families(commands)
    ranked = sorted(found.items(), key=lambda kv: -len(kv[1]))
    lines = [f"{len(found)} families, "
             f"{sum(len(m) for m in found.values())} commands collapsed"]
    for verb, members in ranked[:limit]:
        sample = ", ".join(sorted(members)[:6])
        lines.append(f"  {verb:<16} {len(members):>3}  {sample}")
    return "\n".join(lines)
