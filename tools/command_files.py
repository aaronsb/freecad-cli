# SPDX-License-Identifier: LGPL-2.1-or-later
"""One file per command: the shape, read and written.

ADR-100. A command file is Markdown with YAML frontmatter. The frontmatter
has a `generated:` block the tool owns and rewrites, and authored fields a
person owns and the tool never touches. The body is the documentation
`man` shows, seeded from the FreeCAD wiki and written by a person after.

Shared by generate_commands.py (writes), compile_dictionary.py (reads) and
lint_dictionary.py (checks), so the three agree on what a file is.
"""

import json
import os
import re

import yaml

# generated: fields, in the order they are written. Every one is harvest
# output the reconcile may rewrite.
GENERATED = ("freecad", "label", "tooltip", "toolbar", "menu", "shortcut",
             "workbench", "wiki", "wiki_rev")

# Authored fields, their defaults, and what the lint accepts.
AUTHORED = {
    "verb": None,
    "aliases": [],
    "requires": [],
    "panel": None,
    "family": None,
    "choice": None,
    "rank": None,
    "type": None,
}
REQUIRES = {"document", "body", "sketch-edit", "selection", "selection:face",
            "selection:edge", "selection:vertex", "selection:solid",
            "selection:sketch", "selection:mesh"}
PANEL = {None, "pick"}
RANK = {None, "registry"}
TYPE_KEYS = {"steps", "options", "hide", "point", "strict"}

FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def workbench_dir(workbench):
    """sketcherworkbench -> sketcher; None -> std."""
    if not workbench:
        return "std"
    name = workbench.lower()
    for suffix in ("workbench", "wb"):
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
    return name


def path_for(root, command, workbench):
    return os.path.join(root, workbench_dir(workbench), command + ".md")


def _scalar(value):
    """A YAML scalar, written the JSON way so nothing needs quoting rules."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def render(command, generated, authored, body):
    """The file text. Comments survive because this is a template, not a dump."""
    lines = ["---", f"command: {_scalar(command)}",
             "generated:                     # owned by the tool; rewritten on reconcile"]
    for key in GENERATED:
        lines.append(f"  {key}: {_scalar(generated.get(key))}")
    lines.append("# authored from here down; the tool never rewrites these")
    for key, default in AUTHORED.items():
        value = authored.get(key, default)
        if isinstance(value, (list, dict)) and value:
            dumped = yaml.safe_dump(value, sort_keys=False,
                                    allow_unicode=True).rstrip("\n")
            lines.append(f"{key}:")
            lines.extend("  " + row for row in dumped.split("\n"))
        elif isinstance(value, list):
            lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {_scalar(value)}")
    lines.append("---")
    text = "\n".join(lines) + "\n"
    if body:
        text += "\n" + body.rstrip("\n") + "\n"
    return text


def parse(text):
    """(frontmatter dict, body) from a file's text. Raises on a bad file."""
    m = FRONT.match(text)
    if not m:
        raise ValueError("no frontmatter")
    front = yaml.safe_load(m.group(1)) or {}
    if not isinstance(front, dict):
        raise ValueError("frontmatter is not a mapping")
    return front, text[m.end():].lstrip("\n")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return parse(fh.read())


def walk(root):
    """Every command file under root: (relative path, absolute path)."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith(".md") and not f.startswith("_"):
                full = os.path.join(dirpath, f)
                out.append((os.path.relpath(full, root), full))
    return sorted(out)


def authored_of(front):
    """The authored fields of a parsed frontmatter, defaults filled in."""
    return {k: front.get(k, d) if front.get(k) is not None else d
            for k, d in AUTHORED.items()}
