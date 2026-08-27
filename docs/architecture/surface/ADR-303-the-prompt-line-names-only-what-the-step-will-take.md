---
status: Accepted
date: 2026-08-26
deciders:
  - aaronsb
  - claude
related:
  - ADR-300
  - ADR-203
---

# ADR-303: The prompt line names only what the step will take

## Context

The prompt is one line: what the step wants, then its options in a
bracket. Three renderers built it, each by joining the option names —
the dock, the socket client's interactive prompt, and the socket client's
`incomplete: still wants` line. One prompt, three copies of the same two
lines of formatting.

Two faults, found live, and both are the prompt saying something the step
does not honour.

**A bracket held two meanings.** After `cylinder 10` the prompt read `The
height of the cylinder [Angle]`. `Angle` is the cylinder's angular sweep,
a property the command will also set — but `[...]` is also how a choice
and a finish token render (`polyline ... [Close/Undo]`), and glued to the
height step it read as a hint about the value being asked for. Height is
not an angle. 129 steps in the tree carry options and 105 of them are
declared properties rather than alternatives to answering (GH #56).

**A word was advertised and refused.** Every panel step prints:

```
name=value sets one · done applies · cancel abandons
```

`done` worked. `cancel` did not — the step is `raw`, so the whole line
reached `_assign`, which found no `name=value` in it and answered
`'cancel' is not an assignment`. The panel stayed up and the engine kept
collecting. `Escape` in the dock and the socket's `cancel` op both did the
job; neither is the word the line names, and nothing at that prompt said
so (GH #71).

Both are the same complaint from opposite directions: an option rendered
as if it were part of what the step asks for, and a word named in the hint
and absent from the step.

## Decision

**Every word the prompt line shows is a word the step takes, and the two
kinds of word render apart.**

- `Option` carries `sets`: whether it names a property the command will
  set, rather than a way to answer or finish the step in front of it.
  The factory's boolean flags and the command tree's declared `options:`
  are settable; `Close`, `Undo`, `Diameter`, `done` and `cancel` are not.
- `Step.prompt_hint()` composes the tail, and the renderers call it.
  What you may type **instead of** answering keeps the bracket, beside
  the thing it replaces. A property the command will **also** set is
  named after it, as something else:

  ```
  The height of the cylinder  ·  also angle:
  Next point [Close/Undo]:
  name=value [done/cancel]:
  ```

- The composed hint travels on the `PROMPT` message and in
  `Session.state()`, so the dock and the socket cannot drift apart.
  `options` stays the whole pool, unsplit, because that is what completion
  offers. What a renderer shows and what a completer offers are two
  questions, and they were one list.
- **A panel step carries the `cancel` option its own instruction line
  advertises.** It aborts the verb, which presses the panel's Cancel and
  lets FreeCAD put the model back — the same thing Escape and the socket
  op already did, reached by the word that was already printed.
- The panel's two sentences — the offer when it opens, the refusal when a
  line will not parse — are constants next to each other and next to the
  options, because they went apart. The refusal now names all three ways
  out rather than two of them.

## Consequences

### Positive

- `The height of the cylinder` no longer reads as an angle, on any of the
  three surfaces.
- A person who reads the line the command line just printed and types the
  word it names gets what it says. The dock's Escape and a typed `cancel`
  are the same action.
- The prompt tail is composed once. A fourth surface renders the prompt by
  asking the step, not by re-deciding what a bracket means.

### Negative

- `close!` at a panel step is still refused. Deliberately: see below.
- A settable option now takes a little more room on the line — `also
  coarseview, fusebeforecut, hardhidden, ...` where a bracket ran them
  together. The longest is twelve, and it was twelve inside the bracket
  too.

### Neutral

- A field genuinely named `cancel` stays addressable. An option is matched
  against the whole raw line and every assignment has an `=` in it, so
  `cancel=5` is no prefix of `cancel` and reaches the field resolver. No
  panel in the tree has such a field; the property is structural rather
  than lucky.
- `sets` says nothing about whether the option *works*. A declared option
  writes `True` to the property it names, which is right for a boolean
  flag and wrong for the 105 that name an angle, a length or an
  enumeration. That is its own fault and its own issue; this record only
  stops the prompt from reading as though it were part of the question.

## Alternatives Considered

- **Render the settable option as `also: angle=`,** which is what GH #56
  suggests. It advertises a syntax the engine does not accept — `angle=180`
  at a cylinder step is not read as an assignment — and advertising a
  syntax that does not work is the fault GH #71 is. `also angle` is what
  the step will actually take today.
- **Stop printing `cancel` on the panel's instruction line.** The other
  half of GH #71's fix direction, and the cheaper one. Rejected because
  the word is what a reader expects and the machinery to honour it already
  existed: `_abort_panel` is what Escape reaches.
- **Make `close!` an escape from a panel step too.** Closing the document
  out from under an open panel is what the panel's own Cancel exists to
  prevent, and letting a token inside a raw step start another verb is the
  hazard `_verb_at_step` documents and ADR-201 refused. `cancel` then
  `close!` is two words in the right order, and the refusal now names the
  first of them.
- **Make `cancel` an option at every step, not only a panel's.** No verb
  is named `cancel`, so the word is free, and the asymmetry is real. But
  no other prompt advertises it, and adding a bare word that abandons the
  open command to all 1111 verbs is a grammar change rather than a prompt
  telling the truth. Left for whoever wants to argue it on its own.
