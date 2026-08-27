---
status: Accepted
date: 2026-08-25
deciders:
  - aaronsb
  - claude
related:
  - ADR-203
  - ADR-501
---

# ADR-200: A select verb sets the selection commands consume

## Context

Most FreeCAD commands act on a selection. You select a sketch, then pad it;
select edges, then fillet them; select two solids, then cut one from the
other. The command reads `Gui.Selection` and works on whatever is there.

The command line can read that selection but not set it. `context.selected()`
and `engine.current_selection()` call `Gui.Selection.getSelection()`; nothing
calls `addSelection`. So a selection command has no way in from the command
line. `pad 10` with nothing selected is refused, the same as `part_cut` was.

A workflow classified the 30 parameter-bearing Part and PartDesign commands:
26 are selection commands, 4 open panels, none is positional. The pattern
holds across the set — Sketcher's 135 commands work inside an open sketch,
the booleans act on selected solids, the transforms on selected features.
The command line reaches a handful of positional primitives and stops at the
mouse for the rest.

FreeCAD already answers labels to objects here: `engine._resolve_names` turns
the text at a selection step into objects, and `delete`, `move` and
`describe` share it. What is missing is a verb that writes the selection
those objects make.

## Decision

Add a hand-written `select` verb that sets the FreeCAD selection.

**Syntax.**

    select <name>[, <name> ...]      select whole objects by label or name
    select <name>.<subelement>       select a subelement: Box.Edge1, Pad.Face2
    select                           bare: clear the selection

Names resolve through `engine._resolve_names`, so `select` answers the same
labels the selection steps of `delete` and `move` already do. A subelement is
the object, a dot, and FreeCAD's own subelement name.

**Semantics.** `select` replaces the selection with what it names. `select A,
B` selects exactly A and B; a following `select C` leaves only C. Bare
`select` selects nothing, which clears it. Building a multi-object selection
is one command with several names, not several commands.

**What it writes.** `select` calls `Gui.Selection.clearSelection` then
`addSelection` for each name, into the same `Gui.Selection` the mouse writes
and every command reads. Nothing changes on the consumer side: a selection
command run next finds its operands the way it always has.

**What it claims, it holds.** `addSelection` answers nothing, and FreeCAD
does not always take what it is handed: a *selection gate* — what Part's
vertex, edge and face filters leave on, and it outlives the document it was
set in — drops every selection made through it and says so to nobody. So
`select` reads the selection back, and a name FreeCAD did not take is a
fault naming the gate and `no_selection_filters`, which lifts it. It is
ADR-203's rule one surface over: a selection the line accepted reaches
FreeCAD, or the line says it did not.

A success over an empty selection is worse than a refusal, because the
command *after* it inherits the failure. `select Line, Line001, Line002,
Line003` then `upgrade` exited 0 and built nothing, and it was `upgrade`
that got the blame (GH #73). Nothing half-selected is left behind either:
a fault clears the selection, so the next command finds nothing rather than
some of what was asked for.

The gate itself is left alone. It is FreeCAD's state, set by a FreeCAD
command somebody ran on purpose, and clearing it on a document close would
be the command line deciding how FreeCAD should be set up — the rule
`docs/conventions.md` holds for preferences. FreeCAD exposes
`addSelectionGate` and `removeSelectionGate` and no way to ask whether one
is on, so `state` cannot report it without making and undoing a selection
to find out. The refusal carries the news instead, at the moment it matters.

**Completion.** `select` at a name position completes document object labels,
from the source that already lists them. Subelement completion is left for
later.

**Preconditions.** `select` requires an active document, and the GUI's
selection service — it is unavailable under `freecadcmd`, which has no
`Gui.Selection`. A named object or subelement that does not exist is a fault
with the name in the reason.

## Consequences

### Positive

- Selection commands become reachable from the command line. `select
  Sketch` then `pad 10`, `select Box, Cyl` then `part_cut` — the modelling
  verbs a person actually reaches for, driven as text.
- The verify harness gains its selection tier (ADR-501). A fixture selects
  its geometry with `select`, then runs the verb, so the 26 selection
  commands the workflow drafted become verifiable, not just documented.
- The drafted examples become runnable. A selection command's example is
  `select <what>; <verb> <params>`, and it verifies as one line of setup and
  one of command.

### Negative

- A read-back costs one `isSelected` per name, and it trusts FreeCAD's
  answer. FreeCAD that cannot answer is read as yes: a missing answer is
  not evidence of a fault, and inventing one would refuse work that runs.
- Subelement names — Edge1, Face2 — are opaque and shift as a shape is
  rebuilt. A person has to learn or discover them; `describe` listing an
  object's edges and faces would answer that, and is the natural companion.
- Selection is GUI state, so `select` needs the GUI. A pure `freecadcmd`
  session cannot use it. The command line already runs against a GUI
  instance, so this bounds the harness, not daily use.

### Neutral

- Replace-only is the v1 semantics. Adding to or toggling a selection —
  `select +A`, `select -A` — is a later extension on the same verb.
- `select` is the standalone counterpart of a command's selection step. The
  step picks operands during a command; `select` sets them before one, which
  is the command line's form of clicking objects and then pressing a tool.

## Alternatives Considered

- **No verb; keep selection on the mouse.** The command line reads selection
  and a person sets it by clicking. Rejected: it leaves the selection
  population — most of the command set — mouse-only, and a command line that
  cannot model without the mouse is not a command line for modelling.
- **A selection argument on each command,** e.g. `pad Sketch 10`. Rejected:
  every selection command would grow bespoke selection arguments, and a
  command that takes several operands (loft's sections, a boolean's solids)
  fits a positional slot badly. FreeCAD's model is select-then-act; one
  `select` verb serves every command that follows it.
- **Fixture selection in the harness only,** set through a script, with no
  user verb. Rejected: it verifies the commands but leaves them undrivable
  for a person. A verb solves the usability gap and the verification gap at
  once.
