# FreeCAD CLI

A command line for FreeCAD.

![The command line docked above the 3D view](docs/images/hero.png)

Type a verb, then feed each step a typed coordinate, a viewport pick, or an
option keyword — through the same door, in any order. Every value records its
typed form as it lands, so a command driven half by mouse replays from
history as text.

## How it feels

![A command in progress, with its options and live validation](docs/images/midcommand.png)

Three things are happening in that one line:

- The prompt names the current getter and its inline options —
  `Next point [Close/Undo]:`
- The command builds up on **one** accumulating line, not one line per step
- Input is validated as it is typed. `@0,40,` parses; `zz` does not, and
  reddens before Enter

Values echo back canonical: `3/8in` becomes `9.525mm`, and a relative point
resolves to absolute. What you see is what replays.

## Install

FreeCAD 1.0+ (developed against 1.1.3, PySide6).

**Addon Manager** — add this repository as a custom addon source:
`https://github.com/aaronsb/freecad-cli`

**Manually** — clone into FreeCAD's `Mod` directory. FreeCAD 1.1 versions
that path:

```bash
git clone https://github.com/aaronsb/freecad-cli \
  ~/.local/share/FreeCAD/v1-1/Mod/freecad-cli
```

Restart FreeCAD. The command line appears as a full-width strip between the
toolbars and the 3D view. `` Ctrl+` `` toggles it, and it is listed under
**View → Panels → Command Line** like any other dock.

## Using it

| | |
|---|---|
| `pol` + Enter | prefix-unique execution, no Tab needed |
| Tab / Shift+Tab | cycle completions |
| ↑ ↓ | history, in its assembled form |
| → | accept the ghost suggestion |
| Enter on an empty line | finish a repeating step |
| Esc / Ctrl+C | cancel |
| trailing `!` | force past a refusal — `close!` |
| `check <command>` | validate it without running it (`whatif`, `ck`) |

### Units

![The same command under two schemas](docs/images/units.png)

Display follows FreeCAD's own unit schema, and every conversion goes through
FreeCAD's API — `getUserPreferred` names the unit, `getValueAs` converts.
There is no mapping table here.

```
> units imperialbuilding
> cylinder 12 40          →  cylinder 1' 3'4"
> box 0,0,0 3/8in 1ft 25.4mm  →  box 0,0,0 3/8" 1' 1"
```

A bare number takes the schema's unit rather than internal millimetres, so
`12` means twelve of whatever you read in. Tab on a bare number appends that
unit, and `units` says what it is.

Schema rendering is meant for reading, not re-parsing: it rounds, and its
compound imperial form (`3" + 7/8"`) does not parse back. Since the echoed
line is also what Up recalls, every rendering is round-tripped before use
and falls back to a precise conversion when it fails.

### Coordinates

```
10,20,30      absolute
10,20         z from the previous point
@10,0,0       relative           (AutoCAD spelling)
r10,0,0       relative, alternate spelling
100<45        polar, in the XY plane
3/8in,1in,0   any unit FreeCAD's parser accepts
```

### Shell builtins

The GUI equivalents route through modal dialogs — Save on an unnamed
document opens a file chooser, closing a modified one asks for confirmation.
These take their arguments inline instead:

```
> save ~/parts/bracket.FCStd     saves there, no dialog
> open ~/parts/bracket.FCStd     new bracket     close     close!
> alias b box                    unalias b       history   clear
> undo    redo    fit    delete  quit    quit!
> units imperialbuilding         switch schema; 9.525mm reads as 3/8"
> check box 0,0,0 40 30 20       validate without running
```

`check` resolves and parses a command through the same code path the engine
uses, then stops before emitting — so what it accepts is what would actually
run, rather than a second implementation that can drift:

```
> check box 0,0,0 40 zz 20
  box -- Create a box from a corner and three dimensions.
    rejected: 'zz' is not a number or quantity

> check cylinder 12
  cylinder -- Create a cylinder from a radius and a height.
    incomplete -- still wants: The height of the cylinder
    valid so far, nothing was run.

> check cylinder 12 40
    would run:  cylinder 12.00mm 40.00mm
    would create: Part::Cylinder
    nothing was run.
```

`close` and `quit` refuse when there is unsaved work rather than raising a
modal; `!` discards. Unsaved state is tracked through
`App.addDocumentObserver`, so it is accurate for edits made anywhere — the
command line, a toolbar, a macro.

### check

![check output, coloured by role](docs/images/check.png)

### man

![The manual page for a generated verb](docs/images/man.png)

`man` lists every command; `man <name>` describes one. `help` is an alias.
Nobody wrote that page — it is generated from FreeCAD's own property
documentation, so every verb has one.

## From a terminal

`bin/fccli` talks to a running FreeCAD over a unix socket. It is not a copy
of the command language reached over a wire — the server subscribes to the
same message bus the dock does and calls the same engine, so there is one
registry, one document, and one prompt. Start a command from a terminal and
the dock's prompt changes.

Nothing in the client imports FreeCAD. It is standard library only, so it
runs from any terminal or virtualenv.

A whole session can run without touching the application window:

```bash
$ fccli start -i                  # from nothing running to a prompt
started FreeCAD, pid 3074336
attached to FreeCAD 3074336.
  detach (or Ctrl+D) leaves this session running.  quit! shuts FreeCAD down.

> box 0,0,0 40 30 20
= box 0,0,0 40.00mm 30.00mm 20.00mm
> polyline
Start of polyline: 0,0,50
Next point [Close/Undo]: 40,0,50
Next point [Close/Undo]: close
= polyline 0,0,50 40,0,50 close
> detach
detached. FreeCAD 3074336 is still running; fccli attach to come back.
```

The prompt is the engine's own, so a getter's options show in the terminal
the way they show in the dock. Tab completions come from the server —
verb names, the open getter's options, the schema's unit on a bare
number — so there is one implementation of what completes, not two.

`detach` ends the connection and leaves the session, its documents and its
undo stack untouched. `quit!` shuts FreeCAD down.

Scripted instead of interactive:

```bash
$ fccli start --headless
$ fccli exec 'box 0,0,0 40 30 20'
= box 0,0,0 40.00mm 30.00mm 20.00mm
$ fccli exec 'save ~/parts/bracket.FCStd'
$ fccli exec 'quit!'
```

With one FreeCAD running, every command attaches to it; `--pid` is only
needed when several are. Bare `fccli` prints the usage and says what it can
reach.

```bash
$ fccli ls
pid 3068224   idle, 1 client(s), floor free
    bracket                1 objects  /tmp/bracket.FCStd
  * scratch                1 objects  (never saved) [unsaved]

$ fccli exec 'box 0,0,0 40 30 20'
= box 0,0,0 40.00mm 30.00mm 20.00mm

$ fccli check 'cylinder 12 40'      # never mutates
$ fccli history -f                  # follow, live
$ echo 'circle 0,0,0 20' | fccli    # stdin is a script
$ fccli --json docs                 # what an agent reads
```

A one-shot answers rather than narrating: stdout carries the result, stderr
the reason a command failed, and `-v` shows the running echo if you want it.

**Exit codes separate "wrong" from "not now".** A rejected command is a
fault — exit 1, reason on stderr. A busy session is ordinary, since someone
using FreeCAD has a dialog open a good fraction of the time — exit **75**
(`EX_TEMPFAIL`), nothing on stderr, deliberately far from 1 so
`if ! fccli exec ...` does not read it as a broken command. `--wait` queues
instead.

Several FreeCADs each get their own socket, and `ls` lists what each has
open so you can tell them apart. See [docs/shell.md](docs/shell.md) for the
design, including the floor and the shared buffer that follow.

## Where the verbs come from

FreeCAD has no Discovery API. It has a **command registry** that knows names,
labels and grouping but carries no parameters, and a **type registry** that
carries typed, documented properties but says nothing about naming or
invocation. `tools/generate_descriptor.py` harvests both into
`fccli/descriptor.json`, and the factory turns that into three tiers:

| Tier | Count | Source |
|---|---|---|
| 0 | ~1020 | every registered command, as a zero-step verb that runs it |
| 1 | ~206 | every parametric type, with steps from its own properties |
| 2 | hand-written + patched | point-picking verbs, ordering, inline options |

Linking a command to the type it builds cannot be done reliably by machine —
name matching puts `BIM_Box` on `Part::Box`, and tracing the call graph puts
`BIM_Tutorial` on `Part::Extrusion`. The design does not need it to: **a type
names and parameterizes its own verb**, so tier 1 stands on the type registry
alone. Command metadata is attached only where the evidence is real.

### What it can drive

![A twisted tower built from 84 typed commands](docs/images/tower.png)

Eighty-four commands, 1.8 seconds, no mouse. Fourteen square levels each
rotated 14°, a circle inscribed at each, 52 stringers connecting corners
level to level, and a plinth dimensioned in inches.

### Patches

A generated verb is functional and generic. A patch makes it feel like the
tool it represents:

```python
PATCH = {
    "key": "Part",
    "types": {
        "Part::Cylinder": {
            "verb": "cylinder", "aliases": ["cyl"],
            "steps": ["Radius", "Height"],   # order, and required
            "options": ["Angle"],            # inline keyword
            "hide": ["FirstAngle", "SecondAngle"],
            "strict": True,
        },
    },
}
```

Patches are keyed by namespace — a type module (`Part`) or an addon identity
(`CurvedShapes`) — and discovered from three roots, each overriding the last:

```
fccli/patches/*.py                     shipped here
<Mod>/<addon>/fccli_patch.py           shipped by the addon itself
~/.local/share/FreeCAD/fccli/patches/  written by you
```

An addon that drops an `fccli_patch.py` is picked up with no registration.
Its commands already work through tier 0; the patch upgrades them.

### Hand-written verbs

Some things want the viewport, not a property sheet. `line`, `polyline`,
`circle`, `move` and `point` are written by hand so they can pick:

```python
REGISTRY.add(Verb(
    name="polyline", aliases=["pl", "pline"],
    steps=[
        Step("start", POINT, "Start of polyline"),
        Step("next", POINT, "Next point", repeat=True,
             options=[Option("Close", "close the wire", _close),
                      Option("Undo", "drop the last point", _undo_last)]),
    ],
    emit=_emit_polyline,
))
```

The completer, the highlighter, the prompt, `man`, and history replay all
follow from the descriptor.

## Architecture

```
descriptor.json  +  patches  +  hand-written verbs
        │
        ▼
   verb registry
        │
        ▼
command engine  ── in-process; owns the picker, document, key filter
        │
        ▼
typed message stream   { prompt | live | result | error }
        │
   ┌────┼────────────────┬──────────────────┐
   ▼                     ▼                  ▼
Qt widget            ANSI adapter        MCP server
(this repo)          (not built)         (not built)
```

The engine talks to the widget over a stream of typed messages rather than
method calls, so the same stream can feed a socket or an agent. That is what
would let a human and an agent share one transcript instead of talking past
each other through write-only RPC.

The key filter is the load-bearing piece: 195 of FreeCAD's 940 default
shortcuts are unmodified keys, so claiming bare printables collides on
purpose. A focus guard keeps real editors' keys, and digits route by step —
`1`–`6` stay the standard views while nothing is running, and become input
once a getter is open.

## Development

```bash
make            # list the targets
make install    # symlink into FreeCAD's Mod directory
make check      # compile, version-check, test  (offscreen, no GUI)
make bvt        # drive a real FreeCAD GUI end to end, unattended
make socket     # drive a real FreeCAD from outside, over the socket
make check-all  # all three
make descriptor # regenerate fccli/descriptor.json
make screenshot # recapture docs/images
make bump PART=minor
make release    # stamp the commit, tag, push, cut a GitHub release
```

`make check` covers the grammar offscreen. `make bvt` covers what only a
running GUI can: the dock, the application-level key filter, the picker,
the factory loading at startup, undo through real transactions, and the
shutdown path. It runs under its own Xvfb display, drives everything
through the command line, and never touches a dialog — which is only
possible because every document verb takes its arguments inline. So it runs
unattended, and a missing result file is reported as a failure rather than
mistaken for success.

The version prints in the banner as `0.2.0+c4113ff (2026-08-23)` — semantic
version, the commit it was built from, and that commit's date. Running from
a checkout the commit is read live from git and marked `-dirty` when the tree
has changes; a released copy carries a stamped `fccli/_build.py`.

## Status

Working, and in use. [CHANGELOG.md](CHANGELOG.md) tracks releases.
[FINDINGS.md](FINDINGS.md) records what was learned about FreeCAD's
internals along the way, including several things not documented anywhere
obvious.

## License

MIT
