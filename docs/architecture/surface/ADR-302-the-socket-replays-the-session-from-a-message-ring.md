---
status: Accepted
date: 2026-08-25
deciders:
  - aaronsb
  - claude
related:
  - ADR-501
---

# ADR-302: The socket replays the session from a message ring

## Context

Everything the engine says travels the bus as a typed `Message`
(`fccli/bus.py`): a kind, a text, a data payload. The dock subscribes and
renders. The socket has two doors onto the same stream: a live
subscription (`server.py` `_broadcast`) and a per-submit collector
(`_Collector`) that hands one line's messages back in the reply, spans
included, so `bin/fccli` paints a command the way the dock paints it.

Nothing is retained. The hello a connecting client receives carries only
the current state (`server.py` `_accept`), so an attaching client sees a
blank scrollback however long the session has run. A client that detaches
loses its place; its identity (`client:<n>`) is minted per connection and
never survives one. And the broadcast strips structure at the wire:
`payload.pop("object")` drops the created object from RESULT with nothing
in its place, so over the socket a completed command reports its replay
text and nothing about what it made.

The verification campaign (ADR-501, GH #47) runs into all three walls at
once. In a live demo, `part_fillet` returned clean — exit 0, engine idle —
while its Fillet computed to `Touched, Invalid` and parametrically hid its
base; no socket client could see it (GH #51, #57). The harness
(`tools/verify.py`) scrapes the human rendering of `state` because the
protocol offers no fact to read. The planned orchestration chain (GH #54)
needs to read what a session did after the fact.

The input side already has its ring: `session.py` `History` holds assembled
command lines. Output has no counterpart.

## Decision

The server retains the session's output as a sequence-numbered message
ring, and any client can replay it.

- **The ring.** The server keeps the last few thousand messages (default
  4096), each stamped with a monotonic sequence number. It retains what
  the dock's scrollback keeps — ECHO, INFO, ERROR, RESULT, and CLEAR as a
  cut point — and drops the kinds that describe the present moment: LIVE,
  BUFFER, PROMPT, OPTIONS, STATE. Entries are stored in the collector's
  wire form: kind, text, role, spans.
- **Character fidelity by re-rendering, not stored bytes.** Replayed
  messages pass through the same painter that rendered them live
  (`bin/fccli`'s span painting), so a resumed scrollback reproduces the
  original character-for-character. The server stores one structured
  stream; every client derives its own pixels.
- **RESULT names what it made.** The dropped `object` is replaced by a
  serializable summary — `{name, label, type, state}`, with `state` read
  the way `describe` reads it (`Up-to-date` filtered out). The summary
  travels all three doors: the submit reply, the live broadcast, the ring.
- **Cursors, not copies.** A client may present a resume id. The server
  maps id → last-delivered sequence number, LRU-capped at 512 ids; use
  bumps an id to the top. Reattaching with an id replays everything after
  its cursor. An interactive client prints its id on exit.
- **One-shot reads.** `fccli tail -n` returns the ring's last n entries; a
  read never moves a cursor. Cursors advance only when messages are
  delivered to a live subscriber.
- **Overflow to transcript.** A message leaving the ring is appended to a
  jsonl transcript file named by `fccli/paths.py`, one object per line,
  beside the history file.

The engine warning on an invalid result — saying it at the moment it
happens, at every terminal — is #57's fix and stays out of scope here.

## Consequences

### Positive

- Attach shows the session as it stands; resume restores a client's exact
  scrollback.
- The harness classifies from facts. RESULT says what was made and whether
  it is sound, so `ok` can require a valid object (GH #51), and
  `verify.py` stops scraping rendered text.
- The orchestration chain (GH #54) reads a transcript instead of holding a
  connection open for the whole run.
- The invisible-invalid case becomes visible at every terminal that cares
  to look.

### Negative

- New server bookkeeping: the ring, the cursor table, the LRU policy, the
  transcript writer.
- Replay renders through the client's current painter, so a changed
  painter re-renders the past in the new idiom — accepted, the same way a
  resized terminal reflows old output.
- Transcript files grow without bound; trimming is left to the operator.

### Neutral

- `History` (input) and the ring (output) stay separate; each answers its
  own question.
- The queryable complement — per-document invalid object names in the
  `state` reply — rides the same implementation for GH #51.
- The protocol version bumps; older clients ignore the new fields.
- A panel verb's RESULT says `object: null` — its emit opens the panel
  rather than making the object. What the panel made is read from the
  per-document invalid list; naming it in the RESULT is the panel tier's
  work (GH #53).

## Alternatives Considered

- **A rendered-character ring per client, resume-by-id over bytes.** The
  shape first proposed. Rejected: it freezes one rendering and discards
  the structure the harness needs, and it multiplies one stream into up to
  512 buffers when clients differ only by position in it. The bus is
  already the structured stream and rendering is deterministic, so the
  bytes are recomputable from the messages at any time; the reverse is not
  true.
- **Char-by-char input transport**, making the socket client a true
  terminal to the application. Rejected: `op=complete` and `op=buffer`
  already give the socket the dock's completion from the same live engine
  (`fccli/completion.py`), with local line editing and no round-trip per
  keystroke.
- **Client-side transcripts** — each client saves what it saw. Rejected: a
  client that was not attached saw nothing; only the server witnesses the
  whole session.
- **Harness-only fix** — have `verify.py` interrogate FreeCAD directly.
  Rejected: the harness verifies through the same door a person uses
  (ADR-501); a fact the protocol cannot carry to a person is the defect,
  not a gap to route around.
