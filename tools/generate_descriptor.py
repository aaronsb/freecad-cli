#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Build fccli/descriptor.json from FreeCAD's two registries.

FreeCAD has no Discovery API. It has a command registry that knows names,
labels and grouping but no parameters, and a type registry that knows typed
parameters but nothing about naming or invocation. This joins them.

Each registry is harvested in its own process:

  types      headless under freecadcmd. Instantiating a type can abort the
             process from C++, so the harvester claims each type before
             touching it and this driver restarts past whatever killed it.
  commands   under a virtual display, since QAction metadata needs a GUI.

    python3 tools/generate_descriptor.py [--out fccli/descriptor.json]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(ROOT, "fccli", "descriptor.json")
MAX_RESTARTS = 40


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ------------------------------------------------------------ pass A: types

def read_jsonl(path):
    """Return (records, suspect, done).

    ``suspect`` is whatever the harvester was last touching. Usually that is
    a type claimed but never resolved. It can also be a type that resolved
    and then aborted the process on the way out -- removeObject destroys the
    object, and that is its own opportunity to crash -- so the last resolved
    type is the fallback suspect.
    """
    records, claimed, last, done = {}, None, None, False
    if not os.path.exists(path):
        return records, None, done
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if "_probing" in rec:
                claimed = rec["_probing"]
            elif "_teardown" in rec:
                if claimed == rec["_teardown"]:
                    claimed = None
            elif "_done" in rec:
                done = True
            elif "type" in rec:
                records[rec["type"]] = rec
                last = rec["type"]
                if claimed == rec["type"]:
                    claimed = None
    return records, (claimed or last), done


def harvest_types(workdir, verbose):
    path = os.path.join(workdir, "types.jsonl")
    skip, crashers = [], []
    for attempt in range(MAX_RESTARTS):
        env = dict(os.environ, FCCLI_OUT=path, FCCLI_SKIP=",".join(skip))
        proc = sh(["freecadcmd", os.path.join(HERE, "harvest_types.py")], env=env)
        records, claimed, done = read_jsonl(path)
        if done:
            if verbose:
                print(f"  types: {len(records)} probed, "
                      f"{len(crashers)} crashed the process")
            return records, crashers
        if claimed is None:
            print("  types: harvester stopped with nothing in flight; "
                  f"rc={proc.returncode}", file=sys.stderr)
            return records, crashers
        skip.append(claimed)
        crashers.append(claimed)
        if verbose:
            print(f"    {claimed} aborted FreeCAD (rc={proc.returncode}), "
                  "restarting past it")
    print("  types: too many restarts, giving up", file=sys.stderr)
    return read_jsonl(path)[0], crashers


# --------------------------------------------------------- pass B: commands

def harvest_commands(workdir, verbose):
    path = os.path.join(workdir, "commands.json")
    env = dict(os.environ, FCCLI_OUT=path)
    # harvest_commands activates every workbench to read its QActions, so
    # this is a full GUI. Two ways it used to land on the operator's screen:
    # falling back to their DISPLAY whenever one was set, and -- once that
    # was fixed elsewhere -- not pinning the Qt platform, since Qt6 picks
    # its plugin from XDG_SESSION_TYPE and a Wayland session ignores the
    # virtual display entirely.
    runner = []
    if shutil.which("xvfb-run"):
        runner = ["xvfb-run", "-a", "-s", "-screen 0 1600x1000x24"]
        env["QT_QPA_PLATFORM"] = "xcb"
    elif not os.environ.get("DISPLAY"):
        print("  commands: needs xvfb-run, or a DISPLAY", file=sys.stderr)
        return {}
    proc = sh(runner + ["freecad", os.path.join(HERE, "harvest_commands.py")],
              env=env)
    if not os.path.exists(path):
        print("  commands: harvester produced nothing; rc=%s" % proc.returncode,
              file=sys.stderr)
        print(proc.stderr[-800:], file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if verbose:
        print(f"  commands: {len(data['commands'])} across "
              f"{len(data['workbenches'])} workbenches")
    return data


# ------------------------------------------------------------------- join

def candidates(command):
    """Same-module name match only.

    Part_Box -> Part::Box holds for the primitives. Reaching outside the
    module -- letting BIM_Box or CAM_Helix fall back to Part:: -- produced
    confident nonsense, so the fallbacks are gone.
    """
    if "_" not in command:
        return []
    module, _, rest = command.partition("_")
    return [f"{module}::{rest}", f"{module}::{rest.replace('_', '')}"]


def link(commands, types, sources, overrides):
    """Attach a type to a command only where the evidence is real.

    Three sources, in descending trust: a hand-written override, a type
    named in the command's own class body, and an exact same-module name
    match. Types reached by tracing the call graph are recorded as
    suggestions for whoever writes the patch, never as links -- tracing put
    BIM_Tutorial on Part::Extrusion.
    """
    links, suggestions, unlinked = {}, {}, []
    for name in commands:
        src = sources.get(name, {})
        tid = overrides.get(name)
        how = "override" if tid else None
        if tid is None and src.get("confidence") == "direct":
            hit = next((t for t in src["types"]
                        if types.get(t, {}).get("params")), None)
            tid, how = hit, "source"
        if tid is None:
            hit = next((c for c in candidates(name)
                        if types.get(c, {}).get("params")), None)
            tid, how = hit, "name"
        if tid and types.get(tid, {}).get("params"):
            links[name] = {"type": tid, "via": how}
        else:
            unlinked.append(name)
            if src.get("types"):
                suggestions[name] = {"types": src["types"],
                                     "confidence": src["confidence"]}
    return links, suggestions, unlinked


# Which module keeps the bare name when two types slug the same. Part::Box
# and PartDesign::Box both want "box"; the solid primitive is what someone
# typing "box" means, and the PartDesign feature becomes "partdesign_box".
MODULE_PRIORITY = ["Part", "Draft", "Sketcher", "PartDesign", "Mesh",
                   "Points", "Surface", "TechDraw", "Spreadsheet", "App"]


def verb_name(tid):
    """Part::Cylinder -> cylinder. The type names the verb; no join needed."""
    stem = tid.split("::")[-1]
    out, prev_lower = [], False
    for ch in stem:
        if ch.isupper() and prev_lower:
            out.append("_")
        out.append(ch.lower())
        prev_lower = ch.islower() or ch.isdigit()
    return "".join(out)


def name_verbs(types):
    """Assign every parametric type a unique verb name.

    A dict comprehension keyed by verb_name silently drops one of every
    colliding pair, which is how Part::Box lost its verb to
    PartDesign::Box. Collisions are resolved by module priority instead, and
    the loser keeps a qualified name rather than vanishing.
    """
    buckets = {}
    for tid, entry in types.items():
        if entry.get("params"):
            buckets.setdefault(verb_name(tid), []).append(tid)

    def rank(tid):
        module = tid.split("::")[0]
        return (MODULE_PRIORITY.index(module)
                if module in MODULE_PRIORITY else len(MODULE_PRIORITY), tid)

    verbs, collisions = {}, {}
    for base, tids in buckets.items():
        if len(tids) == 1:
            verbs[base] = tids[0]
            continue
        ordered = sorted(tids, key=rank)
        collisions[base] = ordered
        verbs[base] = ordered[0]
        for tid in ordered[1:]:
            verbs[f"{tid.split('::')[0].lower()}_{base}"] = tid
    return verbs, collisions


# ----------------------------------------------------------------- report

def report(payload, types, commands, links, suggestions, unlinked, sources,
           crashers, elapsed):
    joined = links
    parametric = [t for t in types.values() if t.get("params")]
    kept = sum(len(t.get("params", [])) for t in types.values())
    dropped = sum(t.get("dropped", 0) for t in types.values())
    errored = [t for t in types.values() if "error" in t]

    groups = {}
    for c in commands.values():
        groups[c.get("toolbar") or c.get("menu") or "(ungrouped)"] = \
            groups.get(c.get("toolbar") or c.get("menu") or "(ungrouped)", 0) + 1
    grouped = sum(v for k, v in groups.items() if k != "(ungrouped)")

    kinds = {}
    for t in types.values():
        for p in t.get("params", []):
            kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1

    vias = {}
    for l in links.values():
        vias[l["via"]] = vias.get(l["via"], 0) + 1
    n = max(1, len(commands))
    lines = [
        "",
        "=" * 68,
        "  FreeCAD CLI  --  descriptor coverage",
        "=" * 68,
        f"  FreeCAD              {payload['freecad']}",
        f"  workbenches          {len(payload['workbenches'])}",
        "",
        f"  commands             {len(commands)}",
        f"    grouped by UI      {grouped:>5}  ({grouped * 100 // n}%)"
        f"  across {len(groups) - 1} toolbars/menus",
        f"    linked to a type   {len(links):>5}"
        f"   ({', '.join(f'{k}={v}' for k, v in sorted(vias.items()))})",
        f"    suggestions only   {len(suggestions):>5}"
        f"   -> traced, for patch authors",
        f"    unlinked           {len(unlinked):>5}"
        f"  ({len(unlinked) * 100 // n}%)   -> tier 0, runCommand",
        "",
        f"  VERBS GENERATED",
        f"    from types         {len(payload['verbs']):>5}"
        f"   tier 1, parameterized -- needs no link",
        f"      name collisions  {len(payload.get('collisions', {})):>5}"
        f"   resolved by module priority",
        f"    from commands      {len(commands):>5}"
        f"   tier 0, runCommand",
        "",
        f"  types probed         {len(types)}",
        f"    with parameters    {len(parametric):>5}",
        f"    failed to build    {len(errored):>5}",
        f"    aborted FreeCAD    {len(crashers):>5}",
        "",
        f"  properties kept      {kept}",
        f"    noise dropped      {dropped:>5}"
        f"  ({dropped * 100 // max(1, kept + dropped)}% of all properties)",
        "",
        "  parameter kinds:",
    ]
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        lines.append(f"    {v:>5}  {k}")
    lines += ["", "  largest UI groups:"]
    for k, v in sorted(groups.items(), key=lambda x: -x[1])[:8]:
        lines.append(f"    {v:>5}  {k}")
    lines += ["", "  sample type-derived verbs (no command link needed):"]
    for name in ("box", "cylinder", "sphere", "torus", "pad", "pocket",
                 "partdesign_box", "revolution"):
        entry = payload["verbs"].get(name)
        if entry:
            ps = ", ".join(p["name"] for p in entry["params"][:4])
            lines.append(f"    {name:<20} {entry['type']:<26} {ps}")
    lines += ["", "  sample command links:"]
    for name in sorted(links)[:6]:
        l = links[name]
        lines.append(f"    {name:<26} {l['type']:<26} via {l['via']}")
    if crashers:
        lines += ["", "  types that aborted FreeCAD (blocklisted):"]
        for c in crashers[:10]:
            lines.append(f"           {c}")
    lines += ["", "=" * 68, ""]
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--keep", action="store_true",
                    help="keep the intermediate harvest files")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()
    verbose = not args.quiet

    workdir = tempfile.mkdtemp(prefix="fccli-harvest-")
    t0 = time.perf_counter()
    if verbose:
        print("harvesting FreeCAD registries...")
    types, crashers = harvest_types(workdir, verbose)
    cmd_data = harvest_commands(workdir, verbose)
    commands = cmd_data.get("commands", {})

    overrides_path = os.path.join(ROOT, "fccli", "type_overrides.json")
    overrides = {}
    if os.path.exists(overrides_path):
        with open(overrides_path, encoding="utf-8") as fh:
            overrides = json.load(fh)

    sources_path = os.path.join(workdir, "sources.json")
    sh([sys.executable, os.path.join(HERE, "harvest_sources.py"),
        "--out", sources_path])
    sources = {}
    if os.path.exists(sources_path):
        with open(sources_path, encoding="utf-8") as fh:
            sources = json.load(fh).get("commands", {})
    if verbose:
        print(f"  sources: {len(sources)} python-registered commands scanned")

    links, suggestions, unlinked = link(commands, types, sources, overrides)
    named, collisions = name_verbs(types)
    verbs = {name: {"type": tid, "params": types[tid]["params"],
                    "module": types[tid].get("module")}
             for name, tid in named.items()}
    if verbose and collisions:
        print(f"  verbs: {len(verbs)} named, {len(collisions)} name "
              "collisions resolved by module priority")
    payload = {
        "freecad": cmd_data.get("freecad", "unknown"),
        "generated_by": "tools/generate_descriptor.py",
        "workbenches": cmd_data.get("workbenches", []),
        "blocklist": crashers,
        "commands": commands,
        "types": types,
        "verbs": verbs,
        "links": links,
        "suggestions": suggestions,
        "unlinked": sorted(unlinked),
        "collisions": collisions,
        "sources": sources,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)

    report(payload, types, commands, links, suggestions, unlinked, sources,
           crashers, time.perf_counter() - t0)
    print(f"  wrote {args.out}  "
          f"({os.path.getsize(args.out) // 1024} KB) in "
          f"{time.perf_counter() - t0:.0f}s")
    if args.keep:
        print(f"  intermediates in {workdir}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
