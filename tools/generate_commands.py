#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Generate one file per command from the descriptor and the wiki.

    python3 tools/generate_commands.py [--out fccli/lib/commands] [--force]

Writes a file for every command in fccli/descriptor.json that has none.
An existing file is left alone -- it may carry authored fields and a
body somebody wrote -- unless --force, which is for a first generation
or a deliberate reset. Keeping generated fields current in an existing
file is reconcile's job, not this one's.

The body is the wiki page's Description, stripped of images and links,
followed by the page's SeeAlso. A command with no page gets its tooltip.
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
import docs_clone  # noqa: E402

DESCRIPTOR = os.path.join(ROOT, "fccli", "descriptor.json")
DEFAULT_OUT = os.path.join(ROOT, "fccli", "lib", "commands")

IMG = re.compile(r"!?\[[^\]]*\]\([^)]*\.(?:png|svg|jpg|jpeg|gif)[^)]*\)|<img[^>]*>", re.I)
TAG = re.compile(r"<[^>]+>")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BOLD = re.compile(r"\*\*([^*]*)\*\*")
VERSION = re.compile(r"\(v\d[\w.]*\)")
DEFLIST = re.compile(r"\s+:\s+")
CAPTION = re.compile(r"^\*[^*]+\*$")
SECTION = re.compile(r"^## +(.*?)\s*$", re.M)
FIELD = re.compile(r"^\s*(\w+):\s*(.*?)\s*$", re.M)


def page_parts(text):
    """(GuiCommand fields, description text) of a wiki page.

    The page's frontmatter is YAML-shaped and not YAML: `Shortcut: **G**
    **C**` is an alias to a parser. The fields are one per line, so a
    line is what is read.
    """
    front = {}
    m = cf.FRONT.match(text)
    if m:
        front = {k: v for k, v in FIELD.findall(m.group(1)) if v}
        text = text[m.end():]
    sections = list(SECTION.finditer(text))
    description = ""
    for i, sec in enumerate(sections):
        if sec.group(1).lower() == "description":
            end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
            description = text[sec.end():end]
            break
    return front, clean(description)


def clean(md):
    """Wiki markdown as plain prose: no images, links flattened, bold dropped."""
    md = IMG.sub("", md)
    md = LINK.sub(r"\1", md)
    md = BOLD.sub(r"\1", md)
    md = TAG.sub("", md)
    md = VERSION.sub("", md)
    md = DEFLIST.sub(" ", md)
    paragraphs = []
    for para in re.split(r"\n\s*\n", md):
        lines = [" ".join(l.split()) for l in para.splitlines()]
        joined = " ".join(l for l in lines if l).strip()
        if not joined or CAPTION.match(joined):
            continue        # an image's caption, with the image gone
        paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def see_also(front):
    raw = (front or {}).get("SeeAlso")
    if not raw:
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def body_for(entry, pages):
    """The seeded body, and where it came from."""
    name = entry["name"]
    page = entry.get("wiki") or name
    path = pages.get(page) or pages.get(name)
    if path:
        with open(path, encoding="utf-8") as fh:
            front, description = page_parts(fh.read())
        if description:
            body = description
            also = see_also(front)
            if also:
                body += "\n\n## See also\n\n" + "\n".join(f"- {p}" for p in also)
            return body, "wiki"
    tooltip = entry.get("tooltip") or entry.get("label") or name
    return tooltip.rstrip(".") + ".", "tooltip"


def generate(out, force=False, quiet=False):
    with open(DESCRIPTOR, encoding="utf-8") as fh:
        descriptor = json.load(fh)
    clone = docs_clone.ensure(quiet=quiet)
    pages = docs_clone.pages(clone) if clone else {}
    rev = docs_clone.revision(clone) if clone else None
    stamp = descriptor.get("freecad")
    written = skipped = 0
    sources = {"wiki": 0, "tooltip": 0}
    for name, entry in sorted(descriptor["commands"].items()):
        path = cf.path_for(out, name, entry.get("workbench"))
        if os.path.exists(path) and not force:
            skipped += 1
            continue
        generated = {
            "freecad": stamp,
            "label": entry.get("label"),
            "tooltip": entry.get("tooltip"),
            "toolbar": entry.get("toolbar"),
            "menu": entry.get("menu"),
            "shortcut": entry.get("shortcut"),
            "workbench": entry.get("workbench"),
            "wiki": entry.get("wiki"),
            "wiki_rev": rev,
        }
        body, source = body_for(entry, pages)
        sources[source] += 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(cf.render(name, generated, {}, body))
        written += 1
    if not quiet:
        print(f"{written} written, {skipped} left alone; bodies from "
              f"wiki {sources['wiki']}, tooltip {sources['tooltip']}; "
              f"wiki @ {rev or 'no clone'}")
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    generate(args.out, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
