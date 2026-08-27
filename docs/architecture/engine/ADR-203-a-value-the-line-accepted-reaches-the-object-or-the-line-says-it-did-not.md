---
status: Accepted
date: 2026-08-26
deciders:
  - aaronsb
  - claude
related:
  - ADR-201
  - ADR-202
  - ADR-100
---

# ADR-203: A value the line accepted reaches the object, or the line says it did not

## Context

A tier-1 verb is a type and its properties. `_emit_type` creates the
object and writes each collected value onto it:

```python
try:
    setattr(obj, p["name"], True if got is None else got)
except Exception:
    pass
```

Two things travel through that write, and both were broken in the same
place.

**A count is parsed as a float and FreeCAD's integer setter refuses one.**
`parse_quantity` hands back `Quantity.Value`, a double. FreeCAD's
`App::PropertyInteger` takes an int and raises `TypeError: type must be
int, dict or tuple, not float` for `4.0` where it accepts `4`. 86 scalar
parameters across the shipped descriptor are integer-typed —
`Occurrences` on both patterns, `Polygon` on the six prisms, `IsoCount`
and `ScrubCount` across TechDraw, `MaxDegree` on the lofts.

**The step asked for the count in millimetres.** `_step_from_param` gives
every quantity step a unit and defaults it to `mm`, because the harvest
writes no unit for a property FreeCAD gives no dimension. `parse_quantity`
appends the schema's preferred length to a bare number, so under
ImperialBuilding a typed `4` reached the write as 101.6 — a number no
rounding turns back into four instances. The grammar lint already counts
this class (GH #47, D5); the integer half is the half where it is fatal
rather than merely wrong.

**And the swallow made both invisible.** `linear_pattern 100 4` reported
`rc=0` and the object read back `Occurrences 2`, FreeCAD's default. Worse,
`additive_prism 6 10 20` read back `Polygon 6` and looked like a pass —
six is `Polygon`'s own default, so the readback agreed with the intent by
coincidence. A refused write and an accepted one were the same event.

What the swallow was hiding is not only counts. `offset 2` over a
selected box writes a list of objects to `Source`, an `App::PropertyLink`
that wants one object, and 82 generated verbs carry at least one
single-link selection step. That is GH #57's other half and ADR-202's
open question — "why those fourteen compute invalid" — and it was
unanswerable while the cause was swallowed and only the symptom reported.

## Decision

**A value the command line accepted is written, coerced where the
property counts, and every refusal is said out loud.**

- `properties.counts()` names the property types that hold a count rather
  than a measurement. `grammar.whole_number()` says what integer a value
  stands for, or None. One definition each, because the engine and the
  factory both ask and have to agree.
- A step over a counting property carries **no unit** and is marked
  `integral`. A bare number takes nothing from the schema, and the echo
  reads `4` rather than `4.00mm`, so the line replays as it was typed.
- A **fraction at a count is refused at the prompt**, not truncated at the
  write: `Occurrences counts -- 4.5 is not a whole number`. Half an
  instance is a typo, and rounding it would build something nobody asked
  for. Refusing at the step is what keeps an object from existing to carry
  the wrong number at all.
- **The line stops at a refused token.** Every step the factory generates
  is optional, so `_only_optional_left` found nothing outstanding and ran
  the command with the refused value simply absent — `linear_pattern 100
  4.5` reported the fraction and then built a pattern of two. `_feed_text`
  and `_accept` now answer whether the value landed, and `_start` stops
  the walk when it did not. This is ADR-201's rule about a verb name
  mid-line, applied to a value: what follows a refused token was answers
  to a command that is not going to run as typed.
- **A write FreeCAD refuses is an error on the bus**, naming the property
  and FreeCAD's own message. Every property is attempted and every refusal
  is reported together, so one that FreeCAD will not take costs only
  itself: `Offset: FreeCAD would not take Source: Type must be
  App.DocumentObject or None, not list -- the rest of the line landed`.
- The `RESULT` still goes out, and the object is not undone. That is
  ADR-202's reading and this is the same kind of statement one layer
  further in: the line ran, the object exists, and the error beside it
  says what is not on it.

## Consequences

### Positive

- 86 integer parameters across 49 types stop dropping the value typed at
  them. `linear_pattern 100 4` reads back `Occurrences 4` and `Offset
  33.33mm`, which is `Length / (Occurrences - 1)` for four instances.
- A count works under a schema that is not millimetres, which it could not
  before at all.
- The 71 integer steps leave the D5 census cured rather than counted: 212
  dimensionless steps echoing in mm, down to 141. The lint's own number is
  the measurement.
- ADR-202 reports an invalid object; this reports why. `offset 2` now
  prints the refused link write above the invalidity, which is the first
  time the two halves of GH #57 have been on the same screen.

### Negative

- Errors appear on lines that used to exit 0. The 82 verbs with a
  single-link selection step are the bulk of it, and every one of them is
  a value that was already being dropped — but a person who ran `offset`
  yesterday and saw nothing will see two errors today. The alternative is
  the silence this record exists to end.
- A caller who was relying on a whole float landing at an integer property
  through some other door gets an int now. Nothing in the tree does.

### Neutral

- `App::PropertyIntegerList` and `App::PropertyIntegerSet` are left out of
  `COUNTING`. They hold a sequence rather than a number and the harvest
  reads them as text steps; writing a string to one raises, and now says
  so, which is the honest report and not a fix.
- The float half of the D5 class — `App::PropertyFloat`,
  `App::PropertyFloatConstraint`, `App::PropertyPrecision`, 141 steps —
  still defaults to millimetres. It is wrong by a factor of 25.4 under an
  imperial schema and it is GH #47's D5 to finish; the cure is the same
  one line, and it changes what 141 steps echo, which is its own reading.

## Alternatives Considered

- **Coerce at the write only, and leave the step in millimetres.** Half
  the fix: it lands the value under the default schema and cannot land it
  under any other, because 101.6 is not a count however it is rounded.
- **Round a fraction to the nearest whole number.** `linear_pattern 100
  4.5` would build four instances, or five, and say nothing. A count with
  a fraction in it is a mistake somebody made; silently picking one of the
  two neighbours is the class of quiet wrongness this record is about.
- **Raise from `emit` when a property is refused.** The transaction aborts
  and the object goes away, which is tidy. Rejected for the same reason
  ADR-202 rejected undoing an invalid object: the rest of the line landed,
  and whether to keep a half-set feature is a decision for whoever is
  looking at the document.
- **Report refusals as INFO rather than ERROR.** Leaves the exit code
  alone, and the exit code is the whole of what a scripted caller sees.
  ADR-202 turned this one down for the same reason.
