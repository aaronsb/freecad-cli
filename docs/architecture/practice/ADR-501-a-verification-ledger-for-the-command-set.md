---
status: Accepted
date: 2026-08-24
deciders:
  - aaronsb
  - claude
related:
  - ADR-100
  - ADR-500
---

# ADR-501: A verification ledger for the command set

## Context

The command set has 1111 entries. Almost none of them are known to work
from the command line. A QA pass drove about fifteen by hand and found real
breakage under the assumption they were fine: `tube` opens a task panel and
takes no typed input, `polyline` never finishes non-interactively, `cut`
resolves to a mesh tool rather than the boolean. The rest are untested.

Nothing records what was tried. There is no note of which commands ran,
when, against which FreeCAD version, or with what result. So a command is
either assumed fine or silently broken, and there is no way to tell the two
apart without driving it again by hand.

FreeCAD's version moves. `make reconcile` already harvests a new release and
reports what changed. A command verified against 1.1.3 says nothing about
1.2, and today nothing marks that confidence as expired. Verification that
leaves no dated, version-stamped record cannot answer the one question that
matters after an upgrade: what needs looking at again.

## Decision

Verify commands against a canonical invocation, and keep the result in a
ledger the harness owns.

**An `example` field, authored, in the command file.** One canonical
invocation per command — `box 0,0,0 40 30 20`. It does two jobs: it is the
example the `man` page shows, and it is the input the verifier drives. A
command with no `example` is one the harness cannot drive on its own.

**Four interaction modes decide how a command is verified.** The QA pass
found them, and they gate the campaign:

| Mode | Verified by |
|---|---|
| positional | the harness runs `example` and checks the object it makes |
| selection | the harness selects a fixture solid, then runs the verb |
| panel | a probe drives the task panel the command opens |
| manual | a person confirms; the harness only records the result |

Mode is derived where the compiled command answers it — steps present reads
as positional, a command that opens a panel reads as panel — and authored
only where that is wrong.

**A harness, `make verify`, drives each command with an `example`** in mode
order: positional first, the largest and cheapest tier; then selection
against a fixture solid; then panel probes. Each pass stamps the ledger.

**The record is a sidecar ledger, not a frontmatter block.** A single file
the verify harness owns — `fccli/verified.json` — keyed by command id:

```json
"Part_Box": { "date": "2026-08-24", "freecad": "1.1.3",
              "mode": "positional", "result": "ok" }
```

The command files stay hand-owned below their `generated:` block, as
ADR-100 has them. A verification sweep changes one file, not 1111. The
ledger is a derived artifact beside `dictionary.json` and `descriptor.json`,
built by a tool, read by `man` and the reports.

**Staleness falls out of the version stamp.** A ledger entry whose `freecad`
is older than the current harvest is stale. `make reconcile` reads that
version already; it reports the never-verified count and the count gone
stale since the upgrade, next to what moved.

## Consequences

### Positive

- Coverage becomes a number: verified over 1111, broken down by mode. The
  unknown set is visible and shrinks with each sweep.
- An upgrade names its own follow-up. Reconcile lists what the new FreeCAD
  invalidated, so re-verification is targeted rather than another full pass
  by hand.
- The `man` pages gain an example each, which is the one thing a command
  reference is most often reached for.
- A verification sweep is one changed file. It does not churn the tree or
  collide with someone's authored edits.

### Negative

- Verification state and the command file are two places to look. The tools
  that need both — `man`, the reports — join them at read time by command
  id.
- An `example` is authored, so 1111 of them is real work. The campaign is
  tiered for this reason, and the QA pass already proved a first batch.
- The manual tier never reaches zero. Some commands are a dialog or a
  viewport gesture with no typed form, and their record says a person
  confirmed them, dated and versioned, rather than a harness.

### Neutral

- The mode taxonomy formalizes what the QA pass found, and it is the same
  classification that decides whether a command is CLI-drivable at all.
- The ledger can grow per-entry detail — the invocation run, the object it
  produced — without touching the command files.

## Alternatives Considered

- **A `verified:` block in the frontmatter.** Co-locates the record with the
  command, and reconcile already renders frontmatter. Rejected: the harness
  would write into files a person also edits, so every sweep churns 1111
  files and collides with authored work. The record is machine output; it
  belongs in a machine-owned artifact.
- **No examples; infer the invocation from the steps.** The harness would
  build a call from a command's parameters. Rejected: the sample values —
  radii, coordinates, angles — cannot be inferred safely, and a wrong sample
  fails verification for a command that works. The canonical invocation has
  to be stated once by a person, and stating it also documents the command.
- **Verify in CI only, keep no stored record.** A green run each release,
  nothing committed. Rejected: the record is the point. Without a dated,
  version-stamped ledger there is no way to ask what an upgrade invalidated,
  which is the question that recurs.
