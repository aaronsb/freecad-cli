# Changelog

<!-- next -->

## 0.2.0 -- 2026-08-23

The command language stops being hand-written.

### Added

- **Verb factory.** `tools/generate_descriptor.py` harvests FreeCAD's
  command registry and type registry and writes `fccli/descriptor.json`.
  At startup the factory turns that into ~1200 verbs across three tiers:
  every registered command as a launcher, every parametric type as a
  parameterized verb with steps, units and enum choices, and patched verbs
  on top.
- **Patch layer**, keyed by namespace and composed from three roots — this
  repo, an addon's own `fccli_patch.py`, and the user's directory. An addon
  needs no registration to be supported.
- **Shell builtins**: `save` `open` `new` `close` `quit` `clear` `undo`
  `redo` `fit` `delete` `man` `history` `alias` `unalias`. Each takes its
  arguments inline so FreeCAD's modal dialogs stay closed. A trailing `!`
  forces past a refusal.
- **`man`**, with `help` as an alias. Bare it lists; with a topic it renders
  the full page, generated from FreeCAD's own property documentation.
- **Dirty tracking** via `App.addDocumentObserver`, so unsaved-changes state
  is accurate for edits made anywhere, not just on the command line.
- **Full/partial width toggle** and a persisted dock height.

### Changed

- The dock's home is the top area: a full-width strip between the toolbars
  and the 3D view.
- Default picking backend is `snap` — Coin3D events resolved through
  `Gui.Snapper.snap()`. Snapping without Draft's Point dialog.
- A command echoes as one accumulating line, with values canonicalized on
  input: `3/8in` becomes `9.525mm`.
- History records the assembled command rather than each typed fragment, so
  a mouse-driven polyline comes back from Up as editable text.
- A verb whose remaining steps are all optional runs on Enter.

### Fixed

- `package.xml` declaring `<content><other>` stopped FreeCAD from running
  `Init.py` and `InitGui.py` at all, silently.
- A class defined in `InitGui.py` is gone by the time a deferred callback
  runs, so `Gui.addCommand` failed with *name is not defined*.
- Draft's grid rendered as stray lines across the model when the user's
  `gridSpacing` preference is `0`.
- Verb name collisions silently dropped 15 types — `PartDesign::Box` was
  overwriting `Part::Box`.
- `Registry.reindex`, so a removed alias stops resolving.

## 0.1.0 -- 2026-08-23

First cut. Six hand-written verbs, the key filter, the terminal widget.
