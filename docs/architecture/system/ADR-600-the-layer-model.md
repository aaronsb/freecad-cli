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
| 1. Command factory | Harvest FreeCAD's registries into the descriptor; generate a verb for every command and every parametric type; derive families from the names | `tools/harvest_*.py`, `generate_descriptor.py`, `factory.py`, `families.py` | vocabulary |
| 2. Plugin factory | The same, for commands an addon registers. Today this holds only for addons present when the descriptor was harvested; a command in `Gui.listCommands()` and absent from the descriptor gets no verb | `factory.py` (gap), `patches/__init__.py` addon root | vocabulary |
| 3. Overlays | The hand-owned layer: one file per command (ADR-100), type tuning, declared verbs, aliases, scripts in `/bin` (ADR-601) | `lib/commands/`, `etc/`, `patches/`, `verbs.py` | vocabulary |
| 3a. Shell builtins | Verbs FreeCAD does not have: `save`, `open`, `undo`, `man`, `use`, `alias`, `history`, `describe`, `check`, `cd`, `ls` | `shell.py` | surface |
| 4. Intercept and normalisation | Parsing, units, points, step routing, panel adoption, modal interception, key usurping, transactions | `engine.py`, `parsing.py`, `units.py`, `panels.py`, `modals.py`, `keyfilter.py`, `picking.py` | engine |
| 5a. In-application terminal | Dock, widget, highlighting, completion | `dock.py`, `widget.py`, `highlight.py`, `completion.py` | surface |
| 5b. Socket terminal | Server, floor, `bin/fccli` | `server.py`, `session.py`, `bin/fccli` | surface |

Curation — rank and adjacency read from FreeCAD's toolbars and menus —
cuts across layers 1 and 3: the host telling the vocabulary what matters.
It stays in `curation.py` and is not a layer.

Rules the model implies:

- A layer reads from the one below it and never reaches past it. Layer 4
  sees verbs, not files; layer 5 sees the bus, not the engine's fields.
- Layer 2 must become true. At startup, a command present in
  `Gui.listCommands()` and absent from the descriptor gets a tier-0 verb
  with its label from `getInfo()`, and `make reconcile` (ADR-100) reports
  it as a command the descriptor does not know.
- Layer 3 is where the work is. Layers 1, 2, 4 and 5 are machinery that
  should change rarely; the command line improves by editing layer 3.

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
- **Curation as a layer.** It produces no verbs and owns no files; it
  orders what layer 3 produced.
