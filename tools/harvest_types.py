# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pass A: the type registry. Runs headless under freecadcmd.

Probing a type means instantiating it, and some types abort the process from
C++ -- an assertion inside a view provider, which no Python try/except can
catch. So this runs with no GUI (no view providers get built at all) and
writes one JSON line per type as it goes: a crash costs the offending type,
not the sweep. The driver restarts past it.

    FCCLI_OUT=types.jsonl freecadcmd tools/harvest_types.py
"""

import json
import os
import re
import sys

import FreeCAD as App

OUT = os.environ.get("FCCLI_OUT", "types.jsonl")
SKIP = set(filter(None, os.environ.get("FCCLI_SKIP", "").split(",")))

MODULES = [
    "Part", "PartDesign", "Sketcher", "Draft", "Mesh", "MeshPart", "Points",
    "Spreadsheet", "TechDraw", "Fem", "Surface", "Import", "Inspection",
    "ReverseEngineering", "Measure", "Material", "Path", "BIM", "Arch",
]

# One definition, shared with the `describe` verb: what a generated verb
# asks for and what describe reads back must be the same set.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fccli.properties import is_noise  # noqa: E402

KIND_BY_PROPERTY = {
    "App::PropertyLength": ("quantity", "mm"),
    "App::PropertyDistance": ("quantity", "mm"),
    "App::PropertyDistanceX": ("quantity", "mm"),
    "App::PropertyDistanceY": ("quantity", "mm"),
    "App::PropertyDistanceZ": ("quantity", "mm"),
    "App::PropertyArea": ("quantity", "mm^2"),
    "App::PropertyVolume": ("quantity", "mm^3"),
    "App::PropertyAngle": ("quantity", "deg"),
    "App::PropertyFloat": ("quantity", ""),
    "App::PropertyFloatConstraint": ("quantity", ""),
    "App::PropertyPrecision": ("quantity", ""),
    "App::PropertyPercent": ("quantity", ""),
    "App::PropertyQuantity": ("quantity", ""),
    "App::PropertyQuantityConstraint": ("quantity", ""),
    "App::PropertyInteger": ("quantity", ""),
    "App::PropertyIntegerConstraint": ("quantity", ""),
    "App::PropertyVector": ("point", ""),
    "App::PropertyVectorDistance": ("point", ""),
    "App::PropertyVectorList": ("point", ""),
    "App::PropertyPosition": ("point", ""),
    "App::PropertyDirection": ("point", ""),
    "App::PropertyPlacement": ("point", ""),
    "App::PropertyBool": ("flag", ""),
    "App::PropertyEnumeration": ("choice", ""),
    "App::PropertyLink": ("selection", ""),
    "App::PropertyLinkSub": ("selection", ""),
    "App::PropertyLinkList": ("selection", ""),
    "App::PropertyLinkSubList": ("selection", ""),
    "App::PropertyFile": ("path", ""),
    "App::PropertyFileIncluded": ("path", ""),
    "App::PropertyString": ("text", ""),
    "App::PropertyStringList": ("text", ""),
}

TAG = re.compile(r"<[^>]+>")


def clean(text):
    if not text:
        return ""
    return " ".join(TAG.sub("", text).split()).strip()


def load_modules():
    loaded = []
    for m in MODULES:
        try:
            __import__(m)
            loaded.append(m)
        except Exception:
            pass
    return loaded


def describe(obj, prop):
    ptype = obj.getTypeIdOfProperty(prop)
    kind, unit = KIND_BY_PROPERTY.get(ptype, ("text", ""))
    entry = {"name": prop, "property_type": ptype, "kind": kind,
             "group": obj.getGroupOfProperty(prop),
             "doc": clean(obj.getDocumentationOfProperty(prop))}
    if unit:
        entry["unit"] = unit
    if kind == "choice":
        try:
            entry["choices"] = list(obj.getEnumerationsOfProperty(prop))
        except Exception:
            entry["choices"] = []
    try:
        value = getattr(obj, prop)
        if isinstance(value, (bool, int, float, str)):
            entry["default"] = value
    except Exception:
        pass
    return entry


def main():
    loaded = load_modules()
    doc = App.newDocument("probe")
    fh = open(OUT, "a", encoding="utf-8", buffering=1)
    fh.write(json.dumps({"_modules": loaded}) + "\n")

    for tid in sorted(doc.supportedTypes()):
        if tid in SKIP:
            fh.write(json.dumps({"type": tid, "skipped": "known crasher"}) + "\n")
            continue
        # Claim the type before touching it. If the process dies here, the
        # driver sees a claim with no result and blocklists it.
        fh.write(json.dumps({"_probing": tid}) + "\n")
        os.fsync(fh.fileno())
        try:
            obj = doc.addObject(tid, "probe")
        except Exception as exc:
            fh.write(json.dumps({"type": tid, "error": str(exc)[:120]}) + "\n")
            continue
        if obj is None:
            fh.write(json.dumps({"type": tid, "error": "addObject -> None"}) + "\n")
            continue
        params, dropped = [], 0
        try:
            props = list(obj.PropertiesList)
        except Exception as exc:
            fh.write(json.dumps({"type": tid, "error": str(exc)[:120]}) + "\n")
            continue
        for prop in props:
            try:
                if is_noise(obj, prop):
                    dropped += 1
                    continue
                params.append(describe(obj, prop))
            except Exception:
                dropped += 1
        fh.write(json.dumps({
            "type": tid, "module": tid.split("::")[0],
            "params": params, "dropped": dropped,
            "groups": sorted({p["group"] for p in params}),
        }) + "\n")
        # Destroying the object is its own chance to abort the process, so
        # re-claim the type across the teardown.
        fh.write(json.dumps({"_probing": tid}) + "\n")
        os.fsync(fh.fileno())
        try:
            doc.removeObject(obj.Name)
        except Exception:
            pass
        fh.write(json.dumps({"_teardown": tid}) + "\n")

    fh.write(json.dumps({"_done": True}) + "\n")
    fh.close()


main()
