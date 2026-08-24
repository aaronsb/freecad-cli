# Adding command-line support to an addon

Your addon already works. Every command it registers became a verb the
moment the command line loaded — no cooperation required, nothing to
declare. This is about the difference between *reachable* and *good*.

## What you already have

Register a command the normal way and it is there:

```
> curved_array
```

The name comes from the command's menu label, the description from its
tooltip, and it lands in a domain named after your module, so `use
curvedshapes` narrows Tab to your commands. Running it does exactly what
clicking the toolbar button does — including opening a Task panel, if that
is what your command does.

That is tier 0, and for a command whose whole interface is a dialog it may
be all you want.

## What you might be missing

Two tiers sit above it, and whether you get them for free depends on how
your objects are built.

**If your objects are real registered types** — you called
`doc.addObject("YourMod::Thing")` and `YourMod::Thing` is a C++ type or a
registered Python type — you already have tier 1. The factory found it,
read its properties, and built a verb with a step per property:

```
> thing <Tab>
Width  Height  Angle  Style
```

Skip to [Patching a generated verb](#patching-a-generated-verb).

**If your objects are `Part::FeaturePython` with a proxy** — which is most
Python addons — you have tier 0 and nothing else. FreeCAD's type registry
never sees a `YourMod::Thing`, so there is nothing to generate from. You
need to [declare the verbs](#declaring-verbs).

Check which you are:

```
> commands yourmod
```

If the list is only your command names, you are the second case.

## Where a patch lives

Three places, each overriding the one before:

```
fccli/patches/*.py                     shipped with the command line
<Mod>/<your-addon>/fccli_patch.py      shipped by you
~/.local/share/FreeCAD/fccli/patches/  written by whoever installed it
```

**Drop `fccli_patch.py` in your addon directory and it is found.** No
registration, no import hook, no dependency on this addon being installed —
if the command line is not there, the file is simply never read.

A patch exports one name:

```python
PATCH = {
    "key": "YourAddon",     # optional; the directory name is used otherwise
    "types": {...},         # retune verbs the factory generated
    "verbs": {...},         # declare ones it could not
}
```

## Declaring verbs

For a `FeaturePython` addon, write the verb out. The example below is real —
`examples/curvedshapes_fccli_patch.py` in this repository, against an addon
that ships no support of its own.

```python
import FreeCAD as App


def make_curved_array(values):
    import CurvedShapes
    obj = CurvedShapes.makeCurvedArray(
        Base=values["base"][0],
        Hullcurves=values.get("hull") or [],
        Items=int(values.get("items") or 4),
        Twist=float(values.get("twist") or 0.0),
        Surface=values["_flags"].get("Surface", False),
    )
    App.ActiveDocument.recompute()
    return obj


PATCH = {
    "key": "CurvedShapes",
    "verbs": {
        "curved_array": {
            "aliases": ["carr"],
            "doc": "Array a shape along one or more hull curves.",
            "gui_command": "CurvedArray",
            "steps": [
                {"id": "base", "kind": "selection", "prompt": "Base shape"},
                {"id": "hull", "kind": "selection", "prompt": "Hull curves",
                 "optional": True},
                {"id": "items", "kind": "quantity", "prompt": "Items",
                 "unit": "", "default": 4},
                {"id": "twist", "kind": "quantity", "prompt": "Twist",
                 "unit": "deg", "optional": True,
                 "options": ["Surface", "Solid"]},
            ],
            "emit": make_curved_array,
        },
    },
}
```

`emit` receives one dict: a key per step, plus `_flags` for the inline
options that were given and `_engine` if you need the session. Return the
object you made, or `None`.

### What a step can say

| | |
|---|---|
| `id`, `kind`, `prompt` | required. `kind` is `point`, `quantity`, `selection`, `choice`, `text` or `path` |
| `optional` | bare Enter skips it |
| `default` | what it takes when skipped |
| `unit` | `mm`, `deg`, or `""` for a plain count. Decides what a bare number means and how the value echoes back |
| `choices` | a closed set, offered on Tab |
| `options` | inline keywords, arriving in `_flags` |
| `repeat`, `min_count` | takes values until Enter |
| `completes` | extra candidates: `verbs`, `objects`, `aliases`, `schemas`, `domains` |
| `prompt_order` | where it sits when asked for. Points default last |

Declare the units honestly and everything downstream follows: `12` means
twelve of whatever the user reads in, Tab appends their unit, and the echo
renders in their schema. Declaring `deg` is what makes an angle colour as an
angle.

## Patching a generated verb

If the factory already built your verb, you are correcting it rather than
writing it. A generated verb is alphabetical, everything optional, and every
property included — functional and shapeless.

```python
PATCH = {
    "key": "YourMod",
    "types": {
        "YourMod::Thing": {
            "verb": "thing", "aliases": ["th"],
            "steps": ["Width", "Height"],      # order, and required
            "options": ["Mirrored"],           # inline keyword
            "hide": ["InternalTolerance"],     # never ask
            "point": {"at": ["Placement"]},    # one getter, not three numbers
            "strict": True,                    # nothing beyond what is listed
            "doc": "A thing, from a width and a height.",
        },
        "YourMod::Legacy": {"skip": True},     # not worth a verb
    },
}
```

Order the steps the way a person would give them, promote booleans to
`options`, and hide what nobody types. `strict` drops everything you did not
name; without it, unnamed properties stay available after the ones you
ordered.

## Points last

A step that takes a point is asked for last unless you say otherwise. That
is deliberate: everything typeable comes first and the click is what commits
the command, so this works —

```
> thing 40 20
Place it:                ← click
> ⏎                      ← repeat, waiting for another click
```

If your verb genuinely needs a point first, say `"prompt_order": 0` on it.

## Testing it

Nothing here needs a GUI:

```python
from fccli.grammar import Registry
from fccli.factory import register_all
from fccli.patches import PatchSet

registry = Registry()
register_all(registry, tier0=False, patches=PatchSet())
verb = registry.get("curved_array")
assert [s.id for s in verb.steps] == ["base", "hull", "items", "twist"]
```

And from a terminal, against a running FreeCAD:

```bash
$ fccli check 'curved_array Box Wire 6'
curved_array -- Array a shape along one or more hull curves.
  would run:  curved_array Box Wire 6
  nothing was run.
```

`check` runs your verb through the same parse the engine uses and stops
before `emit`. It is the fastest way to see whether your steps read the way
you meant.

## What not to do

**Do not import this addon.** A patch is data plus callables; it is read by
whatever finds it. Importing `fccli` would make your addon depend on it.

**Do not declare a verb the factory already built** unless you mean to
replace it. Patch the type instead — you keep the property documentation,
the units and the enum choices that were harvested for free.

**Do not take a name someone else owns.** Hand-written verbs win, and a
family or generated verb keeps a qualified name instead. Check with `man
<name>` before choosing.

## See also

- [conventions.md](conventions.md) — every rule the command line follows
- [shell.md](shell.md) — the socket, for driving a session from outside
- `examples/curvedshapes_fccli_patch.py` — the whole worked example
