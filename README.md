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

### man

![The manual page for a generated verb](docs/images/man.png)

`man` lists every command; `man <name>` describes one. `help` is an alias.
Nobody wrote that page — it is generated from FreeCAD's own property
documentation, so every verb has one.

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
make check      # compile, version-check, test
make descriptor # regenerate fccli/descriptor.json
make screenshot # recapture docs/images
make bump PART=minor
make release    # stamp the commit, tag, push, cut a GitHub release
```

`make check` runs offscreen and needs no FreeCAD GUI.

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
