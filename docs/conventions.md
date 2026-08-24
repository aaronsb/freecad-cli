# Conventions

Every rule the command line follows, in one place. Each was decided once and
holds everywhere — in the dock, in the terminal, and in what an agent reads
over the socket.

## Grammar

| Rule | |
|---|---|
| First token is a **verb** | Everything after a space is an argument. |
| Trailing `!` **forces** | `close!`, `quit!` — past a refusal, never past an error. |
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

## Verbs

Four tiers, each only as hand-made as it needs to be.

| Tier | From |
|---|---|
| 0 | every registered command, as a launcher |
| families | a group FreeCAD spread apart, gathered under one name with a choice |
| 1 | every parametric type, with steps from its own properties |
| 2 | hand-written and patched |

**Nothing generated takes a name a hand-written verb owns.** The generated
one keeps a qualified name instead — `Part::Box` becomes `part_box` because
`box` is hand-written and can pick a corner.

**Where a derived verb reads worse than a curated one, curate.** `zoom` is
hand-written because it gathers commands across two name stems the family
splitter cannot join.

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

## Naming

- A verb is a **lowercase word**, an underscore only where a type name forced
  one (`partdesign_box`).
- An alias is short and unclaimed. The 195 bare-key shortcuts FreeCAD ships
  are a seed alias file, not a collision.
- A patch is keyed by **namespace** — a type module or an addon identity.
