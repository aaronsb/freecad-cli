---
status: Accepted
date: 2026-08-26
deciders:
  - aaronsb
  - claude
related:
  - ADR-201
  - ADR-203
  - ADR-303
  - ADR-100
---

# ADR-204: An inline option carries its value as name=value

## Context

A command file's `type:` block can name properties as inline options
rather than as steps:

```yaml
type:
  of: Part::Cylinder
  steps: [Radius, Height]
  options: [Angle]
```

`patches.apply` built each one with `_setter(name)`, which was
character-for-character `_flag(name)`:

```python
def _setter(name):
    def action(engine):
        engine.flags[name] = True
        return False
    return action
```

`_emit_type` then wrote that: `True if got is None else got`. So typing
the option set the property to `True`.

For a boolean that is right, and it is how the 277 `App::PropertyBool`
options reach an object. **Not one of the 105 options the tree declares
is a boolean.** They are 72 quantities, 30 enumerations and two link-subs:

```
$ cylinder 10
  The height of the cylinder  ·  also angle:
$ angle
$ 40
  = cylinder 10.00mm angle 40.00mm
$ describe Cylinder
  Angle  1.00 deg
```

`Angle = True` is one degree. FreeCAD's own default is 360. So the option
did not merely fail to take a value — it replaced a sensible default with
a nonsensical one, silently, and the cylinder was a one-degree sliver. On
an enumeration `True` selects index 1. On `Part::RuledSurface`'s `Curve1`
the write raises, which ADR-203 now reports rather than swallows.

ADR-303 renders these apart from the step's own prompt, and worded it
`also angle` rather than `also angle=` deliberately: `angle=180` did not
work, and advertising a syntax that does not is the fault GH #71 was.
`also angle` is what the step took. It is not what anybody wants it to
take.

So the option needs a grammar for its value, and there were two candidates
already in the building.

## Decision

**An inline option carries its value as one `name=value` token, and the
bare keyword sets only a boolean.**

- `grammar.assignment()` reads one token as a name, an equals, and the
  rest. Anchored to the whole token, unlike `panels.ASSIGNMENT`, which
  cuts several pairs out of one raw line and has to find its split points
  inside prose.
- `Option.takes` is the value the option carries, **as the step it would
  have been**. `patches.apply` already pops that step out of the verb to
  make room for the option, and had been discarding it; it becomes
  `takes`. A boolean has none — flags never become steps — so `takes` is
  None and the bare keyword remains the whole of setting one.
- `Engine._read_value` is the one reading of a typed value. A step's own
  value and an option's go through it, so `angle=180` at a cylinder is the
  same reading as `180` at an angle step: the same unit, the same schema,
  the same refusal of a fraction at a count (ADR-203). Two copies would
  drift the moment one of them learned something.
- The value is recorded under the **property's own name**, which is the id
  of the step the option was built from. `_emit_type` writes it with
  everything else and nothing there has to know an option was involved.
- **An assignment names its own target, so it has no position on the
  line**, and `_start` reads every assignment out of the line before the
  positional walk. It has to: `_accept` runs the verb the moment the last
  step is answered, so a trailing `angle=180` arrived after the emit it
  was for and was dropped without a word.
- **The bare keyword at a non-boolean is refused**, naming the syntax and
  the shape of the value: `Angle takes a value -- try angle=<number>`. A
  refused token stops the line, which is ADR-201's rule about a verb name
  mid-line applied to a value, the way ADR-203 applied it to a fraction.
- **`True` at a non-boolean is refused at the write too**, for a flag that
  reached `emit` any other way: `Angle takes a value -- angle=<value>`.
  Two doors, one rule, the same shape ADR-203 gave the integer coercion.
- **A name that is nobody's option is left to the step.** `label=Wall` at
  a text step is that step's value. Reading every `=` as a failed
  assignment is the fault GH #71 was on the panel side.
- **The prompt says `also angle=`**, and completion offers `angle=`. The
  step advertises what it takes, which is ADR-303's rule; the wording
  changes because what it takes has changed.

## Consequences

### Positive

- 104 declared options over 72 quantities, 30 enumerations and two
  link-subs stop writing `True` to the property they name. `cylinder 10 20
  angle=180` reads back `Angle 180.00 deg` rather than `1.00 deg`.
- The two kinds of step read the same. A panel field is `xposition=25 mm`
  and a generated option is `angle=180`, and `panels.OFFER` has been
  teaching the first of those all along.
- The refusal is the syntax. Somebody who types `angle` is told what to
  type instead, at the step, rather than getting a cylinder that is 1/360
  of the one they asked for.
- `_setter` is gone. It said something `_flag` already said, and the two
  names were what let a settable property and a boolean share one action
  without anybody noticing.
- The highlighter reads the assignment too, so `angle=zz` underlines the
  `zz` rather than the whole token, and `angle=180` is not red.

### Negative

- **An option's value cannot contain a space when it is given inline.**
  The line is split on whitespace before the assignments are read, so
  `angle=3/4 in` inline arrives as two tokens. At a prompt the whole line
  is one answer and it lands, which is where `3/4 in` is typed anyway. A
  panel field does better because its step is raw and takes the whole
  line; a generated verb's steps are not.
- **A recalled line puts the assignments first.** They are read before the
  positional walk, so `cylinder 10 20 angle=180` replays as `cylinder
  angle=180.00° 10.00mm 20.00mm`. It runs to the same object — arguments
  are matched by kind, not by position — but it is not the order it was
  typed in, and history says elsewhere that it is.
- A line that used to exit 0 with a one-degree cylinder now reports an
  error. That is the same trade ADR-203 made: the alternative is the
  silence this record exists to end.

### Neutral

- `Part::Helix`'s declared `Style` is the 105th, and it names a property
  `Part::Helix` does not have. The tree lint already reports it (A2, "the
  line does nothing"); it is a tree fault and not this grammar's.
- An addon that declares a step's options by hand (`patches._build_step`)
  still gets bare keywords. Nothing declares a value-carrying option that
  way yet, and the field is there when something does.
- A token that names no option and reaches no step is still dropped
  without a word. That is GH #77, and it is what made the trailing
  `angle=180` fail silently rather than loudly — the pre-scan routes
  around it rather than curing it.

## Alternatives Considered

- **`angle 180` — the option keyword followed by its value.** AutoCAD's
  shape, and the issue's other candidate. Rejected on three counts. It
  needs the option to claim the next token, which is a pending-option
  state the engine would have to carry across cancel, restart, refusal
  and picking — four paths that exist and would each need to know about
  it. It is ambiguous against the positional walk: a bare number after the
  keyword looks exactly like the step's own value, so `cylinder 10 angle
  180` and `cylinder 10 180` differ at a token a reader cannot tell apart.
  And `=` is already in the building for this act.
- **`Diameter` on `circle` as the precedent.** It is not this. It modifies
  the step's own value rather than taking one of its own, so it is an
  alternative to answering rather than a property assignment. ADR-303
  already renders those two populations apart — `[Close/Undo]` against
  `also angle=` — and giving them one syntax would put them back together.
- **`mirrored=false` for booleans.** One spelling per option is worth
  more than the convenience. The bare keyword is what a flag is, and `=`
  at one is refused naming the bare form.
- **Refuse the bare keyword and leave the value grammar for later.** The
  half the issue said could land ahead of the decision. It cures the
  one-degree cylinder and leaves 104 options unusable, which is a worse
  place to stop than either end.
- **Let the option's action take the value** — `action(engine, value)`.
  Every action in the program has the one-argument signature, including
  `done`, `cancel`, `Close` and `Undo`, and widening it for the two that
  need it would touch all of them. The engine reads `Option.takes` and
  records the value itself; an option that carries one reaches no action
  at all.
