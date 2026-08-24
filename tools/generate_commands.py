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
TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
QUOTES = re.compile(r"(?:\\?'){2,3}")   # wiki italics and bold, sometimes escaped
ESCAPED = re.compile(r"\\([^\w\s\\])")   # the conversion escapes punctuation; prose does not
LIST_ITEM = re.compile(r"^\s*(?P<mark>[-*]|\d+\.)\s+")
REDIRECT = re.compile(r"REDIRECT\s+\[[^\]]*\]\((\w+)\.md\)")
SECTION = re.compile(r"^(#{2,3}) +(.*?)\s*$", re.M)
# One field per line. \s would cross the newline and let an empty field
# swallow the next one: "Shortcut: \n SeeAlso: X" read as Shortcut = "SeeAlso: X".
FIELD = re.compile(r"^[ \t]*(\w+):[ \t]*(.*?)[ \t]*$", re.M)
# Sections that describe the tool, first one wins.
DESCRIBES = ("description", "introduction")


def page_parts(text):
    """(GuiCommand fields, description text, redirect target) of a page.

    The page's frontmatter is YAML-shaped and not YAML: `Shortcut: **G**
    **C**` is an alias to a parser. The fields are one per line, so a
    line is what is read. A page that is only a REDIRECT names where to
    look instead; the caller follows one hop.
    """
    front = {}
    m = cf.FRONT.match(text)
    if m:
        front = {k: v for k, v in FIELD.findall(m.group(1)) if v}
        text = text[m.end():]
    r = REDIRECT.search(text)
    if r and not SECTION.search(text):
        return front, "", r.group(1)
    sections = list(SECTION.finditer(text))
    description = ""
    for i, sec in enumerate(sections):
        if sec.group(2).lower() in DESCRIBES:
            # To the next heading of the same or a higher level: a ###
            # inside the Description is part of it.
            level = len(sec.group(1))
            end = len(text)
            for later in sections[i + 1:]:
                if len(later.group(1)) <= level:
                    end = later.start()
                    break
            description = text[sec.end():end]
            break
    return front, clean(description), None


def clean(md):
    """Wiki markdown as plain prose: no images, links flattened, bold dropped."""
    md = IMG.sub("", md)
    md = LINK.sub(r"\1", md)
    md = BOLD.sub(r"\1", md)
    md = TAG.sub("", md)
    md = TEMPLATE.sub("", md)
    md = QUOTES.sub("", md)
    md = ESCAPED.sub(r"\1", md)
    md = VERSION.sub("", md)
    md = DEFLIST.sub(" ", md)
    paragraphs = []
    for para in re.split(r"\n\s*\n", md):
        lines = [" ".join(l.split()) for l in para.splitlines() if l.strip()]
        if not lines:
            continue
        if lines[0].startswith("---") or lines[0].startswith("\u23f5") \
                or "documentation index" in lines[0]:
            continue        # the page footer, when Description is last
        if len(lines) == 1 and re.match(r"#{2,6} ", lines[0]):
            # A heading inside the description, at one level: man shows
            # a "## " paragraph as a heading.
            paragraphs.append("## " + lines[0].lstrip("#").strip())
            continue
        if LIST_ITEM.match(lines[0]):
            # A list stays a list, one item per line; a line that starts
            # with no marker is the previous item wrapped. Numbers stay
            # numbers.
            items = []
            for l in lines:
                m = LIST_ITEM.match(l)
                if m:
                    mark = m.group("mark")
                    items.append((mark if mark[0].isdigit() else "-")
                                 + " " + l[m.end():])
                elif items:
                    items[-1] += " " + l
            paragraphs.append("\n".join(items))
            continue
        joined = " ".join(lines).strip()
        if not joined or CAPTION.match(joined):
            continue        # an image's caption, with the image gone
        paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def see_also(front):
    """Page names only. The field carries templates and prose on some
    pages, and `}}` is not a page."""
    raw = TEMPLATE.sub("", (front or {}).get("SeeAlso") or "")
    return [p.strip() for p in raw.split(",")
            if re.fullmatch(r"[\w.-]+", p.strip() or " ")]


def body_for(entry, pages):
    """The seeded body, and where it came from."""
    name = entry["name"]
    page = entry.get("wiki") or name
    path = pages.get(page) or pages.get(name)
    for _hop in range(2):           # a page may redirect once
        if not path:
            break
        with open(path, encoding="utf-8") as fh:
            front, description, redirect = page_parts(fh.read())
        if redirect:
            path = pages.get(redirect)
            continue
        if description:
            body = description
            also = see_also(front)
            if also:
                body += "\n\n## See also\n\n" + "\n".join(f"- {p}" for p in also)
            return body, "wiki"
        break
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
            "wiki_rev": None,
        }
        body, source = body_for(entry, pages)
        if source == "wiki":
            generated["wiki_rev"] = rev    # provenance only where there is any
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
