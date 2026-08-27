# Changelog

<!-- next -->

### Fixed

- **A count typed at a generated verb reaches the object (GH #78,
  ADR-203).** `linear_pattern 100 4` exited 0 and read back `Occurrences
  2`, FreeCAD's default. Every number the command line parses is a float
  and FreeCAD's integer setter refuses one outright, and `_emit_type`'s
  bare `except Exception: pass` made the refusal indistinguishable from a
  write that landed -- `additive_prism 6 10 20` looked like a pass because
  six is `Polygon`'s own default. A step over a counting property now
  carries no unit and is marked `integral`, so a bare number takes nothing
  from the schema and a count works under Imperial as well as Standard; a
  fraction is refused at the prompt rather than truncated at the write,
  and the line stops there rather than running with the value missing; and
  a property FreeCAD will not take is named as an error beside the result,
  one refusal costing only itself. 86 scalar integer parameters across 49
  types, and the 71 that are steps leave the D5 census cured rather than
  counted (212 down to 141). What the swallow was also hiding: `offset 2`
  now prints `Source: Type must be App.DocumentObject or None, not list`
  above ADR-202's invalidity report, which is the first answer to the
  question ADR-202 left open.

- **A settable option no longer reads as part of what the step asks for
  (GH #56, ADR-303).** After `cylinder 10` the prompt read `The height of
  the cylinder [Angle]`, and `[...]` is also how a choice and a finish
  token render -- so the cylinder's angular sweep read as a hint that
  height is an angle. `Option` now says whether it names a property the
  command will set, and `Step.prompt_hint()` renders the two apart: what
  you may type instead of answering keeps the bracket, a property you may
  also set is named after it. `The height of the cylinder  ·  also angle`.
  The dock and both of the socket client's prompt lines call the one
  composer rather than joining the names themselves.

- **A panel step takes the `cancel` its own prompt advertises (GH #71,
  ADR-303).** Every panel printed `name=value sets one · done applies ·
  cancel abandons`, and `cancel` was read as a failed assignment while the
  panel stayed up -- only Escape in the dock or the socket's cancel op got
  out. The step now carries the option, which aborts the verb and lets
  FreeCAD put the model back, and the refusal on a line that will not
  parse names all three ways out rather than two. A field genuinely named
  `cancel` stays addressable: an option is matched against the whole raw
  line and every assignment has an `=` in it.

- **A tier-1 typed verb shows its command's page (GH #38).** `man cylinder`
  printed NAME, SYNOPSIS, ARGUMENTS, GUI and SEE ALSO, and nothing between:
  the wiki body reached the tier-0 launcher, which `_make_room` had
  re-homed to `part_cylinder_2`, while the verb people type got none of it.
  `build_type_verb` now takes the linked command's compiled file, so the
  page reaches both doors to one command.

- **`man` shows the authored example, and what a sweep made of it (GH
  #44).** ADR-501 gives each command one canonical invocation and 266 of
  them are stamped in `fccli/verified.json`. `man` prints the example
  between ARGUMENTS and DESCRIPTION, with the sweep's date and FreeCAD
  version under it -- and where the sweep did not call the result `ok`, the
  result and its detail instead, so a page never documents an invocation
  the harness has already refuted. The example appears on the verb its own
  first token names: sixteen commands have two verbs, and the example
  belongs to one of them. A two-part selection example keeps its `select`
  and says whose objects those are.

- **Forty-five more generated verbs lead with the argument the command is
  about (GH #69).** A tier-1 verb's steps are the type's properties in
  alphabetical order, so `FuzzyTolerance` sorted in front of the length,
  radius or count the command exists for and `additive_box 40` set a
  boolean tolerance FreeCAD clamps to 1. PR #68 authored nine `type` blocks
  for the commands a sweep had driven; this round takes the rest of the
  class that can be defended from FreeCAD's own dialog and property docs --
  the sixteen PartDesign primitives and their eight base types, five
  base feature types, both patterns, Groove and Revolution, Mirrored,
  Draft, both lofts, both pipes, Part's Ellipsoid and Prism, Thickness,
  Offset, Offset2D and Extrusion. Sixty-one types are tuned, up from
  sixteen, and 63 remain untuned and reported on the issue rather than
  guessed at.

- **A failed start no longer reports itself as an addon too old (GH
  #53).** `verify.py` read `"panel" not in _snapshot()` as "this FreeCAD
  predates ADR-302", and an instance that never came up answers `{}`, for
  which that is true -- so a start that failed sent the reader to the
  addon. `precondition()` tells no answer at all from an answer without
  panel facts, and says which.

- **A task panel that will not close no longer costs a sweep 80 results
  (GH #53).** The panel tier closes a panel on the way in and on any
  ending that is not a clean apply, and the close is confirmed rather
  than asked for: `Mesh_FromPartShape` opens a Tessellation panel that
  neither `done` nor `cancel` closes, and every command after it was
  answered "a dialog is already open in the task panel" or reported
  inactive. One sweep recorded 90 stuck panels where 9 commands had left
  one; the other 81 never ran. The command that leaves one is now
  `stuck_panel`, and a command that ran against one is `blocked` -- no
  answer about that command at all, so a later sweep runs it again. Both
  restart the instance, and the restart is a real one: `_restart` reuses
  an instance that still answers, which is right for a wedge and wrong
  for a poisoned one, so an instance the sweep started is quit and
  replaced. One it borrowed is not the sweep's to quit, and the sweep
  stops rather than writing the same fact against every command left.


- **`fccli start --log` is bounded.** FreeCAD held the log file directly,
  and a headless instance whose viewer had been switched into a stereo GL
  mode printed an error per repaint -- 51GB into /tmp in 26 minutes,
  stopped only by the quota (GH #62). FreeCAD now writes a pipe; a small
  child copies the pipe to the file up to `--log-cap` (64 MB unless
  raised), then keeps draining and drops the rest, so the writer never
  blocks and the disk never fills.

- **A value under a step in inches replayed as inches of millimetres.**
  `parse_quantity` hands back FreeCAD's internal value -- millimetres for
  any length -- and `format_quantity` built a Quantity in the step's unit
  from it, so `3in` echoed and replayed as `76.2in`. Every hand-written
  step is in millimetres, which is why nobody saw it until a script
  declared a step in inches. A stored length is rendered as millimetres,
  and a stored angle as degrees, whatever unit the step names.
- **239 commands get their workbench.** The harvest snapshots
  `listCommands()` before activating anything, so whatever the startup
  workbench had already loaded -- Sketcher, Part and Part Design on a
  machine that starts in Part Design, and one Material command -- was
  credited to no workbench, and
  the stem repair that fixes misattribution only ran over commands the loop
  had attributed. It now runs over every command. Std keeps none, which is
  true. The test that asserted `Part_Box` had no workbench was asserting
  the bug.
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

### Added

- **The ledger is mode-aware, and 105 selection and panel commands earn
  their example (GH #54, of #47).** `make verify` drove every example bare,
  which is right for a positional one and wrong for the other two: a
  selection example would have run its own `select` line and judged that,
  and a panel example would have been recorded `panel` for opening the
  panel it exists to open. So the ledger could hold only positional
  results, and it held 161 entries, 160 of them positional.

  It now asks `fccli/modemap.json` how each command is driven and drives it
  that way -- positional bare, selection behind the fixture its
  `selection_hint` names with only the verb half judged (ADR-200), panel
  through the panel step that reads the fields, sets the pairs and presses
  `done` (GH #53). A `manual` command is nobody's to drive: ADR-501 has a
  person confirm those, and the entry says `manual` rather than a result
  the harness did not earn. Every entry carries the `mode` ADR-501's
  schema already showed, and the summary counts the ledger by mode and
  result rather than by result alone -- a selection `ok` and a positional
  `ok` are different facts, and the campaign is spent moving commands
  between them.

  Resume reads the stamp back. An entry stands only if it is about the same
  example, in the same mode, against the same FreeCAD; a version older than
  the current harvest is stale (ADR-501) and a mode the command is no
  longer in asserts a driving that no longer happens. With the checkpoint
  after every command that PR #63 added, `make verify` is stoppable and
  resumable: interrupt it and start it again and it runs what the record
  does not answer.

  105 drafts are promoted from `modemap_sweep.json` to `example:` fields:
  82 selection and 23 panel, every one of them `ok` in the live tier sweeps
  and byte-identical to the draft that earned it. Four passing drafts are
  **not** promoted, and each is why the audit was worth doing -- they
  verified `ok` while their arguments went somewhere the example does not
  read as. `linear_pattern 100 4` set `FuzzyTolerance` (clamped to 1) and
  left `Occurrences` at 2; `polar_pattern 360 8` landed the angle and sent
  the 8 to the tolerance; `sweep Transformed` read `Transformed` as the
  *name of an object* for the `Sections` link and left the Sweep invalid.
  Those three are GH #69, commented with the readings. The fourth,
  `subtractive_pipe standard constant transformed`, never ran the command
  at all: `standard` matched `standard_views`, and that is GH #72.

  The ledger after a live headless sweep of all 266 authored examples:
  **246 ok**, 17 broken, 1 panel, 1 mouse_panel, 1 no_panel -- 142/17/1
  positional, **82 of 82 selection**, 22 of 24 panel. Seven of the 17 are a
  correction rather than a regression: `purge_results` and the five FEM
  `solver_*` and `gravity_load` need an analysis in the document, they fail
  on a fresh instance, and their `ok` on main came from PR #64's positional
  sweep sharing one accumulating document across 246 commands in which an
  earlier command had made one. Every command now gets a scratch document
  of its own, so an example is judged on its own -- which is what ADR-501
  asks of one. The other eleven are order-dependent and all eleven verify on
  a fresh instance: GH #74, with the `after` chain recorded against each.

- **A selection filter is a mode, and the harness lifts it before every
  command (GH #73).** Part's `vertex_selection` and its two siblings turn on
  a global selection gate that outlives the document that was open when they
  ran. With one on, `select Box` answers `= select Box` and selects nothing,
  and every command that needs a selection says "is not available here". The
  first mode-routed ledger sweep ran `Part_VertexSelection` at command 141 of
  266 and charged the twenty commands after it with its consequences, each
  recorded against itself. `build_fixture` now closes the last scratch
  document, opens a new one, and lifts the gate -- in that order, because
  `no_selection_filters` needs an active document and answers "is not
  available here" without one, which is how the first attempt at this left
  the gate standing. Lifting the gate took the sweep from 215 `ok` of 266 to
  243, and the selection tier from 61 of 82 to all 82.

  It is very likely the cause PR #70's review named as missing. That review
  recorded `upgrade` returning exit 0 with nothing built and a body ceasing
  to be the active body, could not reproduce either by volume, and concluded
  that the shape was residue from one particular command nobody could name. A
  gate produces exactly that: the `closed_wire` recipe is four `line`s, a
  `select`, and an `upgrade`, and with a gate on the `select` selects nothing
  and `upgrade` has nothing to join.

- **A line the engine abandoned mid-way is no longer a pass (GH #72).** A
  token at a step that will not parse as that step's value, but does match
  a verb name, cancels the command and runs that verb instead. When the
  verb it escapes to takes no steps, the line exits 0 with the engine idle
  and nothing invalid -- every reading `classify` makes says the command
  verified, and what ran was another command. The harness discarded the one
  thing that says otherwise: the engine's own `<verb> cancelled` on stdout.
  It reads it now, and a line that abandoned its command is `cancelled`
  rather than `ok`. The panel tier already caught this shape as `no_panel`,
  a cancelled verb opening no panel, so it was the positional and
  selection paths that were exposed.

- **A5 reads ADR-200's two-part example (GH #54).** A selection command's
  example is `select <what>; <verb> <params>` -- one written line, two
  typed ones -- and the lint called every one of them a shell line, because
  the semicolon was in its shell-punctuation pattern. The rule now splits
  the halves: the command half is what the verb rules judge, and the setup
  half is held to being a `select`, since nothing else may stand there. In
  exchange it checks the shape against the mode, which is what "shaped for
  the command's mode" always said and the rule could not do: a positional
  command whose example selects operands first, and a selection command
  whose example names none and so runs against whatever was selected last,
  are both reported. The blanket report on any non-positional mode carrying
  an example is gone -- with the ledger driving all three modes it fired on
  every correct case, and the mode-versus-example disagreement it stood in
  for is now answered at runtime by the panel tier's `no_panel`.

- **The verify harness gets a panel tier (GH #53, of #47).**
  `tools/verify.py --modemap --tier panel` runs the verb, asks the panel
  it opens what it answers to, sets the `name=value` pairs the draft
  carries one at a time, and presses `done` -- the protocol #53 found by
  hand, driven for all 272 commands the mode map calls panel. The fields
  come from the engine two ways: the block it prints when a panel opens,
  which is complete, and the complaint on a name the panel has not got,
  which is capped at six names and is the question #53 named. Both are
  read, because `datum_line` offers eleven fields and the complaint would
  have reported six of them. A draft that carries no pairs still runs --
  open, read, `done` -- so a command with nothing authored still says
  whether its panel opens, what it offers and whether it applies.

  Nothing is written per command, for the same reason `panels.py` has
  nothing per command: a panel names its own fields. What is authored is
  the draft. Eight of them, in `fccli/modemap.json`, for the
  parameter-bearing Part and PartDesign batch ADR-200 named: `part_fillet
  filletstartradius=3`, `revolve revolveangle=270`, `partdesign_mirror
  comboplane=Base XZ-plane`, `boolean_operation combotype=Cut` and four
  more. A draft may name its own fixture with `panel_fixture`, because
  `needs_selection` was classified from the wiki: Part_Fillet's page
  describes a dialog, and the dialog fillets nothing unless an edge was
  selected first. Naming the fixture leaves the classification it
  disagrees with legible instead of overwriting it. Two recipes are new --
  two bodies with the second left active, for a PartDesign boolean, and a
  body holding an additive feature, which is what a transform feature
  will pattern.

  The tier drives 136 of the 272 and punts 136 with a reason each, so the
  report answers "why was this command not driven" for all of them. The
  acceptance batch is **8 of 8**: each draft runs to a valid object, and
  the value reaches it -- a 3 mm `filletstartradius` takes a 20x20x10 box
  from 4.00 ml to 3.98 ml, the 19 mm³ the geometry predicts for a 10 mm
  edge; `revolveangle=270` reads back as `Angle 270.00°` and gives three
  times the volume of the 90° one; `attachmentoffsetz=5` puts a datum
  plane at z=15 on the face at z=10. Over the whole tier: 23 ok, 76
  no_panel, 31 mouse_panel, 1 broken, 1 panel, 1 hazard. **76 of the 136
  open no panel** -- the mode map has them in the wrong tier, 40 because
  FreeCAD says the command is not available here and 20 because the verb
  simply ran -- and 31 open one only a mouse can drive. The field names of
  the 25 panels that did open are recorded beside their results, 87
  distinct names, which is the half of GH #50 the mode map does not have.

- **`verify.py --restart-every N` bounds an instance's lifetime, and
  every failure records what ran before it (GH #53).** Something in a long
  sweep breaks a fixture that works on a fresh instance, and what it is
  is not known. Observed once, in a 136-command panel sweep: `upgrade`
  stopped joining four lines into a wire -- exit 0, nothing built -- and a
  body stopped being the active body, so the eight panel drafts read 7 of
  8 there and 8 of 8 one command into a fresh instance. Command volume is
  not the cause: 40 builds of that recipe, five workbench borrows and 330
  commands on one instance reproduced none of it (PR #70 review), so the
  likelier shape is residue from one particular command rather than
  accumulation. A result that is not `ok` now records `after`, the command
  the same instance ran before it, which is what turns "it failed late in
  the sweep" into a name to try; and `--restart-every N` bounds the
  lifetime while the cause is open. It is off unless asked for, because a
  sweep that restarts constantly cannot see the effect at all.


- **The verify harness gets a selection tier (GH #52, of #47).**
  `tools/verify.py --modemap --tier selection` builds the fixture a
  command's `selection_hint` names, hands it over with `select` (ADR-200),
  and runs the verb -- so a selection command is driven the way a person
  drives one, and the example recorded is ADR-200's two-part
  `select <what>; <verb> <params>`. A recipe is command lines only: a box
  for the solid consumers, two overlapping boxes for the booleans, four
  Draft lines and `upgrade` for a closed profile (Draft's own closed-wire
  verbs are all panel-mode), `new_body` over a selected solid for a
  PartDesign body and its BaseFeature, `draft_to_sketch` plus
  `duplicate_object` for a sketch inside that body. Each command gets a
  scratch document of its own, so no fixture feeds the next. A fixture
  that will not build is `no_fixture` -- the harness's gap, recorded
  against the harness rather than blamed on the verb -- and one that fails
  because the instance died is the hazard the old sweep already knew how
  to survive.

  The vocabulary reaches 112 of the 383 selection commands, over Part,
  PartDesign, Draft, Std, OpenSCAD and Surface. The other 271 are punted
  by workbench with a reason each: Sketcher's 42 act inside a sketch in
  edit mode, TechDraw's 82 want a page with views on it, and FEM, CAM,
  Mesh, Arch/BIM, Spreadsheet and the rest each need a subject no command
  line builds today. Those are the panel tier's (GH #53).

  The live sweep: 86 of 112 run to a valid object, 15 leave an invalid
  one, 6 are broken, 5 turn out to open a panel. No hazards and no
  restarts. **#52's acceptance is not met and the tier says so.** The
  acceptance names the batch ADR-200 named -- the parameter-bearing Part
  and PartDesign commands, 23 of which the mode map now calls selection --
  and that batch stands at **6 of 23**: 13 invalid, 2 broken, 2 panel. The
  other 30 Part/PartDesign selection commands take no arguments at all, and
  28 of them pass; adding the two halves gives 34, which is a real number
  about an easier set. #52 stays open.

- **Nine commands stop reading their first argument as a tolerance
  (GH #69, found by #52).** A tier-1 verb's steps are the type's
  properties in alphabetical order, and `FuzzyTolerance` sorts in front of
  the length, radius or diameter the command is about. `fillet 10` set
  `FuzzyTolerance` -- clamped to 1 -- and left `Radius` at its 1 mm
  default; `pad 10` and `pocket 5` set `Direction` and the tolerance, not
  `Length`; `hole 6 10` set `BaseProfileType`. `ruled_surface Automatic`
  is the same shape without a tolerance: two link properties sort first, so
  it went looking for an object called `Automatic`. Nine command files now
  carry a `type` block naming the order a person types and hiding the
  tolerance, which is a tree edit and not a FreeCAD one. `man fillet` is
  `fillet <Radius>` rather than sixteen properties, and 11 dimensionless
  steps leave the D5 census.

  Re-running the parameter-bearing slice across the change: both `broken`
  results cleared, and **no invalid converted**. `fillet 10` now sets
  `Radius` to 10 mm and the Fillet is still `Touched, Invalid`, so what
  invalidates those features is independent of argument routing --
  fourteen named instances are on GH #57, and the cause is open.

- **The grammar spec gets a lint (GH #49, of #47).** `tools/interaction.py`
  checks the D group over the compiled tree and the built registry: D1
  every listed choice is a value some input selects, D3 every step has a
  pool to offer, D4 a verb answers to the word it is about, D5 a quantity
  echoes in the unit it was read in. `make grammar` prints it and writes
  the per-command verdicts into the same record `make descriptions`
  writes, so one file carries every rule that has spoken about a command.
  It finds GH #55 (`view iso`, shadowed by `isometric`) and 20 more of that
  shape, 4 choices two commands answer to, 264 dimensionless steps echoing
  in millimetres, and 79 commands whose prefix names a workbench they do
  not ship in (GH #21). A choice collision is above the line -- it runs the
  wrong command with no refusal and no message -- with the four the tree
  carries grandfathered by name in `KNOWN_COLLISIONS`, so the next one
  fails the lint the day it appears. The other three problem classes are
  empty today, which is what lets the lint join `make check`.
- **The choice matcher is one function.** `grammar.match_choice` is what
  the engine's accept path, its restart guard and both of the
  highlighter's choice branches now call; there were four copies of the
  same two-line comparison. No behaviour change -- each copy was
  character-identical -- but the D1 lint reads the matcher there rather
  than restating it, so it cannot end up answering a question about a
  comparison the engine no longer makes.
- **154 commands gain a verified example.** The GH #47 positional sweep
  drove all 246 mode-map drafts against a live headless instance; 159
  ran to completion with a valid result, of which 4 were already
  authored and 1 (BIM_ImagePlane) passed only vacuously -- its argument
  names a file that need not exist -- leaving 154 promoted into their
  command files' `example:` field and stamped into the ledger. 153 of
  them are bare verbs: verified to execute and leave a valid document,
  which says nothing yet about positional argument handling. The
  remainder: 69 broken (mostly drafts needing a context the bare
  instance lacks), 6 incomplete, 4 panel-tier, 8 hazards -- triage
  feeds the selection and panel tiers. Rendering the example in `man`
  is GH #44.
- **A sweep survives its own targets.** `tools/verify.py` records a
  command that kills or wedges the instance as `hazard`, starts a fresh
  headless one, and continues; recorded hazards are skipped on later
  sweeps unless `--force`. The ledger is written after every command, so
  a stopped sweep loses at most the command it was on. `--modemap` drives
  the mode map's positional drafts instead of the dictionary's authored
  examples, recording to `modemap_sweep.json` and skipping drafts already
  recorded; `--start-at` resumes mid-alphabet. A KNOWN_HAZARDS list seeds
  the skips: Std_ToggleToolBarLock (GH #61), Std_TestProgress (GH #60),
  and the stereo view modes that poison a headless GL context (GH #62).
- **A mode map for every command.** `fccli/modemap.json` classifies all
  1111 commands by interaction mode -- 383 selection, 272 panel, 246
  positional, 210 manual -- with a drafted example, what must be selected
  first, and a confidence grade per command. Produced by the GH #50
  classification campaign over the offline wiki and each verb's steps;
  it sizes the verification tiers and feeds the selection and panel
  harnesses (GH #52, #53).
- **The socket replays the session from a message ring.** The server keeps
  the last 4096 durable messages, sequence-numbered: `fccli tail -n` reads
  the recent scrollback without touching anything, `fccli attach --resume
  ID` replays what happened while a client was away (the id prints on
  exit), and what leaves the ring lands in `transcript.jsonl` under the
  state directory. A RESULT now names the object it made -- `{name, label,
  type, state}` -- instead of dropping it at the wire; the state reply says
  whether a task panel is open and which objects in each document are
  invalid, and `fccli state` prints both. The verify harness reads those
  facts instead of scraping rendered text, and a command that computes an
  object FreeCAD rejects is `invalid`, not `ok` -- the fillet that
  vanished in the live demo is caught at every door. Protocol 2. ADR-302.
- **The prompt shows where the session is.** `PartDesign Body › Sketch* [2]
  /plinth > `: the workbench, the active Body or Part and the object in
  edit, a `*` when the document is dirty, the selection count, the working
  directory -- each left out when empty, so a fresh session still says
  `> `. One `STATE` message from the session, after every command and on
  workbench, selection and document change; both terminals render it. Tab
  puts the active workbench's commands first within a rank. A command
  FreeCAD says cannot run now is refused before running, with the reason
  from its file's `requires`; `!` runs it anyway. ADR-300.
- **A root the terminal navigates.** `~/.local/share/fccli` laid out after
  the FHS on first run: `bin/`, `etc/`, `lib/commands` linking to the
  shipped command tree, `lib/addons/<name>` to what each addon ships, and
  `macros` to FreeCAD's macro directory, read from its preference. The
  session has a working directory, moved by `cd` from either terminal and
  shown in both prompts; `ls`, `pwd` and `cat` read the tree; Tab on a path
  offers what is there. The root is a jail: `cd ..` at `/` stays at `/`.
  ADR-601.
- **Scripts.** A `.fccli` file is YAML frontmatter -- `doc`, `steps` in the
  step syntax patches use -- and a body of command lines with `$id` for
  each argument. One in `bin/` is a verb by file name: it completes,
  prompts, and replays. Elsewhere `run plinth/tower 20` or `./tower 20`
  runs it with the arguments inline. The first error or unanswered prompt
  stops it; the call is one history line and the lines inside are not
  recorded; each line is its own undo step. `rehash` reads `bin/` again;
  `man` on a script shows the `.md` beside it. A `.FCMacro` runs through
  FreeCAD's Python console. The format is experimental, as ADR-601 says.
- **One file per command.** `fccli/lib/commands/<workbench>/<Command>.md`
  for all 1111 -- Markdown with YAML frontmatter, a `generated:` block the
  tool owns and authored fields (`verb`, `aliases`, `requires`, `panel`,
  `family`, `choice`, `rank`, `type`) a person owns, the body seeded from
  the command's page in FreeCAD/FreeCAD-documentation (854) or its tooltip
  (257). `make commands` writes what is missing, `make dictionary` compiles
  the tree to `fccli/dictionary.json`, and `tools/lint_dictionary.py` runs
  in `make lint` with ADR-100's five rules.
- **The tree is read.** `register_all` loads `fccli/dictionary.json` and a
  command file's `verb`, `aliases`, `rank`, `family`/`choice`, `requires`
  and `panel` reach its verb; the page becomes the verb's manual, which
  `man` prints as DESCRIPTION. `std/_families.yaml` now holds the list of
  leading words that are not actions, moved out of `families.py`. First two
  authored entries: `Mesh_PolySegm` is `mesh_segment` and `Draft_Split` is
  `draft_split`, generic words given back. `requires` and `panel` are
  carried and not yet acted on; `type` is parsed and not yet applied.
- **`make reconcile`.** Harvests FreeCAD afresh, refreshes the wiki clone,
  and reports what changed against the committed tree: commands added,
  removed, re-homed, fields changed, bodies reseeded, conflicts where a
  page moved under a body somebody wrote, and authored verbs that became
  what the factory derives anyway. `FLAGS=--apply` brings the tree, the
  descriptor and the compiled dictionary to the new harvest together.
  A `seed` hash in each generated block is what tells a written body from
  a stale one. Against a fresh harvest today: nothing changed.
- **Every command carries its wiki page.** `getInfo()` returns `whatsThis`,
  the page name FreeCAD's F1 help resolves against, and the harvest had
  been dropping it. It is recorded as `wiki`: 1106 of 1111 have one, 9
  differ from the command name (`TechDraw_Annotation` documents itself at
  `TechDraw_NewAnnotation`), and it is the link ADR-100 seeds each
  command's documentation from.
- **An addon's commands reach the command line without a new descriptor.**
  The descriptor is harvested once, from stock FreeCAD, so an addon
  installed on this machine had no verbs until somebody regenerated it with
  the addon present. Now a command FreeCAD has registered that the
  descriptor never saw gets a tier-0 verb at startup, named from
  `getInfo()` the way the harvest names one -- and again whenever a
  workbench is activated, since an addon that registers in `Initialize()`
  has nothing until its workbench opens. Measured live: CurvedShapes brings
  ten verbs the moment its workbench is activated, and none before.
- **Decision records.** `docs/architecture/` holds ADRs in six domains --
  vocabulary, engine, surface, host, practice, system -- managed by
  `docs/scripts/adr`, with lint in `make check`. ADR-500 records the
  adoption. ADR-100 records the command dictionary: one generated file per
  command, organised by workbench, the tool owning a `generated:` block
  it rewrites on reconcile and a person owning the rest. ADR-600 is the
  layer model; ADR-601 is the directory tree the terminal navigates, with
  `.fccli` scripts, notes, and FreeCAD's macros symlinked in.
- **`docs/state.md`.** A reference for the engine's two states and the six
  machines around it: states, transitions, and the invariants the rest of
  the code depends on.

### Changed

- **The zoom and view tables moved from code into the command tree.**
  `shell.py`'s `ZOOM_TARGETS` and `VIEW_TARGETS`, and the hand-written
  `zoom` verb, are gone. The five fit/zoom commands carry `family: zoom`
  in their command files; `zoom`'s aliases (`fit`, `zf`), default (`all`)
  and doc live in `std/_families.yaml`. Alternate spellings -- `extents`
  for `all`, `iso` and `axonometric` for `isometric`, `rear` for `back` --
  are each a command file's `also`. A family verb now carries a default
  and aliases, and the lint refuses two commands claiming one choice in a
  family. `zoom front` is now `view front`, the two being separate
  families; every other spelling is preserved.
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
