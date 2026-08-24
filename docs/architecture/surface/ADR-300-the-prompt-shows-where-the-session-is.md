---
status: Proposed
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-100
  - ADR-600
  - ADR-601
---

# ADR-300: The prompt shows where the session is

## Context

The prompt shows the engine's step and, since ADR-601, the working
directory. It shows nothing of FreeCAD: not the workbench, not the Body
or the sketch in edit, not whether the document is dirty, not what is
selected. Yet those decide what a command does next. `Sketcher_CreateCircle`
fails on the Part workbench because no sketch is open, and would fail on
the Sketcher workbench for the same reason; the workbench is the GUI's
proxy for the precondition, and the command line has no proxy at all.

A shell prompt that shows the branch and the dirty flag is the model.
Both terminals must show the same thing, from the same source, the way
`bin/fccli` already renders its prompt from the session's `state()`.

`bus.STATE` has been declared since the bus existed and never emitted
(`docs/state.md`). `MainWindow.workbenchActivated` is already connected
(ADR-600, layer 2). `Gui.Command.isActive()` reports whether a command can
run now, and changes with every selection; ADR-100 rules that such a fact
is never written down.

## Decision

**One message.** The engine emits `STATE` — the declared, never-used kind
— with the session's context whenever it changes and after every command:

| Field | Source | Shown as |
|---|---|---|
| `workbench` | `Gui.activeWorkbench().name()`, `Workbench`/`WB` suffix dropped | `PartDesign` |
| `active` | the active Body or Part, then the object in edit (`Gui.ActiveDocument.getInEdit()`) | `Body › Sketch` |
| `dirty` | `App.ActiveDocument.Modified` | `*` after the document chain |
| `selection` | `Gui.Selection.getSelection()` count, when non-zero | `[3]` |
| `cwd` | the session (ADR-601) | `/plinth` |

Emitted on `workbenchActivated`, on document change (the observer
`dirty.py` already installs), on selection change (`Gui.Selection.addObserver`),
and from `_announce` when the engine returns to idle.

**Both terminals render it, neither computes it.** The dock prepends the
segment to the idle prompt; `bin/fccli._prompt_for` does the same from
`state()`, which gains the same fields. The rendering is one function in
`fccli/prompt.py`, used by both:

```
PartDesign Body › Sketch* [2] /plinth > 
```

Empty fields are omitted; at `/` with nothing active on a clean document
in the default workbench, the prompt is `> ` as it is today.

**Context orders completion; it never narrows it.** `curation.order`
sorts a verb whose command's `workbench` matches the active one ahead
within its rank. `use` keeps its contract as the one way to narrow.

**A refusal says why, before running.** When the verb runs a command and
`Gui.Command.get(name).isActive()` is false, the engine reports the
command file's `requires` (ADR-100) if it has one — "needs a sketch in
edit mode" — and "is not available here" otherwise, and does not run it.
`isActive()` is read at that moment and never stored. A trailing `!` runs
it anyway.

## Consequences

### Positive

- The prompt answers the question the GUI answers with a toolbar: where
  am I, and what will a command act on.
- One message, one renderer, two terminals showing the same thing.
- `requires` in the command tree becomes visible: a refusal with a reason.
- `STATE` finally means something.

### Negative

- A selection observer fires on every click; the emit is cheap, but it is
  one more thing on the click path.
- A long prompt. The segment is omitted where empty, and the dock's prompt
  colour separates it from the step's prompt.

### Neutral

- `panel` from the command tree is not acted on here; declining a
  pick-driven panel is a separate change.
- `docs/state.md` gains the message and its triggers.

## Alternatives Considered

- **A status strip field instead of the prompt.** The dock has a strip;
  the socket terminal has no strip, only a prompt. The prompt is what both
  have.
- **Context as scope.** Narrowing Tab to the active workbench would hide
  the 1000 launchers by default, which `use` deliberately leaves to the
  operator.
- **Refuse by workbench.** Wrong in fact (ADR-100): a loaded command runs
  from any workbench. `isActive()` is what FreeCAD itself greys a button
  with.
- **Store `requires` verdicts.** Runtime state, ruled out by ADR-100.
