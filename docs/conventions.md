# Conventions

Every rule the command line follows, in one place. Each was decided once and
holds everywhere — in the dock, in the terminal, and in what an agent reads
over the socket.

## Grammar

| Rule | |
|---|---|
| First token is a **verb** | Everything after a space is an argument. |
| Trailing `!` **forces** | `close!`, `quit!` — past a refusal, never past an error. It also takes the floor, or a session whose floor is stuck could not be told to quit. |
| A unique **prefix** runs | `pol` + Enter is `polyline`. Tab is for discovery; prefix is for speed. |
| Bare **Enter** finishes a repeating step | `polyline` takes points until you stop. |
| **Esc** / **Ctrl+C** cancels | The command, not the session. |
| **Enter** on an empty prompt repeats | The last command, minus anything a click supplied — so it waits for a fresh one. Rhino and AutoCAD do the same. |
| **Right-click** repeats, or picks from recent | Rhino repeats on a right-click here; AutoCAD offers a Recent Commands menu. Both are on it — the top item repeats, the rest are what came before. |
| **Space** is a separator, not Enter | Rhino and AutoCAD submit on Space, because they take one value per prompt. This grammar takes a whole command on one line, so Space separates arguments and passes through to FreeCAD when idle. Enter, right-click and Tab already reach the repeat. |
| A verb typed **mid-command** restarts | Only when the token cannot be read as input for the open step, so `c` stays `Close` inside `polyline`. |

## Arguments

**Matched by kind, positional within a kind.** A coordinate is recognisably a
coordinate, so it finds the point step wherever it appears. Three lengths in
a row are told apart by order and nothing else.

```
circle 0,0,0 20      circle 20 0,0,0      circle 20 → click
```

All three work. So does a line recalled from history, whatever order it was
typed in.

**Points are asked for last.** Everything typeable comes first; the pick is
what commits the command. That is what makes `circle diameter 10` → click →
Up → Enter → click a working way to place a series.

Selections come first — pick the thing, then say what to do to it. A step can
override with `prompt_order`.

## Coordinates

```
10,20,30      absolute
10,20         z from the previous point
@10,0,0       relative           (AutoCAD spelling)
r10,0,0       relative, alternate spelling
100<45        polar, in the XY plane
3/8in,1in,0   any unit FreeCAD's parser accepts
```

## Units

- **Display follows FreeCAD's schema.** `units imperialbuilding` and 9.525mm
  reads as `3/8"`. Conversion goes through `getUserPreferred` and
  `getValueAs`; there is no mapping table in this addon.
- **A bare number takes the schema's unit**, not internal millimetres. `12`
  means twelve of whatever you read in.
- **Tab on a bare number appends that unit**, so what it means is visible.
- **Every rendering round-trips.** Schema output rounds and its compound
  imperial form does not parse back, so a rendering that fails to read back
  falls back to a precise conversion.

## Colour

Colour says *what a token is*.

| | |
|---|---|
| **verb** | teal, bold |
| **x / y / z** | terracotta / sage / steel — FreeCAD's axis colours, desaturated |
| **dimension** | from `Unit.Type`: length, angle, area, mass each their own |
| **option keyword** | yellow |
| **object name** | blue when it resolves in the document |
| **error** | saturated red, wavy underline |

An axis colour is muted so a component never reads as the error red, which
stays saturated and keeps its underline.

## Weight, slant, underline

Each carries exactly one meaning.

| | Means | Example |
|---|---|---|
| **Bold** | the verb — the token that decides what every other token means | **`circle`** |
| *Italic* | the command line supplied this, not you | *`0,0,0`* when the schema supplied the unit; the ghost suggestion |
| <u>Underline</u> (dotted) | a click produced this, and a click will replace it | a recalled line's coordinate |
| Underline (wavy, red) | this will not parse | `zz` |

## History

- **The ring holds the assembled command**, not the fragments typed to build
  it. A polyline entered over four Enters is one entry.
- **Up recalls the whole line**, with any clicked part underlined.
- **Enter on an untouched recalled line re-arms it** — the clicked tail is
  dropped and the next click places it again.
- **Editing it makes it yours.** The underline goes, and Enter runs what is
  written.
- **Tab walks a remembered command out**, one argument per press.
- **`history clear` empties the ring**, and does not record itself doing it.
  A verb can declare `record=False` when its whole job is the ring.
- **Tab on an empty line offers recent commands.** Shells answer that key by
  listing every executable on `PATH` — noisy enough that they prompt first —
  and here it would be 1250 entries beginning `1_front`. Tab has never meant
  history anywhere, so nothing is being broken by making it useful.

## Scope

`use <domain>` narrows what Tab offers to one corner of FreeCAD. Typing `c`
against 1250 launchers is a wall, not discovery; scoped to Sketcher it is 22
candidates.

- **Domains are read off the verbs**, from the command a verb runs or the
  type it builds. Nothing is tagged by hand.
- **A scope never hides a verb someone wrote.** Hand-written, patched and
  family verbs always complete; the scope narrows the launchers.
- `use` alone lists the domains and says which is active; `use off` clears.
- `commands` lists the domains, `commands <domain>` lists what is in one.

## The shared line

One session has one line being typed, the same as it has one prompt.

- **The dock broadcasts what a person types there**, so a `fccli watch` pane
  shows it live. Rendering a client's command is not typing: only a real
  edit claims the floor, or the dock would lock every client out of a
  session nobody is using.
- **The floor is busy when the engine is collecting or a line is
  half-typed** — not whenever the dock has focus. An idle dock with an empty
  line holds nothing, so a one-shot lands in the gaps.
- **A client without the floor is ignored with a reply**, never silently
  dropped.
- **Read-only operations are never blocked.** `history`, `state`, `watch`
  and `docs` work whoever is typing.
- **`fccli watch` is where a terminal renders the shared line.** The REPL
  cannot: readline owns that row of the terminal.

## Completion

- **Verb names complete at the start of a line only**, or at a step that
  declares its value is a command (`man`, `alias`, `check`).
- **A step says where its candidates come from** — `Step.completes` is one of
  `verbs`, `objects`, `aliases`, `schemas`. Selection steps default to
  document objects.
- **Tab cycles**, in both the dock and the terminal. The terminal binds
  `menu-complete` for that reason: readline's default inserts the longest
  common prefix, which for `c` against chamfer/check/circle/clear is `c`.
- **Completions are computed once**, in `fccli/completion.py`, and the socket
  serves them. There is no second implementation to drift.
- **Verb names are offered in rank order**, promoted first. See Curation.

## Curation

FreeCAD's command registry is flat: `Part_Box` and `Std_TestQuestion` are
peers in it. Its toolbars and menus are not, and that difference is the
project's own answer to which commands matter and which belong together.
`tools/harvest_commands.py` records the placement by activating every
workbench and reading it off the QAction; `fccli/curation.py` is what reads
it back.

| Rank | Meaning | Commands |
|---|---|---|
| `promoted` | in a default toolbar | 510 |
| `menu` | reachable from a menu, no button | 399 |
| `registry` | neither — internals, test hooks, context-menu-only | 215 |

- **Rank orders; it never hides.** Every verb stays reachable by typing its
  name. Finding out the program does something you did not know it did is
  most of what a command line is for, and a registry-rank verb that sorts
  last is still there when you type it.
- **A hand-written or patched verb ranks promoted.** It exists because
  somebody decided the command line needed it.
- **A family ranks as its best member.** `view` runs no command of its own,
  so it has no placement to read; what it gathers does.
- **Adjacency is the rest of the toolbar.** `man box` cites cone, cylinder,
  sphere, torus and tube because FreeCAD put them on one toolbar. Nothing
  here is a list somebody maintains — deleting `curation.py` loses the
  ordering, not any data.

## Habit

Curation is the same answer for everyone. `fccli/frecency.py` is the layer
that makes it personal, and it composes on top rather than replacing: verb
names are ordered by curation, then names with a history are lifted above
the rest. Somebody who draws walls all day stops being offered `box` first
because Part's toolbar is bigger than BIM's.

The weights are Mozilla's frecency buckets by way of
[clicue](https://github.com/aaronsb/clicue) — count times a bucketed age
multiplier, integer arithmetic, no curve.

- **A partition, not a sort.** An unused name is not competing on a score of
  zero; it is behind the used ones, in the order curation already put it.
  Alphabetical there would throw curation away.
- **`now` is a parameter.** Nothing in `frecency.py` reads a clock, so an
  ordering is reproducible in a test rather than drifting with the calendar.
- **A missing timestamp weighs 1**, degrading that entry to plain frequency.
  History written before timestamps existed still counts.
- **Clicking counts.** A toolbar click reaches the ring as a command like
  any other, so the ranking learns from the mouse as well as the keyboard.
- **The click cue fades.** Clicking an unfamiliar command names its
  neighbours; after `ActionBridge.CUE_UNTIL` uses it goes quiet. A cue that
  never goes away is furniture.

## Geometry

- **Docked, the user sets height; floating, both axes.** The two sizes are
  remembered under separate keys, so neither state inherits the other's
  shape.
- **The control strip clips rather than setting a floor.** A layout makes
  its widget as wide as its children and Qt reads that back through
  `minimumSizeHint` whatever the layout's constraint says, so the strip and
  the body are `_Squeezable` — they report no minimum width. The scrollback
  is what somebody resizes to see.
- **`CliDock.persist` turns geometry saving off.** A test shows a real dock
  in a window whose shape it did not choose; saving that would replace a
  real setting. Stopping the debounce timer is not enough, because a later
  relayout restarts it.

## The viewport

- **Draft draws.** Snapping, the snap markers, the grid and the rubber band
  from the last point to the cursor are all Draft's, reached by passing
  `lastpoint` to `Gui.Snapper.snap()`. This project wrote its own
  `SoAnnotation` line for one commit before finding `Snapper.trackLine`
  already there; the line had never appeared only because `lastpoint` was
  arriving as the wrong type. Look for the FreeCAD tracker before adding a
  node to the scene graph.
- **`lastpoint` is a point.** `Snapper.snap` hands it straight to its own
  tracker and raises inside `p1()` if it is anything else — after having
  part-configured that tracker, on every mouse move. `Engine.last_point`
  reads only point steps for this reason.
- **Frame-rate updates do not go on the bus.** The bus carries roles a dock
  renders in Qt colours and a terminal renders in ANSI, and it crosses a
  socket. What happens on every mouse move belongs to the viewport.

## Files

`fccli/paths.py` is the only module that names a directory of ours.
FreeCAD's own `Mod` roots are named where they are read, in
`fccli/patches`.

| | |
|---|---|
| `$XDG_STATE_HOME/fccli/history` | what accumulates by use — the spec names history as the example |
| `$XDG_DATA_HOME/fccli/aliases` | what the user wrote down on purpose |
| `$XDG_DATA_HOME/fccli/patches` | the same, in Python |
| `$XDG_DATA_HOME/fccli/shots` | where `screenshot` writes when told nowhere else |

- **Reads fall back to the pre-XDG location**, `~/.local/share/FreeCAD/fccli/`.
  Writes only go to the new path, and nothing is moved or deleted — the
  fallback stops applying by itself once the new file exists. User patches
  are a directory rather than a file, so both are scanned and the XDG copy
  wins where a name appears in each.
- **A test may not read or write any of these.** Three did, and each was
  invisible until something else broke: the offscreen suite loaded the
  operator's real history into every test ring, drove `shortcuts import`
  into their real alias file, and moved `UserSchema` — a persisted FreeCAD
  preference — with the restore on the happy path only, so a failure left
  the next run reading bare numbers as inches.
- **History lines are `<epoch>\t<command>`.** A line with no tab is read as
  epoch 0 rather than skipped.

## Verbs

Four tiers, each only as hand-made as it needs to be.

| Tier | From |
|---|---|
| 0 | every registered command — and, where it opens a task panel, that panel's own parameters |
| families | a group FreeCAD spread apart, gathered under one name with a choice |
| 1 | every parametric type, with steps from its own properties |
| 2 | hand-written and patched |

**A task panel names its own parameters, so none of them are written here.**
Its widgets carry the names its `.ui` file gave them — `xPositionSpinBox`,
`planeLength`, `AngleQSB` — the same in every language FreeCAD ships,
unlike the labels beside them. Values are typed in rather than set, so
FreeCAD's parser runs and `3/4 in` lands as 19.05mm without `fccli/panels.py`
knowing what an inch is.

Three things the shape of a panel forces:

- **A panel is a stack, not a widget.** `Part_Primitives` puts
  `PartGui__DlgPrimitives` and `PartGui__Location` side by side as siblings.
- **The field set is live.** A combo box swaps a `QStackedWidget` page. A
  step looks its field up by name when it writes, never holding the widget.
- **Order comes from the screen.** Tab order lists Transform's eight hidden
  checkboxes first and its x/y/z positions last.

**A panel keeps its own undo and puts everything back on Cancel**, which is
why a panel verb opens no transaction — a second wrapped around it would
nest inside. It also applies as each field is written, so answers land as
they are given rather than in a batch at the end.

**Whether a verb was generated is stated, not inferred.** `Verb.generated`,
set by the factory, read through `curation.authored`. The emit a verb
carries stopped answering it: every generated command verb now shares one
with the hand-written panel verbs.

**Nothing generated takes a name a hand-written verb owns.** The generated
one keeps a qualified name instead — `Part::Box` becomes `part_box` because
`box` is hand-written and can pick a corner.

**Where a derived verb reads worse than a curated one, curate.** `zoom` is
hand-written because it gathers commands across two name stems the family
splitter cannot join.

## Undo

**One typed line is one undo step**, labelled with the line. FreeCAD's Edit
menu reads *Undo box 10mm 10mm 10mm*.

Objects created outside a transaction never reach the undo stack, and
`UndoMode` is off by default on a document nobody has told otherwise, so
both are set by the engine rather than left to each verb. A verb that
manages documents rather than editing them declares `transactional=False`.

## Screenshots

**`screenshot` prints where it wrote.** A person can open the file; an agent
driving the session over the socket can find it without guessing the name.

Default is the 3D view through FreeCAD's `saveImage`, auto-numbered under the
document name. `window` grabs the whole application, which needs real
hardware GL — a widget grab of an OpenGL viewport on a virtual display comes
back as flat colour.

## FreeCAD's settings are FreeCAD's

**Read a preference, never overrule one.** This project is a way of
interacting with FreeCAD, not a second opinion about how FreeCAD should be
configured. Writing a preference and defeating its effect at runtime are
the same imposition through different doors — the picker once turned
Draft's grid off on every snap while `alwaysShowGrid` was on, and called
that restraint because `user.cfg` was untouched.

- **Report the condition, do not correct it.** A grid that draws nothing
  because `gridSpacing` is `0` gets one line naming where to fix it.
  `fccli/picking.py` `report_grid`.
- **Borrow and return.** A command that needs its workbench loaded does not
  need it left in front. `fccli/panels.py` `_workbench_borrowed`.
  `fccli/actions.py` `flash` is the same move on a toolbar button, and
  shows the trap: it saves what to restore into a widget property rather
  than reading the live stylesheet, because a second borrow inside the
  first one's window otherwise saves the borrowed state as the real one.
- **Write only what was asked for, and only where it belongs.** `units`
  writes `Units/UserSchema` because somebody ran `units`, which is the
  command-line spelling of Preferences → Units. Everything this project
  keeps for itself lives under `Mod/fccli`.

**A standing instruction is not a running command.** A preference outlives
every command, so overruling one reaches past what the operator asked for.
`units` is not a counter-example — there the preference is what was asked
for.
An event filter armed around a typed command *is* that command running, and
is not the same thing. That is why `keyfilter.py` swallowing
FreeCAD's bare-key shortcuts is fair and `quiet_grid` was not: the filter
is scoped to focus and engine state, comes off with `remove()`, and is
visible and switchable in the dock. `modals.py` clicking buttons on
FreeCAD's own dialogs is the same case, refcounted to one emit.

**A borrowed workbench cannot be borrowed quietly.** FreeCAD has no
load-without-activating, and `Activated()` / `Deactivated()` hooks are the
workbench's own business: BIM's writes `RestoreBimViews` and `BimViewsSize`
into `Mod/BIM` and calls `Snapper.hide()`. A fetch therefore costs a round
trip through two workbenches' hooks and fires more of them than switching
and staying would. Accepted, because the alternatives are refusing to run
the command or leaving somebody where a typed command moved them. What this
project owes is not stacking its own writes on top.

**Tests may read the operator's settings and may not write them.** A GUI
suite runs inside a real FreeCAD and its job is checking that FreeCAD's
state matches what FreeCAD's own settings ask for — stubbing the
preference would replace that assertion with a tautology about the stub.
Reading one has a second cost, though: a check that compares live state
against a preference is silent on any machine where the preference makes
both sides agree by accident. Say so in the run when it happens, rather
than printing a green line that carries nothing. `tests/bvt.py`
`suite_tracker`.

The operator's real history and alias file are off limits outright —
`tests/offscreen.py` runs against a scratch XDG root for exactly this. A
preference this project does not own may be written only where the write
*is* the thing under test, and only inside a `finally` that puts it back.
§4f writes `Units/UserSchema` because `units`' whole job is that
preference; `main()` restores it. A `finally` is what makes that one case
allowed, not a general licence.

## Dialogs

**A command takes its arguments inline and never raises a modal.** `save`
writes without a file chooser; `close` refuses on unsaved work rather than
asking; `!` discards.

That is what lets the whole application be driven unattended — `make bvt`
and `make socket` depend on it.

Unsaved state comes from `App.addDocumentObserver`, so it is accurate for
edits made anywhere: the command line, a toolbar, or a macro.

## Messages

The engine emits typed messages, never rendered text. A renderer decides how
they look.

| Kind | |
|---|---|
| `prompt` | the open getter, its prompt and its options |
| `live` | the command being built, rewritten in place |
| `result` | it ran; carries the replay text, what was picked, and what was typed |
| `error` | it did not |
| `info` | chatter, optionally carrying a role: `head`, `value`, `ok`, `warn`, `bad`, `quiet` |

**Roles travel, colours do not.** The dock resolves a role to a colour, the
terminal to ANSI. Neither hard-codes the other's palette.

## Exit codes

`fccli` separates "wrong" from "not now".

| | |
|---|---|
| 0 | done |
| 1 | the command was rejected — a fault, reason on stderr |
| 2 | usage |
| 3 | no running instance, or it went away |
| 4 | several instances, pass `--pid` |
| 75 | busy — a dialog is open or someone holds the floor |

75 is `EX_TEMPFAIL`, deliberately far from 1, so `if ! fccli exec ...` does
not read a busy session as a broken command. Nothing is written to stderr
for a busy result, because nothing went wrong.

## Streams

- **stdout** carries the answer — results, and the text of a verb whose whole
  output is text.
- **stderr** carries failures and progress. `-v` adds the running echo.
- A one-shot **answers, it does not narrate.**

## The declarative surface

A verb and its steps are data. Everything below is read by the engine, the
completer, the highlighter, `man`, the socket and `check` — declared once,
honoured everywhere.

### Verb

| | |
|---|---|
| `name`, `aliases` | what it is called |
| `steps` | what it asks for, in the order it reads |
| `emit` | what it does |
| `creates` | the document type it produces, so `check` can say so |
| `gui_command` | the QAction it corresponds to |
| `transactional` | wrap it in an undo step (default true) |
| `record` | put it in history (default true) |

### Step

| | |
|---|---|
| `id`, `kind`, `prompt` | what it is, and what it asks |
| `optional` | bare Enter skips it |
| `default` | what it takes when skipped |
| `repeat`, `min_count` | takes values until Enter, at least this many |
| `unit` | how a quantity is echoed and what a bare number means |
| `choices` | a closed set, offered on Tab |
| `options` | inline keywords accepted alongside the value |
| `completes` | where else candidates come from: `verbs`, `objects`, `aliases`, `schemas`, `domains` |
| `raw` | take the rest of the line verbatim, not one token |
| `prompt_order` | where it sits when asked for; points default last |

## The verbs written by hand

Everything else is generated. These exist because they pick points, manage
documents, or read better than what a machine would derive.

| | |
|---|---|
| Drawing | `line` `polyline` `circle` `box` `point` `move` |
| Documents | `new` `open` `save` `close` `quit` |
| Editing | `undo` `redo` `delete` |
| Looking | `zoom` `screenshot` |
| Asking | `man` `check` `commands` `units` `use` |
| The session | `history` `alias` `unalias` `clear` |

## Naming

- A verb is a **lowercase word**, an underscore only where a type name forced
  one (`partdesign_box`).
- An alias is short and unclaimed. The bare-key shortcuts FreeCAD ships
  are a seed alias file, not a collision.
- A patch is keyed by **namespace** — a type module or an addon identity.
