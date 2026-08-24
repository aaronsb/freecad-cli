# Changelog

<!-- next -->

### Fixed

- **148 commands get their real names and documentation.** The harvest read
  everything off QActions, and 147 registered commands have none -- they are
  runnable and appear in no toolbar and no menu. They reached the descriptor
  carrying only a name, which slugged into verbs like `arch_multimaterial`
  whose entire documentation was the string `Arch_MultiMaterial`. FreeCAD
  had their menuText and toolTip the whole time behind
  `Gui.Command.get(name).getInfo()`, which `harvest_commands.py` asserted
  did not exist. `multi_material` is now "Creates or edits multi-materials",
  `nest` is "Nests a series of selected shapes in a container". Each field
  now picks its own source rather than the whole entry riding on whether a
  QAction exists -- `Std_WindowsMenu` has one whose text is empty, and it
  stayed bare one branch away from the fix.
- **909 tooltips were the command's own name glued to a sentence.**
  `act.toolTip()` is rich text in three blocks and `clean()` ran them
  together, so `Part_Box` documented itself as
  `CubeCreates a solid cubePart_Box` -- and that string is what `man`
  printed. The tooltip now comes from `getInfo`, which is the plain
  sentence, falling back to the action's statusTip and then to the rich
  text with the trailing name taken off.
- **The descriptor no longer names the machine that built it.** TechDraw's
  `PatIncluded`, `SvgIncluded` and `SymbolIncluded` defaults pointed at a
  copy FreeCAD had made inside the transient document's cache directory --
  24 absolute paths through a home directory, carrying a per-document UUID
  that changed on every regeneration, into a directory deleted with the
  document. `make descriptor` is now byte-identical across runs.
- **A contested short name goes to the command FreeCAD surfaces.** Two
  commands whose labels slug the same both want the plain name and the
  first registered took it, which alphabetical order decided by accident:
  `compound` went to CAM_Compound over Part_Compound, `material` to
  Arch_Material over the BIM_Material sitting in a toolbar. Twenty names
  moved that way, every one off a command with a toolbar or menu entry and
  onto one reachable only from code. Registration is now ordered by that
  presence, which is the same signal `curation.py` ranks completions by,
  and the descriptor's sorted order still breaks genuine ties.
- **A command whose verb name is taken is no longer dropped in silence.**
  Two commands whose labels slug the same are ordinary. The loser used to
  vanish -- 90 commands before this, and 133 once labels got better and
  more of them wanted the same short names. It now keeps the prefix its
  command name already carries, falling back to the command's own slug and
  then a suffix, so every one of the 1111 commands has a verb.
- **Draft's grid is left as the operator configured it.** The picker turned
  `show_always` and `show_during_command` off and hid the grid on every
  Draft bootstrap, every snap and every teardown, on the grounds that
  `gridSpacing` of `0` draws stray lines across the model. It never wrote
  the preference, and it overruled one: `alwaysShowGrid` was on, Draft
  honoured it in `setTrackers`, and the picker switched it back off for the
  rest of the session. `quiet_grid` and the console-warning suppression
  around it are gone; `report_grid` says the spacing is zero once, on the
  command line, and names the preference page.
- **A workbench fetched to run a command is handed back.** Typing an Arch
  command with BIM unloaded moved the operator from wherever they were to
  BIM and left them there. `_workbench_borrowed` activates, takes the
  command registration -- which survives the switch, so it is still a
  one-off -- and puts the previous workbench back, saying on the command
  line where it went and where it came back to. FreeCAD has no
  load-without-activating, so the round trip runs both workbenches'
  `Activated`/`Deactivated` hooks; what those write is FreeCAD's business
  and is now written down rather than discovered.

- **A toolbar flash no longer sticks.** `actions.flash` read the live
  stylesheet as the thing to restore, so a second flash inside the first
  one's 350ms saved the flashed state as the real one and left FreeCAD's
  button yellow until the workbench reloaded. The base is parked in a
  widget property and taken back once.

### Changed

- **`constrain` is a command verb rather than a family.** Sketcher's
  CompConstrainTools carries the label "Constrain" and now claims the name.
  Its 21 constraint commands stay individually reachable. Whether a family
  should outrank a generated command verb is a real question -- it would
  move about thirty names -- and is not settled here.

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

- **`describe`** reads an object out as text -- identity, placement, the
  parametric properties, and what the shape measures. Bare it lists the
  document. Closes #1.
- **A rubber band follows the cursor** from the last point placed. It is
  Draft's -- `Gui.Snapper.snap(lastpoint=...)` lights `Snapper.trackLine`
  from that point to the cursor, and always could. It never appeared
  because `lastpoint` was arriving as a document object. Closes #2 with
  FreeCAD's own tracker rather than another one. Closes #2.
- **`shortcuts`** offers FreeCAD's key chords as aliases: `A,X` becomes
  `ax`. `list`, `why`, `import`, `drop`. Closes #4.
- **`units.format_measure`** for numbers FreeCAD computed rather than ones
  somebody typed, which are not owed a round-trip and print better without
  one: `5.03 ml`, not `5.02654824574ml`.
- **`fccli/properties.py`** holds the property filter that `describe` and
  the type harvester now share, so what a verb asks for and what describe
  reads back cannot drift apart.

### Changed (tests)

- **`tests/test_spike.py` is now `tests/offscreen.py`.** It stopped being a
  spike a long time ago and is the whole offscreen suite. Its docstring
  claimed to prove four things; there are eighteen sections.
- **24 edge cases added** -- every frecency bucket boundary and which side
  each edge falls on, a future timestamp, an empty curation, column layout
  with nothing and with one oversized item, the XDG fallback ceasing once
  the new file exists, and a history file holding both line formats.

### Fixed

- **A verb that acts on a selection could never run.** `move`, and anything
  else with a selection step, asked "select objects" and had no way to be
  answered: nothing in the engine ever read `Gui.Selection`. Enter said the
  step was required, forever. The engine now takes the live selection --
  and takes it without asking when something is already selected, which is
  what select-then-act means.
- **`last_point` returned a document object.** It scanned every step for
  anything list-shaped, so for any verb with a selection step it handed
  back the last selected object. That went to `Gui.Snapper.snap` as
  `lastpoint`, which passes it to Draft's own tracker, which raises inside
  `p1()` -- on every mouse move, after part-configuring that tracker.
- **`make bvt` ran on the operator's desktop.** It used Xvfb only when
  `DISPLAY` was unset, so running the suite on a workstation opened FreeCAD
  windows on that workstation and popped its dialogs at whoever was there.
  It now always takes its own display; `FCCLI_BVT_DISPLAY=1` asks for the
  real one.

- **A declared choice was hijacked by a command of the same name.**
  `_is_restart` guarded text, point and quantity steps and forgot choices,
  so `view sketch` cancelled `view` and ran the `sketch` verb. 242
  verb-and-choice pairs read that way, `constrain coincident` and
  `additive helix` among them.
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
- **The test suites wrote into the operator's own command line history.**
  The offscreen suite builds a real Session, so `History()` resolved to the
  real file -- and one of its checks is "history clear empties the ring",
  which truncated it. The live suites appended their commands to it. All
  three now run against a scratch `XDG_STATE_HOME`. This mattered more once
  history began feeding completion ranking: a test run was not just noise in
  the ring, it was a vote.
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
