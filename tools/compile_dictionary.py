#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Compile the command tree into one file the factory reads at startup.

    python3 tools/compile_dictionary.py [--tree fccli/lib/commands] [--out fccli/dictionary.json]

1111 YAML files at every FreeCAD launch is a second nobody asked for, for
content that changes only when somebody edits a file. The tree is the
source; this is what runs. The lint fails when the two disagree.
"""

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import command_files as cf  # noqa: E402

DEFAULT_TREE = os.path.join(ROOT, "fccli", "lib", "commands")
DEFAULT_OUT = os.path.join(ROOT, "fccli", "dictionary.json")


def compile_tree(tree):
    """The compiled form: authored fields and the body, per command."""
    commands = {}
    stamps = []
    revs = []
    for rel, full in cf.walk(tree):
        front, body = cf.read(full)
        name = front.get("command")
        if not name:
            raise ValueError(f"{rel}: no command")
        if name in commands:
            raise ValueError(f"{rel}: {name} already at {commands[name]['file']}")
        generated = front.get("generated") or {}
        stamps.append(generated.get("freecad"))
        revs.append(generated.get("wiki_rev"))
        entry = {"file": rel.replace(os.sep, "/"), "doc": body.strip()}
        for key, value in cf.authored_of(front).items():
            if value not in (None, [], {}):
                entry[key] = value
        commands[name] = entry
    import yaml
    families = {}
    extra = os.path.join(tree, "std", "_families.yaml")
    if os.path.exists(extra):
        with open(extra, encoding="utf-8") as fh:
            families = yaml.safe_load(fh) or {}
        if not isinstance(families.get("exclude", []), list):
            raise ValueError("std/_families.yaml: exclude must be a list")
    # Type tuning, keyed by the type it retunes. A command file's `type`
    # block names its type in `of`; a workbench's _types.yaml holds tuning
    # for a type with no command of its own (Part::Wedge, Part::Helix).
    types = {}
    for name, entry in commands.items():
        block = entry.get("type")
        if isinstance(block, dict) and block.get("of"):
            tid = block["of"]
            if tid in types:
                raise ValueError(f"{entry['file']}: type {tid} is already "
                                 f"tuned by {types[tid]['file']}")
            types[tid] = {k: v for k, v in block.items() if k != "of"}
            types[tid]["file"] = entry["file"]
    import command_files as _cf
    for dirpath, dirs, files in sorted(os.walk(tree)):
        dirs.sort()
        if "_types.yaml" not in files:
            continue
        with open(os.path.join(dirpath, "_types.yaml"), encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        rel = os.path.relpath(os.path.join(dirpath, "_types.yaml"), tree).replace(os.sep, "/")
        for tid, spec in (doc.get("types") or {}).items():
            if not isinstance(spec, dict):
                raise ValueError(f"{rel}: {tid} must be a mapping")
            bad = set(spec) - (_cf.TYPE_KEYS - {"of"})
            if bad:
                raise ValueError(f"{rel}: {tid} has keys {sorted(bad)} not in "
                                 f"{sorted(_cf.TYPE_KEYS - {'of'})}")
            if tid in types:
                raise ValueError(f"{rel}: type {tid} is already tuned by "
                                 f"{types[tid]['file']}")
            types[tid] = {**spec, "file": rel}
    def common(values):
        # The stamp most files carry. A version sorts wrong as a string
        # (1.9 above 1.10) and a commit hash does not sort at all.
        counted = Counter(v for v in values if v)
        return counted.most_common(1)[0][0] if counted else None
    return {
        "generated_by": "tools/compile_dictionary.py",
        "families": families,
        "types": types,
        "freecad": common(stamps),
        "wiki_rev": common(revs),
        "commands": commands,
    }


def dump(data):
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", default=DEFAULT_TREE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    try:
        data = compile_tree(args.tree)
    except ValueError as exc:
        print(f"compile: {exc}", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(dump(data))
    authored = sum(1 for c in data["commands"].values()
                   if set(c) - {"file", "doc"})
    print(f"{len(data['commands'])} commands compiled, {authored} with "
          f"authored fields, {os.path.getsize(args.out) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
