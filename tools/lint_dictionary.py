#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Check the command tree against the descriptor and the compiled form.

    python3 tools/lint_dictionary.py [--tree ...] [--descriptor ...] [--compiled ...]

ADR-100's five rules, and the description spec's mechanical half:

  1. every file names a command in the descriptor, and every command has
     a file
  2. a file's generated: block matches the descriptor field for field --
     a hand edit inside it belongs in an authored field or in etc/
  3. authored fields are well-formed: requires from the closed
     vocabulary, panel pick or null, rank registry or null, a type
     block's keys from the named set with an `of` that is a real type
  4. verb names asked for are unique across the tree
  5. the compiled dictionary is what the tree compiles to

and, from GH #47, two spec groups over the same tree. Group A is what a
person reads before typing a command -- A2 the synopsis, A3 the argument
glosses, A5 the example, A6 the family -- and lives in descriptions.py.
Group D is what happens as they type -- D1 the choices, D3 the completion
pools, D4 the naming, D5 the units -- and lives in interaction.py. Both
build the registry and check the verbs themselves rather than a second
model of them.

Each group splits the same way: a fault that silently changes what a
command does is a problem like any other, and the rest is a report.
`--describe` prints group A's reports and `--grammar` group D's;
`--report FILE` writes both into the one per-command JSON the verification
campaign reads; `--strict-descriptions` and `--strict-grammar` make every
line of one group fail.

Exit 1 on any error. Rule 2 is the one that keeps a generated field safe
to regenerate.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import command_files as cf  # noqa: E402
import compile_dictionary as cd  # noqa: E402
import descriptions as dsc  # noqa: E402
import interaction as ixn  # noqa: E402

DESCRIPTOR = os.path.join(ROOT, "fccli", "descriptor.json")

# Descriptor field -> generated: field, compared value for value. freecad
# Descriptor field -> generated: field, compared value for value. freecad
# is compared to the descriptor's stamp. wiki_rev is the tool's own: null,
# or the short hash of the documentation commit the body was seeded from.
# seed is the tool's too, and reconcile owns both.
MIRRORED = ("label", "tooltip", "toolbar", "menu", "shortcut", "workbench",
            "wiki")


def _kind(value, *types):
    return value is None or isinstance(value, types)


def lint(tree, descriptor_path, compiled_path, described=None,
         grammared=None):
    problems = []
    with open(descriptor_path, encoding="utf-8") as fh:
        descriptor = json.load(fh)
    commands = descriptor["commands"]
    seen, verbs, choices, tuned = {}, {}, {}, {}
    # The parsed files, for the description pass: it wants the body and
    # the generated block, and the tree is worth walking once.
    files = {}
    # Every type a tier-1 verb is built from, for `of` to be checked
    # against. Read from the descriptor's own verb table.
    types_built = {v.get("type") for v in descriptor.get("verbs", {}).values()}
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
        files[name] = (rel.replace(os.sep, "/"), front, _body)
        want_dir = cf.workbench_dir(entry.get("workbench"))
        if os.path.dirname(rel) != want_dir:
            problems.append(f"{rel}: belongs in {want_dir}/ (rule 1)")
        if os.path.basename(rel) != name + ".md":
            problems.append(f"{rel}: file is not named {name}.md (rule 1)")
        generated = front.get("generated") or {}
        if not isinstance(generated, dict):
            problems.append(f"{rel}: generated must be a mapping (rule 2)")
            generated = {}
        for extra in sorted(set(generated) - set(cf.GENERATED)):
            problems.append(f"{rel}: generated.{extra} is not a field the "
                            f"tool writes (rule 2)")
        for key in MIRRORED:
            if generated.get(key) != entry.get(key):
                problems.append(
                    f"{rel}: generated.{key} is {generated.get(key)!r}, the "
                    f"descriptor says {entry.get(key)!r} -- a change here "
                    f"belongs in an authored field (rule 2)")
        wiki_rev = generated.get("wiki_rev")
        if wiki_rev is not None and not (isinstance(wiki_rev, str)
                                         and re.fullmatch(r"[0-9a-f]{7,40}", wiki_rev)):
            problems.append(f"{rel}: generated.wiki_rev {wiki_rev!r} is not a "
                            f"commit hash or null (rule 2)")
        if generated.get("freecad") != descriptor.get("freecad"):
            problems.append(f"{rel}: generated.freecad is "
                            f"{generated.get('freecad')!r}, the descriptor is "
                            f"{descriptor.get('freecad')!r} (rule 2)")
        authored = cf.authored_of(front)
        for extra in sorted(set(front) - set(cf.AUTHORED) - {"command", "generated"}):
            problems.append(f"{rel}: unknown field {extra!r} (rule 3)")
        # Shapes first, so a wrong type is one message rather than a crash
        # or eleven per-character complaints.
        shape = {
            "verb": _kind(authored["verb"], str),
            "aliases": isinstance(authored["aliases"], list)
                       and all(isinstance(a, str) for a in authored["aliases"]),
            "requires": isinstance(authored["requires"], list)
                        and all(isinstance(r, str) for r in authored["requires"]),
            "also": isinstance(authored.get("also") or [], list),
            "panel": _kind(authored["panel"], str),
            "family": _kind(authored["family"], str, bool),
            "choice": _kind(authored["choice"], str),
            "rank": _kind(authored["rank"], str),
            "type": _kind(authored["type"], dict),
        }
        for key, ok in shape.items():
            if not ok:
                problems.append(f"{rel}: {key} has the wrong shape (rule 3)")
        if shape["requires"]:
            for req in authored["requires"]:
                if req not in cf.REQUIRES:
                    problems.append(f"{rel}: requires {req!r} is not one of "
                                    f"{sorted(cf.REQUIRES)} (rule 3)")
        if shape["panel"] and authored["panel"] not in cf.PANEL:
            problems.append(f"{rel}: panel must be pick or null (rule 3)")
        if shape["rank"] and authored["rank"] not in cf.RANK:
            problems.append(f"{rel}: rank must be registry or null (rule 3)")
        if shape["type"] and authored["type"]:
            for key in sorted(set(authored["type"]) - cf.TYPE_KEYS):
                problems.append(f"{rel}: type.{key} is not one of "
                                f"{sorted(cf.TYPE_KEYS)} (rule 3)")
            of = authored["type"].get("of")
            if not of:
                problems.append(f"{rel}: a type block needs `of` (rule 3)")
            elif of not in types_built:
                problems.append(f"{rel}: type of {of!r} is not a type any "
                                f"command builds (rule 3)")
            elif of in tuned:
                problems.append(f"{rel}: type {of} is also tuned by "
                                f"{tuned[of]} (rule 4)")
            else:
                tuned[of] = rel
        fam, choice = authored["family"], authored["choice"]
        if shape["family"] and shape["choice"]:
            if fam is False and choice is not None:
                problems.append(f"{rel}: family: false takes no choice (rule 3)")
            elif fam is True:
                problems.append(f"{rel}: family must be a name or false (rule 3)")
            elif isinstance(fam, str) != isinstance(choice, str):
                problems.append(f"{rel}: family and choice go together (rule 3)")
        if isinstance(authored.get("family"), str) and authored.get("choice"):
            fam = authored["family"].lower()
            for spelling in [authored["choice"]] + list(authored.get("also") or []):
                key = (fam, str(spelling).lower())
                if key in choices:
                    problems.append(f"{rel}: choice {spelling!r} in family "
                                    f"{authored['family']!r} is also "
                                    f"{choices[key]} (rule 4)")
                choices[key] = rel
        verb = authored["verb"]
        if verb and shape["verb"]:
            if verb in verbs:
                problems.append(f"{rel}: verb {verb!r} is also asked for by "
                                f"{verbs[verb]} (rule 4)")
            verbs[verb] = rel
        if shape["aliases"]:
            for alias in authored["aliases"]:
                if alias in verbs:
                    problems.append(f"{rel}: alias {alias!r} is also asked for "
                                    f"by {verbs[alias]} (rule 4)")
                verbs[alias] = rel
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
    # The description spec (A2, A3, A5, A6), over the tree as compiled --
    # not over the file on disk, so a tree the lint was pointed at is
    # checked as itself and rule 5 stays the one that compares the two.
    try:
        found = dsc.inspect(descriptor, cd.compile_tree(tree), files)
    except Exception as exc:
        # A problem, not a report. The catch is here so a tree that will
        # not compile is rule 5's message rather than a traceback -- but
        # five hard-fail classes live inside inspect(), and a pass that
        # declined to run and said so quietly is the vacuous pass this
        # lint exists to refuse. Nothing else notices: rule 5 compares the
        # compiled dictionary to the tree and knows nothing about these.
        found = dsc.Findings()
        found.problems.append(f"the description rules did not run: "
                              f"{exc.__class__.__name__}: {exc} (A2)")
    problems.extend(found.problems)
    if described is not None:
        described.append(found)
    # The grammar spec (D1, D3, D4, D5), over the same compiled tree. A
    # separate pass rather than a section of the last one: the two groups
    # answer to different flags, and a group A fault that stops descriptions
    # short must not take group D's findings with it.
    try:
        grammar = ixn.inspect(descriptor, cd.compile_tree(tree), files)
    except Exception as exc:
        # A problem, for the reason the description catch is one: five
        # hard-fail classes live inside inspect() -- a registry that will
        # not build, a from_source with no pool names left in it, a
        # hand-authored tier that moved out from under authored_commands
        # or authored_verbs -- and a pass that declined to run and said so
        # quietly is the vacuous pass this lint exists to refuse.
        grammar = ixn.Findings()
        grammar.problems.append(f"the grammar rules did not run: "
                                f"{exc.__class__.__name__}: {exc} (D1)")
    problems.extend(grammar.problems)
    if grammared is not None:
        grammared.append(grammar)
    return len(seen), problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", default=cd.DEFAULT_TREE)
    ap.add_argument("--descriptor", default=DESCRIPTOR)
    ap.add_argument("--compiled", default=cd.DEFAULT_OUT)
    ap.add_argument("--describe", action="store_true",
                    help="print the description report (A2, A3, A5, A6) "
                         "rather than only counting it")
    ap.add_argument("--report", metavar="FILE",
                    help="write the per-command description record, which "
                         "is what A1 and A4 are read from")
    ap.add_argument("--grammar", action="store_true",
                    help="print the grammar report (D1, D3, D4, D5) "
                         "rather than only counting it")
    ap.add_argument("--strict-descriptions", action="store_true",
                    help="fail on every description report, not only on "
                         "the faults that change what a command does")
    ap.add_argument("--strict-grammar", action="store_true",
                    help="fail on every grammar report, not only on the "
                         "faults that change what a command does")
    args = ap.parse_args()
    described, grammared = [], []
    count, problems = lint(args.tree, args.descriptor, args.compiled,
                           described=described, grammared=grammared)
    found = described[0] if described else dsc.Findings()
    grammar = grammared[0] if grammared else ixn.Findings()
    if args.strict_descriptions:
        problems = problems + found.reports
    if args.strict_grammar:
        problems = problems + grammar.reports
    reports = [] if args.strict_descriptions else found.reports
    reports += [] if args.strict_grammar else grammar.reports
    if args.describe:
        for r in ([] if args.strict_descriptions else found.reports):
            print(r)
    if args.grammar:
        for r in ([] if args.strict_grammar else grammar.reports):
            print(r)
    if args.report:
        with open(args.descriptor, encoding="utf-8") as fh:
            dsc.write_report(found, args.report, json.load(fh),
                             grammar=grammar)
        print(f"{args.report}: {len(found.records)} commands described")
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{count} command files, {len(problems)} problems", file=sys.stderr)
        return 1
    tail = ""
    if reports:
        shown = args.describe or args.strict_descriptions
        shown = shown and (args.grammar or args.strict_grammar)
        tail = (f", {len(reports)} spec reports"
                + ("" if shown else
                   " (--describe, --grammar to read them)"))
    print(f"{count} command files, clean{tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
