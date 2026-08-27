# SPDX-License-Identifier: LGPL-2.1-or-later

"""Patch discovery and composition.

A generated verb is functional and generic. A patch makes it feel like the
tool it represents: which properties are prompts and which are inline
options, what order they come in, which three lengths are really one point,
what the verb is called.

Patches are keyed by namespace -- a type module (``Part``, ``PartDesign``)
or an addon identity (``CurvedShapes``, ``BIM``) -- and are discovered from
three roots, each overriding the one before:

    fccli/patches/*.py                      shipped with this addon
    <Mod>/<addon>/fccli_patch.py            shipped by the addon itself
    $XDG_DATA_HOME/fccli/patches/           written by the user

An addon that ships its own ``fccli_patch.py`` is picked up with no
registration step, so a third-party workbench gets generic command-line
support from the factory and a hand-tuned grammar the moment someone writes
one for it. Nothing has to change here for that to happen.

A patch has two halves. ``types`` retunes verbs the factory generated;
``verbs`` declares ones it could not, which is the case for any addon whose
objects are ``Part::FeaturePython`` with a Python proxy -- FreeCAD's type
registry never sees those, so there is nothing to generate from.

A patch module exports ``PATCH``::

    PATCH = {
        "key": "Part",
        "types": {
            "Part::Cylinder": {
                "verb": "cylinder",
                "aliases": ["cyl"],
                "steps": ["Radius", "Height"],     # order, and required
                "options": ["Angle"],              # inline keywords
                "point": {"base": ["Placement"]},  # collapse into one getter
                "hide": ["FirstAngle", "SecondAngle"],
            },
        },
        "verbs": {
            "curved_array": {
                "doc": "Array a shape along hull curves.",
                "gui_command": "CurvedArray",
                "steps": [
                    {"id": "base", "kind": "selection", "prompt": "Base shape"},
                    {"id": "items", "kind": "quantity", "prompt": "Items",
                     "unit": ""},
                ],
                "emit": make_curved_array,   # a callable you supply
            },
        },
    }
"""

import glob
import importlib.util
import os

from .. import paths as _paths
from ..grammar import (CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT,
                       Option, Step, Verb)

KINDS = {"point": POINT, "quantity": QUANTITY, "choice": CHOICE,
         "selection": SELECTION, "text": TEXT, "path": PATH}

BUILTIN_DIR = os.path.dirname(os.path.abspath(__file__))
# XDG, with the pre-XDG directory still read. paths.py's docstring has
# named patches as XDG_DATA_HOME data since it landed; this was the third
# of the "three paths spelled out by hand in three modules" and was the
# one left behind, with no XDG support and no fallback.
USER_DIR = _paths.data("patches")
LEGACY_USER_DIR = _paths.legacy("patches")
MOD_DIRS = [
    os.path.expanduser("~/.local/share/FreeCAD/v1-1/Mod"),
    os.path.expanduser("~/.local/share/FreeCAD/Mod"),
    "/usr/lib/freecad/Mod",
]
ADDON_PATCH = "fccli_patch.py"


def _load_module(path, name):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "PATCH", None)
    except Exception as exc:
        import FreeCAD as App
        App.Console.PrintWarning(f"[fccli] patch {path}: {exc}\n")
        return None


# Patches are imported by path, so they get a synthetic module name rather
# than a package one. curation.rank_of reads this to tell a verb somebody
# wrote from one the factory generated -- it used to look for "patches" in
# the module name, which nothing here has ever produced.
MODULE_PREFIX = "fccli_"


def discover():
    """Every patch on disk, in ascending order of precedence."""
    found = []
    for path in sorted(glob.glob(os.path.join(BUILTIN_DIR, "[!_]*.py"))):
        patch = _load_module(path, MODULE_PREFIX + "builtin_" + os.path.basename(path)[:-3])
        if patch:
            found.append(("builtin", path, patch))
    for root in MOD_DIRS:
        for path in sorted(glob.glob(os.path.join(root, "*", ADDON_PATCH))):
            addon = os.path.basename(os.path.dirname(path))
            patch = _load_module(path, MODULE_PREFIX + "addon_" + addon)
            if patch:
                patch.setdefault("key", addon)
                found.append(("addon", path, patch))
    seen = set()
    for root in (USER_DIR, LEGACY_USER_DIR):
        for path in sorted(glob.glob(os.path.join(root, "*.py"))):
            base = os.path.basename(path)
            if base in seen:
                continue        # the XDG copy wins over the one beside it
            seen.add(base)
            patch = _load_module(path, MODULE_PREFIX + "user_" + base[:-3])
            if patch:
                found.append(("user", path, patch))
    return found


class PatchSet:
    def __init__(self, patches=None):
        self.sources = patches if patches is not None else discover()
        self.by_type = {}
        self.declared = {}
        self.keys = []
        for origin, path, patch in self.sources:
            key = patch.get("key", "?")
            self.keys.append((origin, key, path))
            for name, spec in (patch.get("verbs") or {}).items():
                merged = dict(self.declared.get(name, {}))
                merged.update(spec)
                merged.setdefault("key", key)
                self.declared[name] = merged
            for tid, spec in (patch.get("types") or {}).items():
                # Later roots override earlier ones, key by key rather than
                # wholesale, so a user patch can retune one field without
                # restating the addon's whole entry.
                merged = dict(self.by_type.get(tid, {}))
                merged.update(spec)
                self.by_type[tid] = merged

    def for_type(self, tid):
        return self.by_type.get(tid)

    def summary(self):
        by_origin = {}
        for origin, key, _ in self.keys:
            by_origin.setdefault(origin, []).append(key)
        return {"patches": len(self.keys), "types": len(self.by_type),
                "declared": len(self.declared), "by_origin": by_origin}

    # ------------------------------------------------------------ declare

    def build_declared(self):
        """Verbs an addon wrote out in full, because nothing generated them."""
        out = []
        for name, spec in self.declared.items():
            emit = spec.get("emit")
            if not callable(emit):
                continue
            steps = [_build_step(raw) for raw in spec.get("steps", [])]
            out.append(Verb(
                name=spec.get("verb", name),
                steps=[s for s in steps if s is not None],
                emit=emit,
                aliases=list(spec.get("aliases", [])),
                doc=spec.get("doc", ""),
                gui_command=spec.get("gui_command"),
            ))
        return out

    # ------------------------------------------------------------- apply

    def apply(self, verb, entry, spec):
        params = {p["name"]: p for p in entry["params"]}
        steps = {s.id: s for s in verb.steps}

        for name in spec.get("hide", []):
            steps.pop(name, None)

        # Three lengths that are really one point.
        for step_id, sources in (spec.get("point") or {}).items():
            for src in sources:
                steps.pop(src, None)
            prompt = spec.get("prompts", {}).get(step_id, step_id.capitalize())
            steps[step_id] = Step(step_id, POINT, prompt)

        ordered = []
        for name in spec.get("steps", []):
            step = steps.pop(name, None)
            if step is not None:
                step.optional = False
                step.prompt = spec.get("prompts", {}).get(name, step.prompt)
                ordered.append(step)

        inline = []
        for name in spec.get("options", []):
            param = params.get(name)
            step = steps.pop(name, None)
            if param is None:
                continue
            # The step this option replaces is what says how to read its
            # value. A boolean has none -- flags never become steps -- and
            # the keyword alone is the whole of setting one (ADR-204).
            inline.append(Option(name, param.get("doc", "") or name,
                                 _flag(name), sets=True, takes=step))
        if inline and ordered:
            ordered[-1].options = list(ordered[-1].options) + inline

        if not spec.get("strict"):
            # Anything the patch did not speak for stays available, after
            # the steps it did order.
            ordered.extend(steps.values())

        verb.steps = ordered
        verb.aliases = list(spec.get("aliases", verb.aliases))
        verb.doc = spec.get("doc", verb.doc)
        if spec.get("gui_command"):
            verb.gui_command = spec["gui_command"]
        if callable(spec.get("emit")):
            verb.emit = spec["emit"]
        return verb


def _build_step(raw):
    """One step, from a plain dict an addon author can write by hand."""
    if isinstance(raw, Step):
        return raw
    kind = KINDS.get(raw.get("kind", "text"))
    if kind is None:
        return None
    step = Step(
        raw["id"], kind, raw.get("prompt", raw["id"]),
        repeat=raw.get("repeat", False),
        min_count=raw.get("min_count", 1),
        optional=raw.get("optional", False),
        unit=raw.get("unit", "mm"),
        choices=list(raw.get("choices", [])),
        default=raw.get("default"),
    )
    step.options = [
        Option(o["name"], o.get("doc", ""), _flag(o["name"]), sets=True)
        if isinstance(o, dict) else Option(o, "", _flag(o), sets=True)
        for o in raw.get("options", [])
    ]
    return step


def _flag(name):
    """Naming a boolean is the whole of setting it.

    There were two of these, `_flag` and `_setter`, character for
    character the same, and the second was what a declared option ran.
    That is how `angle` on a cylinder came to mean `Angle = True` -- one
    degree, against FreeCAD's default of 360 (GH #81). An option that
    carries a value does not reach an action at all now: the engine reads
    it against `Option.takes` and records it, and what is left here is the
    boolean case both names always described (ADR-204).
    """
    def action(engine):
        engine.flags[name] = True
        return False
    return action


def load_patches():
    return PatchSet()
