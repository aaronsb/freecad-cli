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

Spike. Six verbs, one grammar, one event filter. See [SPIKE.md](SPIKE.md)
for what is proven and what is still open.

## Install

FreeCAD 1.0+ (developed against 1.1.3, PySide6).

**Addon Manager** — add this repository as a custom addon source:
`https://github.com/aaronsb/freecad-cli`

**Manually** — clone into FreeCAD's `Mod` directory:

```bash
git clone https://github.com/aaronsb/freecad-cli \
  ~/.local/share/FreeCAD/Mod/freecad-cli
```

Restart FreeCAD. The dock appears at the bottom; `Ctrl+\`` toggles it.

## Using it

| | |
|---|---|
| `line` `polyline` `circle` `box` `move` `point` | the seed verbs |
| `l` `pl` `ci` `bx` `mv` `pt` | aliases |
| `pol` + Enter | prefix-unique execution, no Tab needed |
| Tab / Shift+Tab | cycle completions |
| ↑ ↓ | history, in parameterized form |
| → | accept the ghost suggestion |
| Ctrl+R, Ctrl+A/E/K/U/W | readline editing (off by default; Ctrl+A is Select All in FreeCAD) |
| Enter on an empty line | finish a repeating step |
| Esc / Ctrl+C | cancel |

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
- **pick** — `snapper` uses `Gui.Snapper.getPoint` and gets FreeCAD's
  snapping; `raw` uses Coin3D callbacks directly and gets no Draft toolbar.

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

## Tests

```bash
QT_QPA_PLATFORM=offscreen python3 tests/test_spike.py
```

Runs offscreen without a FreeCAD GUI.

## License

MIT
