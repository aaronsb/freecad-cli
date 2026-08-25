---
name: command-tree
description: Edit a command's file in fccli/lib/commands — rename a verb, write its doc, declare a precondition, group it into a family, tune its type — then compile and lint. Use when adding or changing a command's name, aliases, requires, panel, family/choice, rank, type block, or manual, or when a new FreeCAD release needs reconciling. Triggers on "rename this command", "add an alias", "this command needs a sketch", "group these into a family", "tune the steps", "make reconcile", "the command tree".
---

# Working the command tree

Every FreeCAD command has a file: `fccli/lib/commands/<workbench>/<Command>.md`.
The command line's vocabulary is edited here, not in code. ADR-100 is the why.

## The file

Markdown, YAML frontmatter, two halves:

```yaml
---
command: "Sketcher_CreateCircle"
generated:                     # the tool's — harvest output, never hand-edited
  freecad: "1.1.3"
  label: "Circle From Center"
  tooltip: "Creates a circle from a center and rim point"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_CreateCircle"
  seed: "…"                    # hash of the body as seeded
# authored from here down — yours
verb: null                     # the name, when the factory's is wrong
aliases: []
requires: []                   # a precondition, so a refusal can say why
panel: null                    # `pick` — do not adopt the task panel
family: null                   # a family to join; false keeps it out of any
choice: null
also: []                       # other spellings of the choice
rank: null                     # `registry` — sort last regardless of placement
type: null                     # tuning for the tier-1 verb built from a type
---
The body man shows, seeded from the FreeCAD wiki.
```

**Never edit the `generated:` block.** The lint fails on it; a change there
belongs in an authored field or is a harvest fix.

## Authored fields

| Field | Use |
|---|---|
| `verb` | rename the verb when the slugged label is wrong (`Mesh_PolySegm` → `mesh_segment`) |
| `aliases` | short spellings; one already in use is dropped and said |
| `requires` | closed vocabulary: `document`, `body`, `sketch-edit`, `selection`, `selection:face`, … — the prompt refuses with this before running |
| `panel` | `pick` on a panel whose real input is a viewport pick |
| `family` / `choice` / `also` | fold a spread-apart group into one verb with a choice; `also` gives one command an alternate spelling |
| `rank` | `registry` demotes a promoted-but-useless command |
| `type` | `{of: <Type>, verb, aliases, doc, steps, options, hide, point, prompts, strict, skip}` — tunes the tier-1 verb built from `of` |

A **curated family** (its own aliases and default, like `zoom`) is declared
in `<workbench>/_families.yaml` under `verbs:`; the members carry
`family`/`choice` in their files. A **type with no command** (Part::Wedge)
is tuned in `<workbench>/_types.yaml`, keyed by type.

## The loop

1. Edit the file(s).
2. `make dictionary` — compile the tree into `fccli/dictionary.json`.
3. `make lint` — the five rules: every file names a real command and every
   command has a file; the generated block matches the descriptor; authored
   fields are well-formed; verbs and family choices are unique; the compiled
   file is current.
4. `make test` — the offscreen suite reads the shipped dictionary.

A lint error names the file, the field and the rule. Rule 2 firing means a
hand edit landed in the generated block; move it to an authored field.

## An entry earns its place

Every command has a file; that is not the same as every command needing an
authored field. An authored field that only restates the harvest — a `verb`
equal to the slugged label, a `doc` equal to the tooltip — is noise. If a
harvest fix would make your entry redundant, fix the harvest instead. The
148 "unlabeled" commands were a harvest bug, not a case for 148 hand-written
entries. Ask FreeCAD properly first. (This is discipline, not a lint rule —
the lint checks shape and consistency, not whether an entry adds anything.)

## Reconciling a new FreeCAD

When FreeCAD updates or an addon changes what it registers:

```
make reconcile              # report: added, removed, re-homed, relabelled,
                            # bodies whose wiki page moved, entries gone stale
make reconcile FLAGS=--apply  # bring tree + descriptor + dictionary to it
```

Read the report before applying. A body a person wrote whose wiki page also
moved is a **conflict** — reported, left alone. Everything else the tool
merges field by field; authored fields are never touched.

## Verify like the rest of the repo

Falsify a new lint rule by planting its fault and confirming it fires. When
you change what a file produces, measure it against a run with no dictionary
(`register_all(..., dictionary={})`) so the check is the difference the tree
makes.
