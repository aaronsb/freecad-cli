---
status: Accepted
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-500
  - ADR-600
  - ADR-601
---

# ADR-100: The command dictionary

## Context

FreeCAD was never built for a command line. It has a command registry that
knows names, labels and placement, a type registry that knows properties,
and an object model where most operations are a task panel or a mode. The
factory reads both registries and produces a verb for every command and
every parametric type: 1111 launchers, 206 typed verbs, 40 families, no
command dropped. What it cannot produce is judgement — that `Mesh_PolySegm`
should not own the word `segment`, that `Sketcher_CreateCircle` needs a
sketch in edit mode, that `Std_Test1` is a test hook.

That judgement is spread over seven mechanisms today, five of them
hand-owned, no two sharing a format:

| Mechanism | Lives in | Keyed by |
|---|---|---|
| slug of label, `_by_prominence`, `_qualify_command` | `factory.py` | command |
| families (`CAMEL` split, `NOT_ACTIONS`) | `families.py` | command name shape |
| tier 1 from types, `NOISE_TYPES` | `factory.py` | type |
| `PATCH["types"]`, `PATCH["verbs"]` | `patches/*.py`, addon, user | type, declared name |
| hand-written verbs | `verbs.py` | — |
| `ZOOM_TARGETS`, `VIEW_TARGETS` | `shell.py` | word |
| alias file | XDG | word |

The 1111 tier-0 commands, the largest surface, have no hand-owned layer at
all: `patches/` is keyed by type, and a command that builds no type has
nowhere for a correction to go. "Which corner of FreeCAD is this" has four
spellings — the descriptor's `workbench` (`DraftWorkbench`),
`completion.domain_of` (`Draft`, sliced off the command name), a patch's
`key` (`Part`), and a descriptor `verbs` entry's `module` (`PartDesign`) —
and nothing reconciles them.

Four facts from the harvest thread shape the answer:

- The 148 commands that reached the descriptor without a label looked like
  a case for hand-written entries. They were a harvest bug; `getInfo()` had
  the labels all along. A hand edit that papers over a harvest gap hides
  it.
- `panels.py` reads a panel's fields live and caches nothing, because
  which fields a panel shows depends on what has been chosen in it. The
  same holds for whether a command can run: `Gui.Command.isActive()`
  changes with every selection.
- PR #14 regenerated the descriptor and read the diff by hand. That
  reading found two bugs no test and no reviewer had raised.
- The harvested `workbench` field says which workbench *loads* a command.
  `not_yet_loaded` activates that workbench, hands the operator's own
  back, and then runs the command; once loaded, a command runs from any
  workbench. What a command needs is a precondition — a document, a Body,
  a sketch in edit mode, a selection of the right kind — and the
  workbench is the GUI's proxy for it.

The first draft of this record proposed a sparse overlay: an entry only
where the factory's answer is wrong, so that a file which is 95 % copy
does not rot. The operator's direction is the opposite shape — one file
per command, all of them, externalised and organised by workbench, so the
factory becomes a maintenance tool and the command line improves by
editing the files. That direction is taken here, and the rot problem is
solved by tooling instead of sparseness.

## Decision

**One file per command.** The factory generates `lib/commands/<workbench>/
<Command>.md` for every command in the descriptor, organised by the
workbench that loads it (`std/` for the 213 that belong to none). Each
file is Markdown with YAML frontmatter. The frontmatter has two parts:

```yaml
---
command: Sketcher_CreateCircle
generated:                      # owned by the tool; rewritten on reconcile
  freecad: 1.1.3
  label: Circle From Center
  tooltip: Creates a circle from a center and rim point
  toolbar: null
  menu: Geometries
  shortcut: G, C
  workbench: SketcherWorkbench
  wiki: Sketcher_CreateCircle   # whatsThis; the page name F1 resolves
  wiki_rev: 3f1c2a9             # FreeCAD-documentation commit the body was seeded from
  seed: 9c1e0b7d2a44            # hash of the body as seeded; a body that no longer matches was written by a person
verb: null                      # authored from here down; null means "as generated"
aliases: []
requires: [sketch-edit]
panel: null
family: null
rank: null
---
Creates a circle from a centre point and a point on the rim. Both are
picked in the sketch; the radius is the distance between them.
```

The body is the documentation `man` shows, seeded from the tooltip and
thereafter written by a person against the FreeCAD wiki. Types are the
same shape: a command linked to a type carries a `type:` block with the
`steps`, `options`, `hide`, `point` and `strict` keys `PATCH["types"]`
uses today, and `patches/*.py` migrates into it. Python patches remain
for declared verbs with a custom `emit`; data lives in files, code in
Python.

**The tool owns `generated:`; a person owns the rest.** Reconcile is a
three-way merge per file, per field: base is the generation from the
committed descriptor at the file's stamp, theirs is a fresh harvest, ours
is the file. A field unchanged by the harvest is kept; a field the
harvest changed is applied to `generated:`; an authored field is never
touched. The body's base is `generated.seed`: a body that still hashes
to it is the tool's and is reseeded when the page moves; one that does
not was written by a person and is reported as a conflict when the page
moves, and left alone. A command gone from the harvest is reported and its file moved
aside, not deleted; a command new to the harvest gets a fresh file. That
is `make reconcile`, and it is what a release PR reads before `make
descriptor` commits the new stamp.

**Three roots, one layout.** `lib/commands/` ships with the addon;
`lib/addons/<name>/commands/` is what an addon ships beside its own code;
`etc/commands/` is the operator's, merged key by key over the same
relative path. ADR-601 places all three in the tree the terminal
navigates.

**Compiled, not parsed at startup.** `make dictionary` compiles the
shipped tree into `fccli/dictionary.json`, checked in beside
`descriptor.json`; the lint fails when the two disagree. At startup the
factory reads the compiled file and parses only `etc/commands/`, which is
small.

**Authored fields:**

| Field | Meaning |
|---|---|
| `verb` | the name, when the factory's is wrong: `segment` → `mesh_segment` |
| `aliases` | short spellings |
| `requires` | closed vocabulary: `document`, `body`, `sketch-edit`, `selection`, `selection:face`, … — the precondition, so a refusal can say why |
| `panel` | `pick` — do not adopt the task panel |
| `family`, `choice` | force into or out of a family, under what name |
| `rank` | `registry` — sort last regardless of placement |
| `type` | tuning for a tier-1 verb, keyed by `of` (the type): `of`, `verb`, `aliases`, `doc`, `steps`, `options`, `hide`, `point`, `prompts`, `strict`, `skip` |

**A file never holds runtime state.** Not a panel's field list, not
whether the command is currently active. `generated:` holds harvest
output because the tool rewrites it; nothing holds what changes between
selections.

**Lint runs in `make check`:**

1. Every file names a command in the descriptor and every command has a
   file, in both directions. A file whose command is gone fails.
2. `generated:` matches the descriptor field for field. A hand edit
   inside it fails, with the message that the edit belongs in an
   authored field or in `etc/`.
3. `requires` values come from the closed vocabulary; `panel` is `pick`
   or null; `rank` is `registry` or null; `family` is a name or `false`;
   `type` keys are the five named. `generated.wiki` is not checked
   against the clone: 195 of 1106 name no page (composite tool groups,
   Std internals, test hooks), and the body falls back to the tooltip.
4. After composition, every verb name is unique and every `verb` a file
   asked for is the one granted.
5. `fccli/dictionary.json` is the compilation of `lib/commands/`.

**The official documentation is the source.** `wiki` is harvested, not
authored: `Gui.Command.getInfo()` returns `whatsThis`, which is the wiki
page name FreeCAD's own F1 help resolves against, and it moves into
`generated:`. The page itself comes from
[FreeCAD/FreeCAD-documentation](https://github.com/FreeCAD/FreeCAD-documentation),
the markdown conversion of the wiki, whose `wiki/<page>.md` carries a
`GuiCommand` frontmatter (`Name`, `MenuLocation`, `Workbenches`, `SeeAlso`)
and a `## Description` section. The generator seeds each file's body from
that description, stripped of images and links, and records the page's
commit in `generated:` so a later reconcile can tell a wiki change from an
authored one. The clone lives in the tool's cache and is refreshed by
`make reconcile`; the lint checks every `wiki` value against it when the
clone is present and says so when it is not. A person editing a body
writes against the same page. FreeCAD's source
([FreeCAD/FreeCAD](https://github.com/FreeCAD/FreeCAD)) is the reference
for what a command does when the page and the tooltip disagree.

*Amended 2026-08-24, same day as acceptance: the operator directed that
the overlays stay referenced to the official documentation.*

**Precondition, not workbench.** `requires` names what a command needs;
`isActive()` reports it live; the prompt shows the context that determines
it. The `workbench` field is used for loading, for the directory a file
lives in, and for ordering completion — never for refusing.

## Consequences

### Positive

- Every command has a place a person can open, read, and improve, and the
  improvement is the project's work product from here on.
- Third-party addons ship the same shape beside their code and appear in
  the same tree.
- Rule 2 makes the generated block safe to regenerate, so a new FreeCAD
  release is a reconcile pass and a diff, not a rewrite.
- The two `shell.py` tables, `families.NOT_ACTIONS`, and `patches/*.py`
  type tuning move into files and out of code.
- Declining a pick-driven panel becomes a declared fact. A missing panel
  in the test suite becomes a named conformance failure.

### Negative

- 1111 files in the repository, most of them unedited for a long time.
  The compiled JSON is what runs; the files are what people read.
- Every FreeCAD release costs a reconcile pass, and a conflict — a field
  changed both by the harvest and by hand — needs a person.
- `requires` is a closed vocabulary that grows, and each value needs a
  live check behind it.
- Depends on PyYAML, which FreeCAD requires and the standard library does
  not provide.

### Neutral

- A `type` block in the tree wins wholesale over a Python patch
  (`patches/*.py`) for the same type: the block replaces the patch rather
  than merging field by field. An addon that ships a Python type patch for
  a type the shipped tree also tunes is overridden. Type tuning belongs in
  the tree; a Python patch is for a declared verb the factory cannot make.


- Two runtime facts stay runtime: a panel cancelled in the panel still
  reports success, and Space belongs to the command line for the whole of
  a panel verb. The dictionary describes; it never drives.
- Before the tree is generated, 238 Sketcher, Part and PartDesign
  commands need their workbench: `harvest_commands.py` snapshots
  `listCommands()` after the startup workbench has loaded them, and its
  stem repair only runs over commands already attributed. Std stays
  unattributed and lands in `std/`.
- The seven mechanisms in Context reduce to: the factory (generation),
  the tree (data), `patches/*.py` (declared verbs with code), the alias
  file.

## Test cases

- `Mesh_PolySegm`: `verb: mesh_segment`. `Draft_Split`: `verb:
  draft_split`.
- `Sketcher_CompConstrainTools` carries the label "Constrain" and takes
  the name from the 21-member family. `family: constrain, choice: tools`
  on the composite moves one name.
- `ZOOM_TARGETS` and `VIEW_TARGETS` moved: each command carries `family`/`choice` (and `also` for a spelling), the curated `zoom` family's aliases and default live in `std/_families.yaml`, and `shell.py` lost both tables and its hand-written verb.
  `Std_View*` file.
- `NOT_ACTIONS` becomes a `families.exclude` list in `lib/commands/
  std/_families.yaml`, beside the commands it speaks for.
- `Std_Test1`: `rank: registry` on a command already ranked registry by
  placement is accepted; the file records the intent even where the
  placement agrees.
- Editing `generated.label` in any file fails rule 2.

## Alternatives Considered

- **A sparse overlay recording divergence only** — the first draft. Keeps
  the hand-owned surface small and cannot rot, and gives nobody a place
  to open for the 1000 commands it does not mention. Rejected in favour
  of the tree with the tool owning the generated block, which keeps the
  anti-rot property by a different route.
- **A separate lintable file format.** A second loader and discovery for
  data the patch loader already merges by key. The tree uses one format
  for commands, types and scripts (ADR-601).
- **Parse the tree at startup.** 1111 YAML files at every FreeCAD launch
  for content that changes only on reconcile. Compiled instead.
- **Runtime heuristics per case.** `can_finish()` already declines a
  panel with no accepting button; extending that to pick-driven panels by
  widget class is a probe per panel kind, each a fact about FreeCAD
  restated as code.
- **Refuse by workbench.** Wrong in fact: a loaded command runs from any
  workbench. The refusal would fire on commands that work and miss the
  precondition that fails them.
