#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a new harvest changes, and -- with --apply -- the tree brought up to it.

    python3 tools/reconcile.py --descriptor <fresh>.json [--apply]

ADR-100's prize. The committed descriptor and the tree agree (the lint
says so); a fresh harvest is the other side. Per command, per field, a
three-way merge whose base is the file's generated: block:

    added        a command the tree has no file for      -> written
    removed      a file for a command the harvest lost   -> moved to _retired/
    re-homed     workbench changed                       -> file moves directory
    changed      label, tooltip, toolbar, menu, shortcut, wiki
                                                         -> generated: rewritten
    reseeded     body never edited, and the page moved   -> body rewritten
    conflict     body edited, and the page moved         -> reported, left alone
    identity     an authored verb equal to the name the factory now derives

Authored fields are never touched. Without --apply nothing is written;
the report is the diff a release PR reads. With --apply the tree, the
descriptor and the compiled dictionary are all brought to the new
harvest together, so the lint holds afterwards.
"""

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import command_files as cf  # noqa: E402
import compile_dictionary as cd  # noqa: E402
import docs_clone  # noqa: E402
import generate_commands as gen  # noqa: E402

DESCRIPTOR = os.path.join(ROOT, "fccli", "descriptor.json")
MIRRORED = ("label", "tooltip", "toolbar", "menu", "shortcut", "wiki")


def _slug(text):
    """factory._slug, without importing the package."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[&.]", "", text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unnamed"


class Report:
    def __init__(self):
        self.added, self.removed, self.rehomed = [], [], []
        self.changed, self.reseeded, self.conflicts = [], [], []
        self.identity, self.stamp = [], None

    def empty(self):
        return not any((self.added, self.removed, self.rehomed, self.changed,
                        self.reseeded, self.conflicts, self.identity,
                        self.stamp))

    def text(self):
        lines = []
        if self.stamp:
            lines.append(f"freecad {self.stamp[0]} -> {self.stamp[1]}")
        for title, items in (("added", self.added), ("removed", self.removed),
                             ("re-homed", self.rehomed),
                             ("changed", self.changed),
                             ("reseeded", self.reseeded),
                             ("conflict", self.conflicts),
                             ("identity", self.identity)):
            if not items:
                continue
            lines.append(f"{title} ({len(items)})")
            lines.extend(f"  {i}" for i in items[:40])
            if len(items) > 40:
                lines.append(f"  ... {len(items) - 40} more")
        return "\n".join(lines) if lines else "nothing changed"


def reconcile(tree, old_path, new_path, apply=False, refresh_docs=False,
              quiet=False):
    with open(old_path, encoding="utf-8") as fh:
        old = json.load(fh)
    with open(new_path, encoding="utf-8") as fh:
        new = json.load(fh)
    report = Report()
    if old.get("freecad") != new.get("freecad"):
        report.stamp = (old.get("freecad"), new.get("freecad"))
    clone = docs_clone.ensure(refresh=refresh_docs, quiet=quiet)
    pages = docs_clone.pages(clone) if clone else {}
    rev = docs_clone.revision(clone) if clone else None
    stamp = new.get("freecad")

    files = {}
    for rel, full in cf.walk(tree):
        front, body = cf.read(full)
        files[front.get("command")] = (rel, full, front, body)

    for name, entry in sorted(new["commands"].items()):
        if name not in files:
            report.added.append(name)
            if apply:
                body, src = gen.body_for(entry, pages)
                path = cf.path_for(tree, name, entry.get("workbench"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(cf.render(name, gen.generated_for(
                        entry, stamp, rev if src == "wiki" else None, body),
                        {}, body))
            continue
        rel, full, front, body = files[name]
        generated = dict(front.get("generated") or {})
        authored = cf.authored_of(front)
        diffs = [k for k in MIRRORED if generated.get(k) != entry.get(k)]
        moved = cf.workbench_dir(generated.get("workbench")) != \
            cf.workbench_dir(entry.get("workbench"))
        for k in diffs:
            report.changed.append(
                f"{name}: {k} {generated.get(k)!r} -> {entry.get(k)!r}")
        if moved:
            report.rehomed.append(
                f"{name}: {cf.workbench_dir(generated.get('workbench'))}/ -> "
                f"{cf.workbench_dir(entry.get('workbench'))}/")
        # The body. Unedited means it still hashes to its seed.
        new_body, src = gen.body_for(entry, pages)
        edited = cf.edited(front, body)
        page_moved = cf.seed_of(new_body) != (generated.get("seed")
                                              or cf.seed_of(body))
        page_rev = rev if src == "wiki" else None
        write_body = body
        if page_moved and not edited:
            report.reseeded.append(name)
            write_body = new_body
        elif page_moved and edited:
            report.conflicts.append(
                f"{name}: the page changed and the body was written by hand "
                f"({rel})")
        # Authored verb that the factory would now derive on its own.
        if authored.get("verb") and authored["verb"] == _slug(entry.get("label")):
            report.identity.append(f"{name}: verb {authored['verb']!r} is what "
                                   f"the label gives now; delete it")
        stale = (diffs or moved or write_body is not body
                 or generated.get("freecad") != stamp
                 or (not edited and generated.get("wiki_rev") != page_rev))
        if apply and stale:
            regenerated = gen.generated_for(
                entry, stamp, page_rev if page_moved or not edited
                else generated.get("wiki_rev"),
                write_body if not edited else new_body)
            if edited:
                # Keep the seed the person's body departed from, unless the
                # page moved, in which case the seed is the new page and the
                # conflict says so.
                regenerated["seed"] = (cf.seed_of(new_body) if page_moved
                                       else generated.get("seed"))
            text = cf.render(name, regenerated, authored, write_body)
            path = cf.path_for(tree, name, entry.get("workbench"))
            if moved:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                os.remove(full)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)

    for name in sorted(set(files) - set(new["commands"])):
        rel, full, front, body = files[name]
        report.removed.append(f"{name} ({rel})")
        if apply:
            dest = os.path.join(tree, "_retired", rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(full, dest)

    if apply:
        shutil.copyfile(new_path, old_path)
        data = cd.compile_tree(tree)
        with open(cd.DEFAULT_OUT if tree == cd.DEFAULT_TREE else
                  os.path.join(os.path.dirname(tree), "dictionary.json"),
                  "w", encoding="utf-8") as fh:
            fh.write(cd.dump(data))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--descriptor", required=True,
                    help="a fresh descriptor, from generate_descriptor --out")
    ap.add_argument("--tree", default=cd.DEFAULT_TREE)
    ap.add_argument("--against", default=DESCRIPTOR,
                    help="the committed descriptor (default fccli/descriptor.json)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--refresh-docs", action="store_true")
    args = ap.parse_args()
    report = reconcile(args.tree, args.against, args.descriptor,
                       apply=args.apply, refresh_docs=args.refresh_docs)
    print(report.text())
    if args.apply:
        print("applied; run make lint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
