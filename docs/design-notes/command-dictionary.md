# The command dictionary

*2026-08-24. Design note: an approach and its constraints, recorded before
the code. Task #9 of the harvest thread; PR #14 is the evidence it cites.*

FreeCAD was never built for a command line. It has a command registry
that knows names, labels and placement, a type registry that knows
properties, and an object model where most operations are a task panel or
a mode. The factory reads the two registries and produces a verb for every
command and every parametric type, and that part is complete: 1111
launchers, 213 typed verbs, 59 families, no command dropped. What it
cannot produce is judgement — that `Mesh_PolySegm` should not own the word
`segment`, that `Sketcher_CreateCircle` needs a sketch in edit mode, that
`Std_TestQuestion` is a test hook.

The dictionary is where that judgement lives: a versioned record, for one
release of FreeCAD, of every place the command line's vocabulary departs
from what the factory would have said on its own.

## Where names get decided today

| Mechanism | Lives in | Keyed by |
|---|---|---|
| slug of label, `_by_prominence`, `_qualify_command` | `factory.py` | command |
| families (`CAMEL` split, `NOT_ACTIONS`) | `families.py` | command name shape |
| tier 1 from types, `NOISE_TYPES` | `factory.py` | type |
| `PATCH["types"]`, `PATCH["verbs"]` | `patches/*.py`, addon, user | type, declared name |
| hand-written verbs | `verbs.py` | — |
| `ZOOM_TARGETS`, `VIEW_TARGETS` | `shell.py` | word |
| alias file | XDG | word |

Five of the seven are hand-owned and no two share a format. The 1111
tier-0 commands, the largest surface, are the one tier with no hand-owned
layer at all: `patches/` is keyed by type, and a command that builds no
type — most of them — has nowhere for a correction to go.

"Which corner of FreeCAD is this" has four spellings: the descriptor's
`workbench` (`PartWorkbench`), `completion.domain_of` (`Part`, sliced off
the command name), a patch's `key` (`Part`), and a verbs entry's `module`
(`PartDesign`). Nothing reconciles them, and the prompt work in
[state.md](state.md) needs one of them to be the answer.

## Constraints

These were established in the discussion that produced this note, and the
design below is shaped by them rather than the other way round.

**It records divergence.** An entry exists only where the factory's answer
is wrong. A 1111-entry file that is 95 % identity mapping rots in two
releases, and the lint enforces this by machine (rule 2 below) rather than
by discipline.

**It never holds what changes at runtime.** `panels.py` reads a panel's
fields live and caches nothing, because which fields a panel shows depends
on what has been chosen in it. The same rule covers whether a command is
currently runnable — `Gui.Command.isActive()` answers that, and it changes
with every selection. A field list or an availability flag in the
dictionary is stale the day it is written and silently wrong after.

**Ask FreeCAD properly first.** The 148 commands that reached the
descriptor without a label looked like a case for hand-written entries.
They were a harvest bug: `Gui.Command.getInfo()` had the labels all along.
An entry that papers over a harvest gap hides the gap. Before any entry is
written, the question is whether the harvest could have known.

**Lint runs in `make check`.** "Lintable" is the least specified word in
the original proposal and does the most work. An overlay that is checked
by a script nobody runs is a text file. The check fails the build.

**One format.** `PATCH` already has two halves — `types` retunes generated
verbs, `verbs` declares ones the factory could not make. The dictionary is
the third half, `commands`, keyed by command name. The per-namespace
files, the three discovery roots, key-by-key merging and the addon
author's mental model come free, and a second file format with its own
loader would be sprawl of exactly the kind this note exists to stop.

**The reconcile is the prize.** `descriptor.json` stamps `freecad:
1.1.3`. What is missing is the diff against the next stamp. PR #14
regenerated the descriptor and read the diff by hand, and that reading
found two bugs no test and no reviewer had raised. It becomes a tool.

## Shape

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

An entry may carry:

| Field | Meaning | The divergence it records |
|---|---|---|
| `verb` | the name, when the factory's is wrong | `segment`, `split`; any contested name `_by_prominence` gets wrong |
| `doc` | one sentence, when FreeCAD's tooltip is absent or wrong against the manual | the "read the manual" investment, per command |
| `wiki` | page name on wiki.freecad.org; `man` cites it | a versionable pointer to the documentation |
| `requires` | closed vocabulary — `document`, `body`, `sketch-edit`, `selection`, `selection:face`, … | the declared precondition, so a refusal can say why |
| `panel` | `pick` — do not adopt the task panel | a panel whose substance is a viewport pick (task #2) |
| `family`, `choice` | force into or out of a family, under what name | `zoom`, `view`; the `constrain` non-finding; `NOT_ACTIONS` |
| `rank` | `registry` — sort last regardless of placement | `Std_TestQuestion` and its kin |

An entry may not carry a label, a tooltip copy, a toolbar, a menu, a
workbench, a panel's field list, or anything `isActive()` answers. The
first five are harvest output; the rest is runtime state.

## Lint

Four rules, in `make check`, over the data subset of all three halves:

1. Every key in `commands` names a command in `descriptor.json` for the
   stamped FreeCAD version. An entry for a command that disappeared fails.
2. No identity entries. A `verb` equal to what the factory produces
   unaided, a `doc` equal to the harvested tooltip, a `family`/`choice`
   equal to what `families.py` derives — each fails.
3. `requires` values come from the closed vocabulary; `wiki` matches
   `^[A-Za-z0-9_]+$`; `panel` is `pick` or absent; `rank` is `registry`
   or absent.
4. After composition, every verb name in the registry is unique and every
   `verb` the dictionary asked for is the one that was granted.

Rule 2 is the one that keeps the file sparse. It fails the moment a
harvest fix makes an entry redundant, which is the signal to delete it.

## Reconcile

`make reconcile` regenerates the descriptor into the scratch directory and
diffs it against the committed one:

- commands added, removed, relabeled, re-homed to another workbench
- verbs whose name would change, and why (label changed, collision
  appeared or cleared)
- dictionary entries that became identity (rule 2) or dangling (rule 1)
- tier-1 verbs whose parameters changed

The output is what a release PR reads before `make descriptor` commits the
new stamp. It is the diff PR #14 read by hand, as a subcommand.

## Workbench and precondition

The harvested `workbench` field says which workbench *loads* a command.
The operator's framing — certain tools must be used on certain workbenches
— is a GUI habit rather than a FreeCAD rule: `_workbench_borrowed` already
loads a workbench, runs the command from wherever the operator was, and
hands the workbench back. Once loaded, a command runs from any workbench.

What a command actually needs is a precondition: an active document, a
Body, a sketch in edit mode, a selection of the right kind. The workbench
stands in for those in the GUI because the toolbar that needs them is
nearby. `requires` names the precondition; `isActive()` reports it live;
the prompt in [state.md](state.md) shows the context that determines it.

Two harvest facts precede any of this. 455 of 1111 commands have no
workbench, and 238 of those — Sketcher, Part, PartDesign — are an artifact
of `harvest_commands.py` snapshotting `listCommands()` after the startup
workbench had already loaded them. The stem repair covers them once it
runs over unattributed commands too. Std stays unattributed, which is
true.

## Test cases

Whatever the dictionary says, it must answer these:

- **`segment` and `split`.** `Mesh_PolySegm` and `Draft_Split` hold
  generic words for workbench-specific operations. Entry: `verb:
  mesh_segment`, `verb: draft_split`. Rule 2 passes because the factory
  would have said `segment` and `split`.
- **`constrain`.** `Sketcher_CompConstrainTools` carries the label
  "Constrain", takes the name, and the 21-member family loses its door.
  Entry: `family: constrain, choice: tools` on the composite, or `rank:
  registry` on it. Either moves one name rather than thirty.
- **`ZOOM_TARGETS` and `VIEW_TARGETS`.** Two tables in `shell.py` that
  map words to `Std_View*` commands. They become `family`/`choice`
  entries on each command, and `shell.py` loses both tables.
- **`NOT_ACTIONS`.** A set of stems in `families.py` that are modules
  rather than actions. It becomes a `families.exclude` list in the `Std`
  patch, in the same file as the rest of the judgement.
- **`Std_TestQuestion`.** Promoted by placement, useless at a prompt.
  Entry: `rank: registry`.

## What it subsumes and what it leaves

| Task | Was | Becomes |
|---|---|---|
| #2 decline pick panels | runtime heuristic over widget classes | `panel: pick` entries |
| #5 Part_Offset opens no panel in the suite | a mystery | a named conformance failure `make reconcile` reports |
| #6 Sketcher edit-mode guard | measured against a real sketch | `requires: [sketch-edit]`, checked before the command runs |
| #3 panel cancelled in the panel reports success | — | untouched; runtime state |
| #4 who owns Space while a panel is open | — | untouched; runtime state |

The split is description against interaction. The dictionary describes; it
never drives.

## Order

1. Harvest attribution and descriptor slimming (task #3). Small, needed by
   both the prompt and the dictionary.
2. Context in the prompt (task #4). Verify `isActive()` on 1.1.3 first.
3. `PATCH["commands"]`, the lint, `make reconcile` (task #5). First
   entries: the two `shell.py` tables, `NOT_ACTIONS`, `segment`, `split`.
