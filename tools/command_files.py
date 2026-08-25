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
             "workbench", "wiki", "wiki_rev", "seed")

# Authored fields, their defaults, and what the lint accepts.
AUTHORED = {
    "verb": None,
    "summary": None,    # the one-liner for a launcher verb, over FreeCAD's tooltip
    "example": None,    # the canonical invocation: shown in man, driven by verify (ADR-501)
    "aliases": [],
    "requires": [],
    "panel": None,
    "family": None,     # a name joins that family; false keeps it out of any
    "choice": None,
    "also": [],         # other spellings of this choice (zoom extents = all)
    "rank": None,
    "type": None,
}
REQUIRES = {"document", "body", "sketch-edit", "selection", "selection:face",
            "selection:edge", "selection:vertex", "selection:solid",
            "selection:sketch", "selection:mesh"}
PANEL = {None, "pick"}
RANK = {None, "registry"}
# A command file's type block: tuning for the tier-1 verb built from
# `of` (ADR-100 option A). The same spec patches.apply reads, plus `of`.
TYPE_KEYS = {"of", "verb", "aliases", "doc", "steps", "options", "hide",
             "point", "prompts", "strict", "skip"}

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
    text = json.dumps(value, ensure_ascii=False)
    # JSON leaves C1 controls and the two non-characters raw; YAML refuses
    # them. Escape what json.dumps did not.
    return re.sub(r"[\x7f-\x9f\ufffe\uffff]",
                  lambda m: "\\u%04x" % ord(m.group()), text)


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


def seed_of(body):
    """What the tool seeded a body as, so reconcile can tell a body a
    person wrote from one the wiki moved under."""
    import hashlib
    return hashlib.sha1((body or "").strip().encode("utf-8")).hexdigest()[:12]


def edited(front, body):
    """Whether a person has written in this body.

    A body that still hashes to its seed is the tool's. A file with no
    seed predates the seed and is taken as the tool's too, so the first
    reconcile after the field appeared stamps it rather than reporting
    a thousand conflicts.
    """
    seed = (front.get("generated") or {}).get("seed")
    return bool(seed) and seed_of(body) != seed


def walk(root):
    """Every command file under root: (relative path, absolute path).

    A name starting with _ is not a command file: _families.yaml beside
    the std commands, and _retired/ where reconcile parks the files of
    commands FreeCAD no longer has.
    """
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("_"))
        for f in sorted(files):
            if f.endswith(".md") and not f.startswith("_"):
                full = os.path.join(dirpath, f)
                out.append((os.path.relpath(full, root), full))
    return sorted(out)


def authored_of(front):
    """The authored fields of a parsed frontmatter, defaults filled in.
    `family: false` is a value -- it keeps the command out of any family
    -- so only None falls to the default."""
    return {k: front.get(k) if front.get(k) is not None else d
            for k, d in AUTHORED.items()}
