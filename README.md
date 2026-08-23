# FreeCAD CLI

A Rhino-style command line for FreeCAD.

A dockable terminal-masquerade widget that drives a declarative command
grammar. Type a verb, then feed each step a typed coordinate, a viewport
pick, or an option keyword — through the same door, in any order.

```
> polyline
Start of polyline: 0,0,0
Next point [Close/Undo]: @100,0,0          ← typed, relative
Next point [Close/Undo]:                   ← clicked in the viewport
Next point [Close/Undo]: close
= polyline 0,0,0 @100,0,0 100,73.2,0 close
```

That last line is the point: a command driven partly by mouse replays from
history as text. It is also what an agent reads, and what a macro recorder
would write.

## Status

Working, and in use. ~1200 commands: a dozen hand-written verbs with
viewport picking, ~200 generated from FreeCAD's type registry, and every
registered command as a launcher.

[CHANGELOG.md](CHANGELOG.md) tracks releases. [FINDINGS.md](FINDINGS.md)
records what was learned about FreeCAD's internals along the way, including
several things that are not documented anywhere obvious.

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

A symlink works too, which is the better dev loop:

```bash
ln -s ~/src/freecad-cli ~/.local/share/FreeCAD/v1-1/Mod/freecad-cli
```

Restart FreeCAD. The command line appears as a full-width strip between the
toolbars and the 3D view. `Ctrl+\`` toggles it, and it is listed under
**View → Panels → Command Line** like any other dock.

## Using it

| | |
|---|---|
| `line` `polyline` `circle` `box` `move` `point` | the drawing verbs |
| `save` `open` `new` `close` `quit` `clear` `undo` `redo` `fit` `delete` `help` | shell builtins |
| ~200 generated verbs | `cylinder` `sphere` `torus` `pad` `pocket` … from FreeCAD's type registry |
| ~1000 command verbs | every registered command, by its menu label |
| `l` `pl` `ci` `bx` `mv` `pt` `w` `cls` `zf` `?` | aliases |
| `close!` | a trailing `!` forces past a refusal |
| `pol` + Enter | prefix-unique execution, no Tab needed |
| Tab / Shift+Tab | cycle completions |
| ↑ ↓ | history, in parameterized form |
| → | accept the ghost suggestion |
| Ctrl+R, Ctrl+A/E/K/U/W | readline editing (off by default; Ctrl+A is Select All in FreeCAD) |
| Enter on an empty line | finish a repeating step |
| Esc / Ctrl+C | cancel |

### Shell builtins

The GUI equivalents route through modal dialogs — Save on an unnamed
document opens a file chooser, closing a modified one asks for confirmation.
A command line that has already been given the path should not stop to ask
again, so these take their arguments inline:

```
> save ~/parts/bracket.FCStd     saves there, no dialog
> save                           saves in place
> open ~/parts/bracket.FCStd
> new bracket
> close                          refuses if there are unsaved changes
> close!                         discards them
> help                           lists the verbs
> help polyline                  describes one
```

`close` refuses rather than prompting, because FreeCAD exposes no
unsaved-changes flag to Python — `isSaved()` reports whether the document
has a file at all and stays true after every later edit — so the addon
tracks its own edits and turns the modal into a refusal you can override.

### Coordinates

```
10,20,30      absolute
10,20         z from the previous point
@10,0,0       relative           (AutoCAD spelling)
r10,0,0       relative           (Rhino spelling)
100<45        polar, in the XY plane
3/8in,1in,0   any unit FreeCAD's parser accepts
```

### The control strip

- **usurp keys** — route bare printable keys to the command line. Digits
  stay with FreeCAD while no getter is open, so `1`–`6` remain the standard
  views.
- **gui** — what a toolbar click does: `echo` logs it, `ghost` pre-fills the
  input line, `follow` opens the grammar instead of the Task panel, `off`
  disconnects.
- **pick** — `snap` (default) takes clicks through Coin3D and resolves them
  with `Gui.Snapper.snap()`: snapping and trackers, no UI of its own.
  `getpoint` uses `Gui.Snapper.getPoint()`, which also brings
  `Gui.draftToolBar` and opens Draft's Point dialog in the Tasks panel — a
  second input surface competing with the command line. `raw` is Coin3D
  alone, no snapping.
- **width** — `full` spans the window; `partial` hands the corners back to
  the left and right docks, so the row is shared and other docks can be
  dragged in beside the command line. Qt toolbars live in their own band
  above the dock area and cannot join the row.

Drag the dock's lower edge to resize it. The height and the width mode
persist under `BaseApp/Preferences/Mod/fccli`.

## Where the verbs come from

Three tiers, in rising order of how much anyone had to write by hand:

| Tier | Count | Source |
|---|---|---|
| 0 | ~1020 | every registered command, as a zero-step verb that runs it |
| 1 | ~206 | every parametric type, with steps from its own properties |
| 2 | 7 + hand-written | tier 1 after a patch: ordering, options, aliases |

FreeCAD has no Discovery API. It has a **command registry** that knows
names, labels and grouping but carries no parameters, and a **type
registry** that carries typed, documented properties but says nothing about
naming or invocation. `tools/generate_descriptor.py` harvests both and
writes `fccli/descriptor.json`.

Linking a command to the type it builds cannot be done reliably by machine —
name matching puts `BIM_Box` on `Part::Box`, and tracing the call graph puts
`BIM_Tutorial` on `Part::Extrusion`. The design does not need it to: **a
type names and parameterizes its own verb**, so tier 1 stands on the type
registry alone. Command metadata is a garnish attached where the evidence is
real (a hand-written override, or a type named in the command's own class
body).

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

Patches are keyed by namespace — a type module (`Part`) or an addon
identity (`CurvedShapes`) — and are discovered from three roots, each
overriding the last:

```
fccli/patches/*.py                     shipped here
<Mod>/<addon>/fccli_patch.py           shipped by the addon itself
~/.local/share/FreeCAD/fccli/patches/  written by you
```

An addon that drops an `fccli_patch.py` is picked up with no registration
step. Its commands already work generically through tier 0; the patch
upgrades them. Nothing in this repo changes to support a new addon.

### Regenerating

```bash
python3 tools/generate_descriptor.py
```

Boots FreeCAD twice — headless for types, under Xvfb for commands — scans
every `Mod` tree for what each command builds, and prints a coverage report.
Instantiating a type can abort FreeCAD from C++, so the type harvester
claims each type before touching it and the driver restarts past whatever
killed it.

## How it fits together

```
grammar registry (verb descriptors, fccli/verbs.py)
        │
        ▼
command engine  ── in-process; owns the picker, the document, the filter
        │
        ▼
typed message stream   { prompt | options | echo | result | error }
        │
   ┌────┼────────────────┬──────────────────┐
   ▼                     ▼                  ▼
Qt widget            ANSI adapter        MCP server
(this repo)          (not built)         (not built)
```

Verb descriptors are data, so one registry can feed the widget's contextual
completer, a generated MCP tool schema, and a headless scripting API. The
message stream is what makes a human and an agent share one transcript.

## Adding a verb

```python
from fccli.grammar import POINT, QUANTITY, Option, Step, Verb, REGISTRY

REGISTRY.add(Verb(
    name="cylinder", aliases=["cyl"], gui_command="Part_Cylinder",
    steps=[
        Step("base", POINT, "Base centre"),
        Step("radius", QUANTITY, "Radius",
             options=[Option("Diameter", "read as diameter", set_diameter)]),
        Step("height", QUANTITY, "Height"),
    ],
    emit=make_cylinder,
))
```

The completer, the highlighter, the prompt, and history replay all follow
from the descriptor.

## Development

```bash
make            # list the targets
make install    # symlink into FreeCAD's Mod directory
make check      # compile, version-check, test
make descriptor # regenerate fccli/descriptor.json
make bump PART=minor
make release    # stamp the commit, tag, push, cut a GitHub release
```

`make check` runs offscreen and needs no FreeCAD GUI.

The version prints in the banner as `0.2.0+dd069a6 (2026-08-23)` — semantic
version, the commit it was built from, and that commit's date. Running from
a checkout, the commit is read live from git and marked `-dirty` when the
tree has changes; a released copy carries a stamped `fccli/_build.py`
instead.

## License

MIT
