# Changelog

<!-- next -->

## 0.3.0 -- 2026-08-23

The command line reads FreeCAD's own opinion about itself, and then yours.

### Changed

- **License is now LGPL-2.1-or-later**, replacing MIT -- the same license
  FreeCAD is under. Code can move between this addon and FreeCAD in either
  direction with no relicensing step, and a fork that modifies these files
  has to publish the modifications.
- **SPDX headers** on every source file, matching FreeCAD's own convention.
- **Completion offers verbs in rank order.** Nothing is hidden -- a verb
  FreeCAD never surfaces still completes, it just sorts after the ones it
  gives a toolbar button.
- **`Bezier Curve` slugs to `bezier_curve`.** Accents folded to their base
  letter instead of stripped, which had produced `b_zier_curve`.

### Added

- **`fccli/curation.py`** -- rank and adjacency read from the toolbar and
  menu placement `harvest_commands.py` already recorded and nothing read.
  510 commands sit in a default toolbar, 399 in a menu only, 215 in
  neither.
- **`man <verb>` cites where FreeCAD puts a command and what it puts beside
  it.** `man box` ends with cone, cylinder, sphere, torus, tube -- the rest
  of the Solids toolbar.
- **`fccli/frecency.py`** -- completion ranks by what this operator actually
  runs, layered over curation rather than replacing it. Mozilla's frecency
  buckets by way of [clicue](https://github.com/aaronsb/clicue): a count
  times a bucketed age multiplier. A partition, not a sort, so an unused
  verb keeps its curation order behind the used ones.
- **`fccli/paths.py`** -- one module owns every directory name.
  `$XDG_STATE_HOME/fccli/history` and `$XDG_DATA_HOME/fccli/aliases`, with
  reads falling back to the old `~/.local/share/FreeCAD/fccli/` so nothing
  is lost. Nothing is moved or deleted.
- **History carries timestamps**, `<epoch>\t<command>`. A line without one
  reads as epoch 0 and counts as frequency, so an existing file still works.
- **Clicking an unfamiliar command names its neighbours** in the command
  line, and stops after five uses. `ActionBridge.cue` turns it off.

- **The dock resizes in both states.** Docked, it takes the height it is
  dragged to. Floating, both axes follow, and the size is remembered apart
  from the docked height -- dragging a floating window tall no longer
  leaves a deep strip across the top of FreeCAD when it is re-docked.
- **A floating command line can be made genuinely small.** The control
  strip's width was the floor for the whole dock; it now clips instead.
- **Long choice lists lay out in columns.** `man view` was one 700-character
  line of 41 names.
- **Qt mnemonic markers are stripped from labels** -- `&Box Zoom` read as
  `&Box Zoom`.
- **A family verb cites its neighbours too.** It runs no command of its own,
  so the toolbar holding most of its members answers on its behalf.

### Fixed

- **Ranking stopped learning once the history ring filled.** The frecency
  tally was cached against the ring's length, and an add past the limit
  trims as it appends -- so at 2000 entries the length stopped moving while
  the contents did not, and the cache never rebuilt. `History.revision`
  counts mutations instead. Timestamps for trimmed lines are dropped with
  them, which they were not.
- **The version banner froze at the last release.** `make release` stamps
  `_build.py`, and the stamp was read before live git -- so from then on a
  working tree reported the released commit no matter what was committed
  since. Git wins wherever there is a checkout to ask; the stamp answers
  for a build shipped without one, which is what it was written for.
- **`version.py bump` stranded the cycle's notes.** It inserted a new
  section directly under the `<!-- next -->` marker, above the
  `## Unreleased` heading notes are written under. It retitles that
  heading instead.
- **`make bvt` overwrote the dock height in real preferences.** Showing the
  dock fires a resize and the dock saves what it is resized to, which under
  Xvfb is the Xvfb window's shape. The run now captures and restores the
  geometry settings, as it already did for the unit schema, and
  `CliDock.persist` turns saving off outright.
- **157 dead lines in `fccli/shell.py`.** `ALIAS_PATH` through `_emit_quit`
  had been pasted twice; the second copy shadowed the first, so a third of
  the module was unreachable.

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
