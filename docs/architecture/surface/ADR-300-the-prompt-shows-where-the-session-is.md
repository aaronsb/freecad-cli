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

A shell prompt shows the path, the branch and the dirty flag because the
next command depends on them. FreeCAD's equivalents are the workbench,
the active Body or Part, the sketch in edit, whether the document is
dirty, and what is selected. Today the prompt shows the engine's step
and, since ADR-601, the working directory; the FreeCAD side is visible
only in the GUI.

That side decides what a command does. `Sketcher_CreateCircle` needs a
sketch in edit mode; in the GUI the Sketcher toolbar stands nearby as a
reminder, and on the command line the operator has to remember. The
prompt is where that reminder belongs.

Three pieces already exist. `bus.STATE` has been declared since the bus
existed and is free for this use (`docs/state.md`).
`MainWindow.workbenchActivated` is connected (ADR-600, layer 2).
`Gui.Command.isActive()` answers, live, whether a command can run now —
the same answer FreeCAD greys a button with — and ADR-100 keeps that
answer live rather than written down.

Both terminals show the same prompt from the same source: `bin/fccli`
already renders its prompt from the session's `state()`.

## Decision

**One message carries the context.** The engine emits `STATE` with the
session's context whenever it changes and after every command:

| Field | Source | Shown as |
|---|---|---|
| `workbench` | `Gui.activeWorkbench().name()`, `Workbench`/`WB` suffix dropped | `PartDesign` |
| `active` | the active Body or Part, then the object in edit (`Gui.ActiveDocument.getInEdit()`) | `Body › Sketch` |
| `dirty` | `App.ActiveDocument.Modified` | `*` after the document chain |
| `selection` | `Gui.Selection.getSelection()` count, when non-zero | `[3]` |
| `cwd` | the session (ADR-601) | `/plinth` |

It is emitted on `workbenchActivated`, on document change through the
observer `dirty.py` installs, on selection change through
`Gui.Selection.addObserver`, and from `_announce` when the engine returns
to idle.

**Both terminals render it from one function.** `fccli/prompt.py` turns
the message into the segment; the dock prepends it to the idle prompt,
and `bin/fccli._prompt_for` does the same from `state()`, which gains the
same fields.

```
PartDesign Body › Sketch* [2] /plinth > 
```

A field that is empty is left out. At `/` with a clean document, nothing
active and the default workbench, the prompt is `> ` as it is today.

**Context orders completion.** `curation.order` sorts a verb whose
command's `workbench` matches the active one ahead within its rank.
Every verb stays offered; `use` remains the one way to narrow.

**A command that cannot run here says so first.** When a verb runs a
command and `Gui.Command.get(name).isActive()` is false, the engine
reports the reason from the command file's `requires` (ADR-100) — "needs
a sketch in edit mode" — or "is not available here" when the file gives
none, and stops. `isActive()` is read at that moment. A trailing `!` runs
the command anyway.

## Consequences

### Positive

- The prompt answers what the GUI answers with a toolbar: where am I,
  and what will a command act on.
- One message, one renderer, two terminals in agreement.
- `requires` in the command tree becomes visible as the reason in a
  refusal.
- `STATE` gains its meaning.

### Negative

- A selection observer fires on every click. The emit is cheap; it is
  one more thing on the click path.
- The prompt grows. Empty fields are left out, and the dock colours the
  segment apart from the step's prompt.

### Neutral

- `panel` from the command tree stays for a separate change: declining a
  pick-driven panel.
- `docs/state.md` gains the message and its triggers.

## Alternatives Considered

- **A status-strip field.** The dock has a strip; the socket terminal has
  a prompt only. The prompt is what both have.
- **Context as scope.** Narrowing Tab to the active workbench would hide
  the thousand launchers by default; `use` leaves that to the operator.
- **Refuse by workbench.** A loaded command runs from any workbench
  (ADR-100); `isActive()` is the fact the refusal should rest on.
- **Store `requires` verdicts.** Runtime state, kept live by ADR-100.
