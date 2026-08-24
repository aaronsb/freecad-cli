---
status: Accepted
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related: []
---

# ADR-500: Decisions are recorded as ADRs

## Context

The command line began as a spike: could FreeCAD's registries be turned
into a typed grammar that reads like a terminal. It could, and the spike
grew into a tool that is in use — 1111 launchers, a task-panel driver, a
socket client, three test tiers. Its decisions live in `docs/conventions.md`
(as rules), in commit messages (as reasoning), in `FINDINGS.md` (as facts
about FreeCAD), and in two design notes. None of those is a place to look up
why a choice was made, whether it still stands, or what it replaced.

The harvest thread made the cost concrete. Its conclusions about a
command dictionary were about to be held in agent memory; a design note was
written instead, and its review found fifteen wrong or incomplete claims
in the state description that no other record would have caught.

## Decision

Architectural decisions are recorded as ADRs under `docs/architecture/`,
managed by the vendored `docs/scripts/adr` tool, in five domains that
follow the seams in the code:

| Domain | Range | Scope |
|---|---|---|
| vocabulary | 100–199 | what the verbs are: descriptor, harvest, factory tiers, families, patches, dictionary, naming, curation |
| engine | 200–299 | how a command runs: steps and getters, task panels, picking, modals, transactions, key routing |
| surface | 300–399 | how it is presented and reached: dock, prompt, colour, completion, bus, socket, external shell, history |
| host | 400–499 | living inside FreeCAD: its settings, workbenches, undo, versions, install |
| practice | 500–599 | how the project is built and checked: test tiers, review, release, reconcile, records |

An ADR records a decision: context, the choice, consequences, alternatives.
A reference document — `docs/conventions.md`, `docs/state.md`,
`docs/shell.md` — describes what the code does and points at the ADR that
decided it. `FINDINGS.md` stays what it is: facts about FreeCAD.

Existing decisions are backfilled as they are touched, not all at once.
The first candidates are the ones `docs/conventions.md` states as rules
with reasoning attached: FreeCAD's settings are FreeCAD's; rank orders and
never hides; one typed line is one undo step; the typed message bus and
the socket as a peer; the three test tiers.

## Consequences

### Positive

- A decision has one home, a status, and a number other documents can cite.
- Superseding is explicit. A rule that changes leaves a record of what it
  replaced and why.
- `docs/scripts/adr lint` runs in `make check`, so a malformed or orphaned
  record fails the build.

### Negative

- Two document kinds where there was one. A change that alters a decision
  touches the ADR and the reference that describes the result.
- Backfill is incremental, so for a while `docs/conventions.md` states
  decisions no ADR records.

### Neutral

- `docs/design-notes/` is retired. The dictionary note became ADR-100; the
  state note became `docs/state.md`, a reference.

## Alternatives Considered

- **Keep design notes.** A note has no status and no number; nothing marks
  one as superseded, and nothing cites it.
- **Decisions in `docs/conventions.md` only.** It states rules well and
  reasons briefly; it has no room for alternatives or for a decision that
  no longer holds.
- **Backfill everything now.** Twenty ADRs written in a day from memory
  would carry the errors the state note's review found. Each is written
  when its subject is next touched, against the code as it is then.
