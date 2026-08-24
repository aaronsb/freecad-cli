---
status: Proposed
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-500
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
  the labels all along. An entry that papers over a harvest gap hides it.
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

## Decision

A command-keyed overlay, `PATCH["commands"]`, as the third half of the
existing patch format alongside `types` and `verbs`. Per-namespace files,
the three discovery roots, and key-by-key merging apply unchanged.

```python
PATCH = {
    "key": "Sketcher",
    "commands": {
        "Sketcher_CreateCircle": {
            "requires": ["sketch-edit"],
            "wiki": "Sketcher_CreateCircle",
        },
        "Mesh_PolySegm": {"verb": "mesh_segment"},
        "Std_ViewFitAll": {"family": "zoom", "choice": "all"},
    },
}
```

**An entry records divergence.** It exists only where the factory's answer
is wrong. It may carry:

| Field | Meaning | The divergence it records |
|---|---|---|
| `verb` | the name, when the factory's is wrong | `segment`, `split`; a contested name `_by_prominence` gets wrong |
| `doc` | one sentence, when FreeCAD's tooltip is absent or wrong against the manual | per-command documentation read from the wiki |
| `wiki` | page name on wiki.freecad.org; `man` cites it | a versionable pointer to the documentation |
| `requires` | closed vocabulary: `document`, `body`, `sketch-edit`, `selection`, `selection:face`, … | the declared precondition, so a refusal can say why |
| `panel` | `pick` — do not adopt the task panel | a panel whose substance is a viewport pick |
| `family`, `choice` | force into or out of a family, under what name | `zoom`, `view`; the `constrain` composite; `NOT_ACTIONS` |
| `rank` | `registry` — sort last regardless of placement | a promoted command that is useless at a prompt |

**An entry never holds runtime state.** Not a label, a tooltip copy, a
toolbar, a menu, a workbench, a panel's field list, or anything
`isActive()` answers. The first five are harvest output; the rest is
stale the day it is written.

**Lint runs in `make check`**, over the data subset of all three halves:

1. Every key in `commands` names a command in `descriptor.json` for the
   stamped FreeCAD version.
2. No identity entries. A `verb` equal to what the factory produces
   unaided, a `doc` equal to the harvested tooltip, a `family`/`choice`
   equal to what `families.py` derives, a `rank` equal to the placement
   rank — each fails.
3. `requires` values come from the closed vocabulary; `wiki` matches
   `^[A-Za-z0-9_]+$`; `panel` is `pick` or absent; `rank` is `registry`
   or absent.
4. After composition, every verb name is unique and every `verb` the
   dictionary asked for is the one granted.

**`make reconcile`** regenerates the descriptor into the scratch directory
and diffs it against the committed one: commands added, removed,
relabeled, re-homed; verbs whose name would change and why; entries gone
identity or dangling; tier-1 verbs whose parameters changed. It is what a
release PR reads before `make descriptor` commits the new stamp.

**Precondition, not workbench.** `requires` names what a command needs;
`isActive()` reports it live; the prompt shows the context that determines
it. The descriptor's `workbench` field is used for loading and for
ordering completion, never for refusing.

## Consequences

### Positive

- Tier 0 gets the hand-owned layer it lacked, in the format the other two
  tiers already use.
- Rule 2 keeps the file sparse by machine. A harvest fix that makes an
  entry redundant fails the build until the entry is deleted.
- The two `shell.py` tables and `families.NOT_ACTIONS` move into the
  overlay and out of code.
- Declining a pick-driven panel becomes a declared fact rather than a
  widget-class heuristic. A missing panel in the test suite becomes a
  named conformance failure `make reconcile` reports.
- The descriptor diff PR #14 read by hand is a subcommand.

### Negative

- Every FreeCAD release costs a reconcile pass before the descriptor is
  re-stamped.
- `requires` is a closed vocabulary that will grow, and each new value
  needs a live check behind it.

### Neutral

- Two runtime facts stay runtime: a panel cancelled in the panel still
  reports success, and Space belongs to the command line for the whole of
  a panel verb. The dictionary describes; it never drives.
- Before the overlay is useful, 238 Sketcher, Part and PartDesign commands
  need their workbench: `harvest_commands.py` snapshots `listCommands()`
  after the startup workbench has loaded them, and its stem repair only
  runs over commands already attributed. Std stays unattributed.

## Test cases

- `Mesh_PolySegm` → `verb: mesh_segment`; `Draft_Split` → `verb:
  draft_split`. Rule 2 passes because the factory would have said
  `segment` and `split`.
- `Sketcher_CompConstrainTools` carries the label "Constrain", takes the
  name, and the 21-member family loses its door. `family: constrain,
  choice: tools` on the composite moves one name.
- `ZOOM_TARGETS` and `VIEW_TARGETS` become `family`/`choice` entries on
  each `Std_View*` command.
- `NOT_ACTIONS` becomes a `families.exclude` list in the `Std` patch.
- `Std_Test1`: registered, no toolbar or menu, already ranked `registry`.
  An entry `rank: registry` for it must fail rule 2.

## Alternatives Considered

- **A separate lintable file.** A second format with its own loader and
  discovery, for data the patch loader already merges by key.
- **A complete dictionary, one entry per command.** 1111 entries that are
  95 % identity mapping rot within two releases and hide the entries that
  matter.
- **Runtime heuristics per case.** `can_finish()` already declines a panel
  with no accepting button; extending that to pick-driven panels by widget
  class is a probe per panel kind, and each probe is a fact about FreeCAD
  restated as code.
- **Refuse by workbench.** Wrong in fact: a loaded command runs from any
  workbench. The refusal would fire on commands that work and miss the
  precondition that fails them.
