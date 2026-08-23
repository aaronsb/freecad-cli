#!/usr/bin/env python3
"""Pass C: what each command actually builds, read from its source.

The naive join -- Part_Box to Part::Box -- looks right on the primitives and
is wrong everywhere else: BIM_Box, Draft_Line and CAM_Helix all have their
own objects, and a name match happily points them at Part's. The
relationship is not in the names.

It is in the source. Nearly every FreeCAD command outside the C++ core is a
Python class registered with Gui.addCommand("Name", Cls()), and the class
body says what it builds -- doc.addObject("Part::Box", ...) or
Draft.make_wire(...). This walks the Mod trees with ast and reads it off.

Addons come along for free: they register commands the same way, so a
third-party workbench is scanned by the same pass with no special casing.

    python3 tools/harvest_sources.py [--out sources.json]
"""

import argparse
import ast
import json
import os
import re
import sys

MOD_ROOTS = [
    "/usr/lib/freecad/Mod",
    "/usr/share/freecad/Mod",
    os.path.expanduser("~/.local/share/FreeCAD/v1-1/Mod"),
    os.path.expanduser("~/.local/share/FreeCAD/Mod"),
    os.path.expanduser("~/.FreeCAD/Mod"),
]

# Calls whose first string argument names a document object type.
TYPE_CALLS = {"addObject", "createObject", "addFeature"}

# FreeCAD commands routinely build objects by handing Python source to
# doCommand as a string, so the type name never appears as a call argument
# the AST can see. Read those out of the string literals too.
EMBEDDED = re.compile(r"""(?:addObject|createObject)\s*\(\s*["']([A-Za-z_]+(?:::[A-Za-z_0-9]+)+)["']""")


def literal(node):
    return node.value if isinstance(node, ast.Constant) and \
        isinstance(node.value, str) else None


class BodyScanner(ast.NodeVisitor):
    """Collect object types and helper calls from any block of code."""

    def __init__(self):
        self.types = set()
        self.calls = set()

    def visit_Constant(self, node):
        if isinstance(node.value, str) and "::" in node.value:
            self.types.update(EMBEDDED.findall(node.value))
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name in TYPE_CALLS and node.args:
            tid = literal(node.args[0])
            if tid and "::" in tid:
                self.types.add(tid)
        if name:
            self.calls.add(name)
        self.generic_visit(node)


def scan_body(nodes):
    scanner = BodyScanner()
    for node in nodes:
        scanner.visit(node)
    return scanner


def scan_file(path):
    """Return {command_name: {"types": [...], "makers": [...]}} for one file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read(), path)
    except (SyntaxError, ValueError, OSError):
        return {}, {}

    classes, functions = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = scan_body(node.body)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = scan_body(node.body)

    # Gui.addCommand("Name", SomeClass()) -- and the occasional bare string.
    registered = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "addCommand" or not node.args:
            continue
        cmd = literal(node.args[0])
        if not cmd:
            continue
        cls = None
        if len(node.args) > 1:
            arg = node.args[1]
            if isinstance(arg, ast.Call):
                cls = getattr(arg.func, "id", None) or \
                    getattr(arg.func, "attr", None)
            else:
                cls = getattr(arg, "id", None)
        registered[cmd] = cls
    return registered, classes, functions


def module_of(path):
    for root in MOD_ROOTS:
        if path.startswith(root + os.sep):
            return path[len(root) + 1:].split(os.sep)[0]
    return "?"


MAX_HOPS = 2

# Types so generic that resolving to them says nothing about a command.
GENERIC = {
    "App::DocumentObjectGroup", "App::FeatureTest", "App::Part",
    "App::Link", "App::LinkGroup", "App::Origin", "App::Plane",
    "App::Line", "App::MaterialObjectPython", "App::FeaturePython",
    "Part::Feature", "Part::FeaturePython", "Mesh::Feature",
    "App::DocumentObject", "App::GeoFeature",
}


def scan():
    """Two sweeps: index every function, then resolve each command through it.

    A command class rarely calls addObject itself. It calls Draft.make_wire,
    which calls something else, which finally names the type. So the call
    graph is walked a few hops before giving up.
    """
    stats = {"files": 0, "roots": [], "classes": 0, "functions": 0}
    raw, all_functions = [], {}

    for root in MOD_ROOTS:
        if not os.path.isdir(root):
            continue
        stats["roots"].append(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ("__pycache__", ".git", "test", "tests")]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                registered, classes, functions = scan_file(path)
                stats["files"] += 1
                stats["classes"] += len(classes)
                stats["functions"] += len(functions)
                # Index per addon. A global index by bare function name
                # collides across 15k functions and smears every module's
                # types into every other module's commands.
                addon = module_of(path)
                index = all_functions.setdefault(addon, {})
                for name, scanner in list(functions.items()) + list(classes.items()):
                    slot = index.setdefault(name, BodyScanner())
                    slot.types |= scanner.types
                    slot.calls |= scanner.calls
                if registered:
                    raw.append((path, root, registered, classes))

    def resolve(scanner, addon):
        """Follow the call graph inside one addon until a type turns up.

        Returns (types, confidence). Direct is a type named in the command
        class itself; traced is one found a hop or two away and worth less.
        """
        direct = {t for t in scanner.types if t not in GENERIC}
        if direct:
            return sorted(direct), "direct"
        index = all_functions.get(addon, {})
        types, seen, frontier = set(), set(), set(scanner.calls)
        for _ in range(MAX_HOPS):
            if types or not frontier:
                break
            nxt = set()
            for name in frontier - seen:
                seen.add(name)
                target = index.get(name)
                if target is None:
                    continue
                types |= {t for t in target.types if t not in GENERIC}
                nxt |= target.calls
            frontier = nxt
        if not types:
            return [], "none"
        # A wide result means the trace wandered, not that the command
        # builds nine different things.
        return sorted(types), ("traced" if len(types) <= 3 else "weak")

    commands = {}
    for path, root, registered, classes in raw:
        for cmd, cls in registered.items():
            scanner = classes.get(cls)
            addon = module_of(path)
            types, confidence = resolve(scanner, addon) if scanner else ([], "none")
            commands[cmd] = {
                "types": types,
                "confidence": confidence,
                "class": cls,
                "addon": addon,
                "source": os.path.relpath(path, root),
            }
    return commands, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="sources.json")
    args = ap.parse_args()
    commands, stats = scan()
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"commands": commands, "stats": stats}, fh,
                  indent=1, sort_keys=True)
    conf = {}
    for c in commands.values():
        conf[c["confidence"]] = conf.get(c["confidence"], 0) + 1
    with_types = sum(1 for c in commands.values() if c["types"])
    addons = {}
    for c in commands.values():
        addons[c["addon"]] = addons.get(c["addon"], 0) + 1
    print(f"  sources: {stats['files']} files, {len(commands)} registered "
          f"commands, {with_types} resolve to a type")
    print("  confidence: " + ", ".join(f"{k}={v}" for k, v in
                                       sorted(conf.items(), key=lambda x: -x[1])))
    print("  by addon: " + ", ".join(
        f"{k}={v}" for k, v in sorted(addons.items(), key=lambda x: -x[1])[:10]))


if __name__ == "__main__":
    main()
