---
status: Accepted
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-100
---

# ADR-301: Command matching is substring, prefix first

## Context

Tab completion of a verb name matches by prefix. `candidates()` keeps a
candidate when `c.lower().startswith(lowered)` (`fccli/completion.py`), so
the typed text must be the start of the name.

A verb's name is not always the word a person reaches for. When a
hand-written verb or another workbench already owns a short name, the
factory qualifies the loser under a compound name: `Part_Cut` becomes
`part_cut`, `Mesh_PolySegm` becomes `mesh_segment`, `Part_Fuse` becomes
`part_union`. The meaningful word — cut, segment, union — sits in the
middle, past the prefix. Under prefix matching it is unreachable: `cut`
plus Tab offers nothing for `part_cut`, because `"part_cut"` does not start
with `"cut"`. The bare `cut` resolves to `Mesh_PolyCut`, so a person after
a boolean subtraction reaches a mesh tool and never sees the one they want.

The pool is large — roughly 1250 verb names — which is why prefix matching
was the safe first choice. Completion already ranks rather than dumps,
though: at the head, `curation.current().order()` sorts candidates by
FreeCAD's own prominence and the active workbench, then `_by_habit()`
floats what this operator has run. A wider match set stays legible because
the ranking carries the good candidates up.

## Decision

Match a verb name at the head by **substring**, ordered **prefix first**.

- A candidate matches when the typed text appears anywhere in the name,
  case-folded (`name.find(typed) >= 0`), replacing the `startswith` test in
  `candidates()`.
- The hits sort in two tiers. Names where the match is at position 0 — the
  prefix hits — rank first, kept in their current curated order. The
  remaining substring hits follow, in the same curated order. A true prefix
  match never loses its place to a substring match.
- A single typed character stays prefix-only. Substring widening applies
  from two characters, so `b` does not pull half the registry.

The change is scoped to the **verb-head position**. Arguments, option
keywords, choices, root filenames, and the history ring keep prefix
matching: their pools are small, the prefix is precise there, and a
remembered command is being replayed, not discovered.

## Consequences

### Positive

- A qualified verb is reachable by its meaningful word. `cut` plus Tab
  offers `part_cut` and `mesh_polycut`, ranked, and the operator picks. The
  same holds for `segment`, `union`, `array`, and every other name the
  factory pushed behind a workbench prefix.
- Discoverability stops depending on knowing where a name starts. A person
  types the concept and the matching verbs surface.
- The pressure to hand-author alias spellings for scattered names eases. A
  substring match reaches `part_union` from `fuse` or `union` without an
  alias entry, so aliasing becomes a ranking nicety rather than the only
  route in.

### Negative

- The match set mid-typing is larger, and a common fragment matches widely.
  The two-character floor and the existing ranking hold this in check; a
  short fragment still returns a ranked list with the prominent verbs on
  top.
- A name collision now surfaces both sides. `cut` shows the mesh tool and
  the boolean together. This is the honest state of the vocabulary, and the
  ranking decides which leads, but the list is no longer a single answer.

### Neutral

- The `cut`-versus-boolean collision and the substring reach are
  independent of any renaming or aliasing the vocabulary later adopts.
  Substring matching makes the names findable; it does not change what they
  are.

## Alternatives Considered

- **Keep prefix-only.** Predictable and tight, and it needs no ranking to
  stay usable. It leaves every qualified name unreachable by its meaningful
  word, which is the whole problem, so the vocabulary would have to grow an
  alias for each scattered verb to compensate.
- **Subsequence (fuzzy) matching.** Match when the typed characters appear
  in order but not adjacent, so `pcut` finds `part_cut`. It reaches more,
  but it folds a match score into a ranking that already balances
  prominence, workbench and habit, and over 1250 names it surfaces
  surprising matches a person did not mean. Substring is the smaller step
  that solves the stated problem; subsequence is a superset that can layer
  on the same prefix-first tiering later if substring proves too narrow.
