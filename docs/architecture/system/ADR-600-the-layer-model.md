---
status: Proposed
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-100
  - ADR-500
  - ADR-601
---

# ADR-600: The layer model

## Context

The command line translates between FreeCAD's object model — commands,
typed properties, task panels, modes — and a line of text. The code has
grown seams that the ADR domains (ADR-500) follow, and the operator's own
account of the architecture names seven layers. The two agree, and the
model needs writing down so a change can be placed before it is made.

## Decision

| Layer | Role | Code | Domain |
|---|---|---|---|
| 0. FreeCAD | The host: registries, documents, task panels, the Qt main window, preferences | — | host |
| 1. Command factory | Harvest FreeCAD's registries into the descriptor; generate a verb for every command and every parametric type; derive families from the names | `tools/harvest_*.py`, `generate_descriptor.py`, `factory.py`, `families.py` | vocabulary |
| 2. Plugin factory | The same, for commands an addon registers. Today this holds only for addons present when the descriptor was harvested; a command in `Gui.listCommands()` and absent from the descriptor gets no verb | `factory.py` (gap), `patches/__init__.py` addon root | vocabulary |
| 3. Overlays | The hand-owned layer: one file per command (ADR-100), type tuning, declared verbs, aliases, scripts in `/bin` (ADR-601) | `lib/commands/`, `etc/`, `patches/`, `verbs.py` | vocabulary |
| 3a. Shell builtins | Verbs FreeCAD does not have: `save`, `open`, `undo`, `man`, `use`, `alias`, `history`, `describe`, `check`, `cd`, `ls` | `shell.py` | surface |
| 4. Intercept and normalisation | Parsing, units, points, step routing, panel adoption, modal interception, key usurping, transactions | `engine.py`, `parsing.py`, `units.py`, `panels.py`, `modals.py`, `keyfilter.py`, `picking.py` | engine |
| 4a. Session | State that belongs to neither the engine nor a terminal: documents, the floor and shared buffer, scope, the history ring, cwd | `session.py` | surface |
| — Bus | The seam between 4 and 5: a typed message stream, the only thing a terminal reads | `bus.py` | surface |
| 5a. In-application terminal | Dock, widget, highlighting, completion | `dock.py`, `widget.py`, `highlight.py`, `completion.py` | surface |
| 5b. Socket terminal | Server, `bin/fccli` | `server.py`, `bin/fccli` | surface |

Layer 0 is touched at 1 (harvest), 4 (`runCommand`, panels, selection,
undo) and 5a (a Qt dock inside FreeCAD's window). Nothing else reaches it.

**The reverse direction.** Every layer above carries text toward
FreeCAD. Five pieces carry FreeCAD toward text, and history replay exists
because they do:

| Reverse translator | What it does | Code |
|---|---|---|
| toolbar bridge | a click becomes a command line — `echo`, `ghost`, `follow` | `actions.py` |
| picker | a viewport click becomes a typed point in the replay | `picking.py`, `Engine.typed_prefix` |
| `describe` | an object becomes text a screen reader or an agent can read | `describe.py` |
| `RESULT`, `LIVE` | what ran, as the line that would run it again | `engine.py` |
| `shortcuts` | FreeCAD's key chords become aliases | `shortcuts.py` |

Curation — rank and adjacency read from FreeCAD's toolbars and menus —
cuts across layers 1 and 3: the host telling the vocabulary what matters.
It stays in `curation.py` and is not a layer.

**Two axes.** The table is the runtime stack. The factory's other life —
harvest, generate, edit, reconcile, release — is a sequence in time, and
layers 1 and 3 are the same files seen at different moments of it.
ADR-100 records that axis.

Rules the model implies:

- A layer reads from the one below it and never reaches past it. Layer 4
  sees verbs, not files; layer 5 sees the bus and the session, not the
  engine's fields.
- Layer 2 must become true. At startup, a command present in
  `Gui.listCommands()` and absent from the descriptor gets a tier-0 verb
  with its label from `getInfo()`, and `make reconcile` (ADR-100) reports
  it as a command the descriptor does not know.
- Layer 3 is where the work is. Layers 1, 2, 4 and 5 are machinery that
  should change rarely; the command line improves by editing layer 3.
- A reverse translator produces a line the forward direction accepts.
  Anything it emits that would not replay is a bug.

## Consequences

### Positive

- A change has a place before it has a diff, and the place names its
  domain and its ADR series.
- The shell's own vocabulary is distinguished from FreeCAD's, which the
  coreutils analogy needs.

### Negative

- Layer 2 is recorded as a gap, and stays one until the runtime
  registration lands.

### Neutral

- Layer 3 absorbs what were seven mechanisms in `factory.py`,
  `families.py`, `shell.py` and `patches/`; ADR-100 says how.

## Alternatives Considered

- **Five layers as first stated**, without the builtins row. The analogy
  to coreutils breaks: `man` and `cd` are not translations of anything
  FreeCAD has.
- **A one-directional stack.** Leaves out the bridge, the picker and
  `describe`, and with them the reason a mouse-driven command replays
  from history as text.
- **Curation as a layer.** It produces no verbs and owns no files; it
  orders what layer 3 produced.
