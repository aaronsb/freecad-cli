#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Check the command tree against the descriptor and the compiled form.

    python3 tools/lint_dictionary.py [--tree ...] [--descriptor ...] [--compiled ...]

ADR-100's five rules:

  1. every file names a command in the descriptor, and every command has
     a file
  2. a file's generated: block matches the descriptor field for field --
     a hand edit inside it belongs in an authored field or in etc/
  3. authored fields are well-formed: requires from the closed
     vocabulary, panel pick or null, rank registry or null, type keys
     from the five
  4. verb names asked for are unique across the tree
  5. the compiled dictionary is what the tree compiles to

Exit 1 on any error. Rule 2 is the one that keeps a generated field safe
to regenerate.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import command_files as cf  # noqa: E402
import compile_dictionary as cd  # noqa: E402

DESCRIPTOR = os.path.join(ROOT, "fccli", "descriptor.json")

# Descriptor field -> generated: field. wiki_rev and freecad are the tool's
# own stamps and are checked for presence, not against the descriptor.
MIRRORED = ("label", "tooltip", "toolbar", "menu", "shortcut", "workbench",
            "wiki")


def lint(tree, descriptor_path, compiled_path):
    problems = []
    with open(descriptor_path, encoding="utf-8") as fh:
        descriptor = json.load(fh)
    commands = descriptor["commands"]
    seen, verbs = {}, {}
    for rel, full in cf.walk(tree):
        try:
            front, _body = cf.read(full)
        except Exception as exc:
            problems.append(f"{rel}: unreadable: {exc}")
            continue
        name = front.get("command")
        entry = commands.get(name)
        if entry is None:
            problems.append(f"{rel}: {name!r} is not a command in the "
                            f"descriptor (rule 1)")
            continue
        if name in seen:
            problems.append(f"{rel}: {name} is also {seen[name]} (rule 1)")
        seen[name] = rel
        want_dir = cf.workbench_dir(entry.get("workbench"))
        if os.path.dirname(rel) != want_dir:
            problems.append(f"{rel}: belongs in {want_dir}/ (rule 1)")
        generated = front.get("generated") or {}
        for key in MIRRORED:
            if generated.get(key) != entry.get(key):
                problems.append(
                    f"{rel}: generated.{key} is {generated.get(key)!r}, the "
                    f"descriptor says {entry.get(key)!r} -- a change here "
                    f"belongs in an authored field (rule 2)")
        if generated.get("freecad") != descriptor.get("freecad"):
            problems.append(f"{rel}: generated.freecad is "
                            f"{generated.get('freecad')!r}, the descriptor is "
                            f"{descriptor.get('freecad')!r} (rule 2)")
        authored = cf.authored_of(front)
        for extra in set(front) - set(cf.AUTHORED) - {"command", "generated"}:
            problems.append(f"{rel}: unknown field {extra!r} (rule 3)")
        for req in authored["requires"]:
            if req not in cf.REQUIRES:
                problems.append(f"{rel}: requires {req!r} is not one of "
                                f"{sorted(cf.REQUIRES)} (rule 3)")
        if authored["panel"] not in cf.PANEL:
            problems.append(f"{rel}: panel must be pick or null (rule 3)")
        if authored["rank"] not in cf.RANK:
            problems.append(f"{rel}: rank must be registry or null (rule 3)")
        if authored["type"] is not None:
            if not isinstance(authored["type"], dict):
                problems.append(f"{rel}: type must be a mapping (rule 3)")
            else:
                for key in set(authored["type"]) - cf.TYPE_KEYS:
                    problems.append(f"{rel}: type.{key} is not one of "
                                    f"{sorted(cf.TYPE_KEYS)} (rule 3)")
        if not isinstance(authored["aliases"], list):
            problems.append(f"{rel}: aliases must be a list (rule 3)")
        if (authored["choice"] is None) != (authored["family"] is None):
            problems.append(f"{rel}: family and choice go together (rule 3)")
        verb = authored["verb"]
        if verb:
            if verb in verbs:
                problems.append(f"{rel}: verb {verb!r} is also asked for by "
                                f"{verbs[verb]} (rule 4)")
            verbs[verb] = rel
    for name in commands:
        if name not in seen:
            problems.append(f"{name}: no file under {os.path.relpath(tree, ROOT)}"
                            f"/{cf.workbench_dir(commands[name].get('workbench'))}/ "
                            f"(rule 1)")
    if os.path.exists(compiled_path):
        try:
            with open(compiled_path, encoding="utf-8") as fh:
                on_disk = fh.read()
            if on_disk != cd.dump(cd.compile_tree(tree)):
                problems.append(f"{os.path.relpath(compiled_path, ROOT)} is "
                                f"not what the tree compiles to; run make "
                                f"dictionary (rule 5)")
        except Exception as exc:
            problems.append(f"compiled: {exc} (rule 5)")
    else:
        problems.append(f"{os.path.relpath(compiled_path, ROOT)} is missing; "
                        f"run make dictionary (rule 5)")
    return len(seen), problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", default=cd.DEFAULT_TREE)
    ap.add_argument("--descriptor", default=DESCRIPTOR)
    ap.add_argument("--compiled", default=cd.DEFAULT_OUT)
    args = ap.parse_args()
    count, problems = lint(args.tree, args.descriptor, args.compiled)
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{count} command files, {len(problems)} problems", file=sys.stderr)
        return 1
    print(f"{count} command files, clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
