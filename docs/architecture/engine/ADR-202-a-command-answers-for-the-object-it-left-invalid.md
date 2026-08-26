---
status: Accepted
date: 2026-08-26
deciders:
  - aaronsb
  - claude
related:
  - ADR-302
  - ADR-501
---

# ADR-202: A command answers for the object it left invalid

## Context

`_finish` decides what a line has to say for itself. It reports an error
when `emit` raises, an error when FreeCAD raised a modal the intercept
caught, and otherwise a `RESULT` — the line, echoed back, with the object
that was made attached to the payload.

That covers every way a command can refuse, and none of the ways it can
succeed at nothing. FreeCAD computes a feature after the properties are
set, and when the references are inadequate it marks the object `Invalid`
rather than raising. `emit` returns normally, the transaction commits, the
`RESULT` goes out, and the socket exits 0.

The GH #52 selection sweep named fourteen instances of this on one run —
`pad`, `pocket`, `groove`, `hole`, `fillet`, `chamfer`, `draft`, four
helices and lofts, `additive_pipe`, `ruled_surface`, `scale` — every one
of them exiting 0 over a feature that built no solid and, in PartDesign,
hid the base feature behind itself. The document looks broken and the
command line said it went fine.

The facts were already on the wire. `_object_summary` (ADR-302) ships
`state` with `Up-to-date` filtered out, so a `RESULT` payload for a bad
fillet carries `["Touched", "Invalid"]`. Nothing read it back to the
person who typed the line, and nothing put it in the exit code.

Why those fourteen compute invalid is a separate question. The leading
lead — that a tier-1 verb creates the object and assigns properties
without running the command that would wire it into the body — is
unproven and has counterexamples in both directions. It stays open. What
does not depend on the answer is that the command line should not report
success over an object FreeCAD rejected.

## Decision

**A line that leaves an object FreeCAD computed and rejected says so, as
an error.**

- `_finish` records the invalid objects in the active document before
  `emit` and reads them again after. The **delta** is what the line is
  answerable for: a document that was already broken when the line ran is
  not this line's doing, which is the same reading `verify.py` makes from
  outside.
- The error names the objects and what it means:

  ```
  error: pad: FreeCAD computed Pad and marked it invalid -- the command
  ran, the result is not usable
  ```

- The `RESULT` still goes out, before the error. The line did run and the
  object does exist; saying only "error" would be as untrue as saying only
  "done".
- The object is **not** undone. Whether to keep a half-built feature and
  fix its references, or drop it, is a decision for whoever is looking at
  the document — and `undo` is one word away.
- The reading is scoped to one document. A verb that switched or closed
  the active document leaves nothing to compare against, and the document
  it switched *to* may have been broken for hours, so nothing is said.

The verification harness reads this the other way round from how it did.
`classify` puts the invalid reading above the exit code, because a
non-zero exit is now what an invalid run looks like from outside, and
`broken` would be the vaguer of the two answers. A run that also raised
keeps its message: `rejection_only` tells the engine's own invalidity
report from anything else stderr said, and `verify_one` carries the
difference into the detail.

## Consequences

### Positive

- Fourteen named commands stop reporting success over geometry that is not
  there. Any command that joins them is caught the day it does.
- The exit code carries it, so a script that runs `pad` and checks `$?`
  finds out. This is the reading the socket exists for.
- The two failure modes a command has — refusing, and succeeding at
  nothing — now travel the same way, which is what makes them comparable.

### Negative

- Every finished line now walks the active document's objects twice.
  Documents at CLI scale are small and the read is one attribute per
  object, but it is work that was not being done before, and a very large
  assembly will feel it.
- A workflow that deliberately builds a feature in stages — create it
  invalid, then give it its references — gets an error at the first stage.
  It is a true statement about the object at that moment, and the second
  stage is not blocked, but it is noise for whoever meant it.

### Neutral

- Nothing is said about *why* an object computed invalid. GH #57 stays
  open on that half if the fourteen turn out to share a cause the command
  line could have avoided.
- `verify.py`'s existing delta read is unchanged; only the order the
  classifications are tried in moved.

## Alternatives Considered

- **Report it as an INFO rather than an error.** Visible in the dock, and
  it leaves the exit code alone. Rejected because the exit code is the
  whole of what a scripted caller sees: a warning nobody's shell can read
  is how these fourteen went unnoticed through a whole sweep.
- **Undo the line when it leaves something invalid.** Tidy, and the verify
  harness does exactly this to keep one bad example from spoiling the
  next. Rejected for the interactive session: a person who pads a sketch
  with the wrong reference usually wants to fix the reference, and a
  command line that silently deletes their feature is worse than one that
  tells them it is broken.
- **Judge only the object `emit` returned.** Simpler, and no document
  walk. It misses every command that creates more than one object and
  every tier-0 verb, which hands back whatever FreeCAD's command left —
  often nothing at all. The delta finds what was actually made.
