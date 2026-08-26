---
status: Accepted
date: 2026-08-26
deciders:
  - aaronsb
  - claude
related:
  - ADR-301
  - ADR-501
---

# ADR-201: A submitted line is one command

## Context

A verb name typed while a command is collecting abandons that command and
starts the one named. `_is_restart` guards it: the token has to be
unreadable as input for the open step — not an option prefix, not a
parsable point or quantity, not one of the step's choices, not the label
of an object in the document — before it counts as a new verb. That guard
has been tightened twice, once for choices and once for selections, and
both times because it had swallowed a value that was input.

The escape itself was never examined. It fires in two situations the
engine did not tell apart:

- A person at a prompt types a new verb. They see `loft cancelled`, they
  see the new prompt, and the next thing they type is answered by the
  command they meant. This is a convenience worth having; Rhino and
  AutoCAD both offer it.
- A token inside one submitted line will not parse at the step it reached.
  `_start` feeds the rest of the line token by token through the same
  door, so that token escapes to the verb namespace with nobody watching.

The second case is GH #72, and it is silent:

```
$ fccli exec 'loft standard'
loft cancelled
= standard_views
EXIT=0
```

`standard` is a prefix of `standard_views` (ADR-301), `standard_views`
takes no steps, so it ran to completion. The line exits 0, the engine is
idle, nothing is invalid, and stderr is empty. `loft` never ran.

It also manufactured a false result for the verification campaign
(ADR-501). The mode map drafted `subtractive_pipe standard constant
transformed`, the GH #52 sweep recorded `ok`, and what ran was the view
command. Every reading `verify.py::classify` makes — exit code, engine
state, delta-invalidity — was satisfied by a command nobody asked for.

Where the escape target has steps of its own, the line is left collecting
and exits 1, so the damage is visible. It is only when the target
completes that the line looks like a success.

## Decision

**A submitted line is one command.** A token in it that will not parse at
the step it reached is an error in that line, whatever else the token
happens to name.

The two situations are two doors, and they become two functions rather
than one function with a flag.

- `_verb_at_step` is a pure reading. It says which verb a token names when
  the token is no answer to the open step, and nothing else. Both doors
  ask it; each decides for itself what the answer means.
- `_feed_text` is the prompt door — somebody answered the step in front of
  them — and it still calls `_restart`.
- `_start` walks the rest of a submitted line itself, and there a named
  verb is refused. The message names both halves, so the line says what it
  would not do:

  ```
  error: 'standard' is the command 'standard_views', and a command does
  not start inside a line -- loft is still asking for List of sections
  ```

  The step it names is the **pending** one — what the following prompt
  announces — not the step the token was judged against. Those are two
  questions: a token is aimed at the step whose kind it matches, so `r1`
  reads as a relative point and is judged at the point step while a
  choice step is what the command is still asking for. Naming the wrong
  one puts two lines in one reply that contradict each other.
- Nothing is adopted on the way out. `_announce` normally fills a
  selection step from what is already selected rather than asking again;
  after a refusal that would advance a command the engine has just said
  it will not run, and where that selection is the only pending step it
  would carry the line all the way to `_finish` — refused, and run
  anyway.

- **The line stops at the refusal.** The tokens after the bad one were
  answers to the command it refused, and reading on would half-answer it:
  `_start` finishes a verb that learned its steps by starting as soon as
  any value lands, so `loft standard` — refused and then read on — came
  back live as a loft with no sections in it and an invalid `Loft` in the
  document.
- The command that was running stays open. The line ends `incomplete` and
  exits non-zero, which is what every other unparsable token at a step
  already does.

Typing a verb at a prompt to abandon the command in front of you is
unchanged.

## Consequences

### Positive

- A mistyped argument can no longer run a different command. The worst
  case is a refusal and a prompt still waiting.
- The verification campaign's `ok` means the command under test ran.
  `cancelled_in` (the harness half, PR #75) stays as a second net for
  cancellations arriving any other way, but the line it reads is no longer
  produced by an inline token.
- The two situations are told apart by which function reads the token, so
  there is no flag to pass wrongly and no third caller to get it right.

### Negative

- A line that used to "work" by escaping now fails. That is the point, but
  it means any script or mode-map draft that depended on the escape gets a
  refusal where it used to get an exit 0 — correctly, and loudly.
- `_start` now duplicates a little of what `_feed_text` does: it resolves
  the step for the token itself, so it can ask `_verb_at_step` before
  feeding. The suite pins both doors against the same token at the same
  step of the same command, so a divergence fails a named check.

### Neutral

- The refusal is an error, not a cancellation, so `<verb> cancelled` now
  only ever means a person asked for it or the escape happened at a
  prompt.
- This covers a token that reached a step. A token that reaches **no**
  step — every step filled, or the verb has none — is still dropped
  without a word: `zoom all extra` runs `zoom all` and exits 0, and
  `delete standard` deletes the selection. Same principle and same
  consequence, but the fix is not the same size: every line carrying a
  trailing token runs today, so it wants a sweep of what the tree and the
  ledger actually send. Filed as GH #77.

## Alternatives Considered

- **Escape only at the first step.** Would fix `loft standard`, since
  `standard` reaches loft's first step — but only by accident of where the
  bad token landed. `cylinder 5 sphere` would still escape at the second
  step, and the rule would be one nobody could predict from the outside.
- **Escape, but say so on stderr and exit non-zero.** Keeps the
  convenience and removes the silence, which was the shape the issue
  leaned toward. Rejected because it leaves the model changed: the escape
  target still runs, so a line that says "this went wrong" has already
  created geometry, and undoing it is the operator's problem. Refusing
  costs nothing and leaves the document alone.
- **Drop the escape entirely, at prompts too.** One rule, no flag. It
  takes away a convenience two CAD command lines have taught people to
  expect, to fix a fault that only occurs where there is no person to see
  it. The suite would have lost four checks that describe behaviour worth
  keeping.
