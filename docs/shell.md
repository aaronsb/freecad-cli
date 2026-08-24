# The external shell — design

A terminal client that talks to a running FreeCAD, so a session can be
inspected and driven from outside the application.

Status: **steps 1–7 built** — history off the widget, the floor, the server,
and a one-shot client. `make socket` drives a real FreeCAD from outside and
asserts on it, 32 checks. Steps 5–8 (follow mode is partly there, the shared
buffer, the REPL) remain.

## "Is it the same as what's in the application?"

Yes — and more literally than it might sound. This is not a second copy of
the command language reached over a wire. It is the *same live state
machine*, with the socket as one more subscriber to the message bus the
engine already publishes on.

```
                  ┌──► Qt dock widget      in-process
engine ──► bus ───┤
                  └──► socket server ──► client A (terminal)
                                     └─► client B (agent)
```

One process, one `Engine`, one `Registry`, one document. Consequences that
fall out of that rather than being designed in:

- Start `polyline` from the terminal and the dock's prompt changes to
  `Next point [Close/Undo]:`, because there is one prompt.
- Click a point in the viewport and the terminal sees it land, because the
  picker feeds the same engine.
- `undo` from either side walks the same transaction stack.
- A verb an addon patch declared is available to both, because there is one
  registry.

| | Shared | Notes |
|---|---|---|
| Verb registry, aliases, patches | yes | one `Registry` |
| Engine state — current verb, step, collected values | yes | one `Engine` |
| Active document, undo stack, unit schema | yes | one FreeCAD |
| History | **needs moving** | see below |
| The input buffer being typed | yes | see *Shared buffer* |
| Who may type into it | one at a time | see *The floor* |
| Clickable option words | no | the dock renders them; a client may render its own |
| Live rubber-band trackers | no | Coin3D scene mutation at frame rate does not cross a socket |
| Mouse picks | yes, one way | they originate in the viewport whoever asked for them |

### The history wrinkle

History currently lives on the `Console` **widget**. That makes
`fccli history` impossible to answer honestly — a client would be asking a
Qt widget for its scrollback, and a headless FreeCAD would have none.

So history moves to a session-level object that subscribes to the bus, and
the widget reads it rather than owning it. That is a prerequisite, not a
nice-to-have, and it is a small refactor: the ring, the file, and
`commit_history` move out; the widget keeps only the cursor into it.

## Transport

**Unix domain socket**, one per FreeCAD process:

```
$XDG_RUNTIME_DIR/fccli/<pid>.sock      mode 0600
```

Never TCP. This executes commands in a live CAD session; it is not a network
service, and `XDG_RUNTIME_DIR` is already per-user and 0700.

Stale sockets from a crashed FreeCAD are removed on bind and on client
connect failure.

## Threading

`QLocalServer` on the **GUI thread**, driven by `newConnection` and
`readyRead` signals. No background thread, no locking, no marshalling.

This is the constraint everything else bends around: FreeCAD's API is not
thread-safe, and `engine.submit()` touches the document. A worker thread
would have to hand every command back to the GUI thread anyway, so it buys
nothing and risks a great deal.

## Protocol

JSON Lines, both directions. The server speaks the message stream that
already exists — `prompt`, `live`, `echo`, `result`, `error`, `info`,
`clear` — so a client that wants structure gets it, and one that wants text
renders it.

Client to server:

```json
{"op": "submit",   "text": "box 0,0,0 40 30 20"}
{"op": "buffer",   "text": "box 0,0,", "cursor": 8}
{"op": "complete", "text": "cylinder 5", "cursor": 10}
{"op": "claim"}
{"op": "release"}
{"op": "cancel"}
{"op": "history", "limit": 50}
{"op": "state"}
{"op": "subscribe"}
```

Server to client:

```json
{"kind": "live",   "text": "box 0,0,0 40mm"}
{"kind": "result", "text": "box 0,0,0 40mm 30mm 20mm", "replay": "...", "object": "Box"}
{"kind": "prompt", "text": "Width", "options": [], "step_kind": "quantity"}
{"kind": "error",  "text": "Length is required"}
{"kind": "buffer", "text": "box 0,0,", "cursor": 8, "holder": "client:3",
 "spans": [[4, 8, "number"]], "ghost": "0 40 30 20"}
{"kind": "ignored", "reason": "floor held by dock", "holder": "dock"}
```

Plus a handshake on connect carrying version, pid, document name, schema —
enough for a client to render a prompt without asking.

## Shared buffer

The line being typed is shared state, not just the commands that get
committed. A terminal user pressing Tab sees the completion cycle, the ghost
suggestion from history, and the red on an unparseable token — the same
things the dock shows, because it is the same buffer.

What is **not** shared is keystrokes. Sending each character would need a
key protocol, and would leave the dock's editor unable to own its own text.
Instead the floor-holder broadcasts the whole line whenever it changes:

```json
{"op": "buffer", "text": "cylinder 5", "cursor": 10}
```

A line is tens of bytes over a unix socket, so whole-line updates cost
nothing and there is no key protocol to design. Tab is a server round trip:

```json
{"op": "complete", "text": "cylinder 5", "cursor": 10}
{"kind": "completions", "candidates": ["5mm"], "replace": [9, 10]}
```

Completion, validation spans, and the ghost suggestion are computed by the
server against live engine state, so every client renders the same answer
without reimplementing any of it. The dock becomes one renderer of the
shared buffer rather than its owner — the same move the message stream
already made for output.

## The floor

Two clients typing into one buffer would interleave characters. So exactly
one holds the floor at a time, and everyone else observes.

**The floor is busy when the engine is collecting, or the buffer is
non-empty.** An idle dock with an empty input line does not hold it. That
rule matters more than who is focused: it means `fccli exec` works whenever
nobody is mid-thought, and refuses when someone is.

- The dock claims the floor when it has Qt focus and starts a command or
  types. It is released on Enter, Escape, or an empty buffer.
- A client claims with `{"op": "claim"}` and releases on `release` or
  disconnect.
- While a client does not hold the floor, `submit`, `buffer` and `cancel`
  are **ignored with a reply**, never silently dropped:

  ```json
  {"kind": "ignored", "reason": "floor held by dock", "holder": "dock"}
  ```

- Read-only operations — `history`, `state`, `subscribe` — always work,
  floor or no floor. Watching is never blocked.
- `--steal` takes the floor anyway, for when the other holder is a forgotten
  terminal.

This is what makes the shared buffer safe. Without it, a shared buffer is a
race; with it, it is a shared terminal.

### Showing it

The floor is worth nothing if you cannot see who has it. Every renderer
shows its own input state, so the answer to "will my keys go there?" is
visible without pressing one:

| State | The dock | A terminal client |
|---|---|---|
| **usurping** — keys anywhere land here | live border, prompt lit | normal prompt |
| **click to type** — usurping off, widget unfocused | dim border, dim prompt | n/a |
| **observing** — another client holds the floor | greyed text, holder named in the strip | greyed prompt, holder named |
| **blocked** — a modal dialog owns input | greyed, dialog named | refused, dialog named |

Greyed is the honest rendering for observing and blocked alike: the line is
still readable and still updating, and it is obvious that typing will go
nowhere. The states above the socket line — usurping and click-to-type —
exist today; observing arrives with the floor.

## Four decisions

**Who owns the prompt.** Shared state, arbitrated by the floor. Everyone
sees the same prompt; one party at a time advances it. This is implied by
having one engine — the alternatives require deliberately building
isolation. The handshake reports how many clients are attached and who holds
the floor, so nobody is surprised.

**Multiple FreeCAD instances.** Socket per pid. A client with one candidate
uses it; with several it lists them and requires `--pid`. `fccli ls
--instances` enumerates.

**Modal dialogs.** A tier-0 verb that opens a Task panel blocks the command
line the same way it blocks the dock. The server stays responsive — a modal
runs a nested event loop that still services sockets — but `submit` is
declined while `Gui.Control.activeDialog()` is set, naming the dialog. A
command executing into a half-open dialog is worse than one that waits.

That decline is **not an error**, and the difference matters to a caller.

**Security.** 0600 in `XDG_RUNTIME_DIR`. Anyone who can read that socket can
already read the user's files and attach a debugger to their FreeCAD, so the
socket adds no new authority. Refuse to bind anywhere world-readable.

## Many clients, one instance

Two different axes, worth not conflating:

- **Many clients → one FreeCAD.** The point of the socket. `QLocalServer`
  accepts simultaneous connections natively; each gets its own
  `QLocalSocket` and its own subscription to the bus. A person in an
  interactive REPL, an agent firing one-shots, and a `history -f` watching
  in a third pane are three clients on one engine.
- **Many FreeCADs.** A separate concern, handled by socket-per-pid.

The first is the interesting one and it should be provable rather than
assumed. The acceptance test is concrete: attach three clients, have one
watch, have the other two submit, and assert every client saw every message
in the same order and the document has exactly the objects that were asked
for.

### One-shot mode

An agent's client is not a REPL with the human removed — it wants different
things, so it is a distinct mode:

```bash
fccli exec 'box 0,0,0 40 30 20'        # claim, submit, await result, release
fccli exec --json 'circle 0,0,0 20'    # the typed message stream
fccli exec --wait 30 'pad 12'          # queue up to 30s for the floor
```

- **Claims the floor only for the moment of execution**, then releases. It
  never holds it while thinking, because it does not think.
- **Exits on the result**, not on a prompt. A command that opens a getter
  and waits for more input is an error in one-shot mode, reported as such
  with the prompt text, rather than hanging.
- **`--wait`** queues rather than failing when a human is mid-thought. An
  agent can afford to wait; a script in a pipeline usually cannot, so the
  default is to fail fast.
- **No tty required.** Output is plain by default and structured under
  `--json`.

The floor rule — busy when the engine is collecting or the buffer is
non-empty — is what makes this safe to run against a session someone is
using. An agent's one-shot lands in the gaps, and refuses rather than
interleaving into a half-typed command.

## "Not now" is not "wrong"

A one-shot meets two different kinds of no, and a caller does different
things about them:

| | Meaning | Caller's move |
|---|---|---|
| **rejected** | the command was wrong — unknown verb, missing argument, the emit failed | fix it |
| **busy** | the session is mid-something — a modal dialog is open, or someone holds the floor | wait and try again |

Busy is an ordinary condition, not a fault. Someone using FreeCAD will have
a dialog open a good fraction of the time, and an agent polling a live
session should expect it. So it reads as information:

```
$ fccli exec 'box 0,0,0 40 30 20'
not now: a task panel is open (Pad). The command was not run.
$ echo $?
75
```

Exit **75** is `EX_TEMPFAIL` from `sysexits.h` — the conventional "temporary
failure, retry later". It is deliberately far away from 1, so a script that
checks `if ! fccli exec ...` does not treat a busy session as a broken
command. Under `--json`:

```json
{"kind": "busy", "reason": "modal", "detail": "Pad", "retryable": true}
{"kind": "busy", "reason": "floor", "holder": "dock", "retryable": true}
```

Nothing is written to stderr for a busy result, because nothing went wrong.
`--wait` converts it into patience; `--steal` converts a floor hold into a
takeover. Neither applies to a modal dialog, which only the person clicking
it can clear.

## Client surface

Pure stdlib — FreeCAD ships the system Python, so the client imports nothing
that is not in the standard library and runs from any terminal or venv.

```bash
fccli                              # usage, and what it can attach to
fccli start --headless             # launch FreeCAD and wait for it
fccli exec 'box 0,0,0 40 30 20'    # one command
echo 'circle 0,0,0 20' | fccli     # stdin, one command per line
fccli history                      # the ring
fccli history -f                   # follow, live
fccli state                        # what the engine is waiting for
fccli ls                           # document objects
fccli --json ...                   # raw message stream, for programs
```

- **stdout** carries results and requested data
- **stderr** carries errors and prompts, so `fccli exec ... > out.txt` keeps
  stdout clean
- **exit code** is non-zero when a command errored, so `&&` composes

Interactive mode gets readline, so history and editing come from the
terminal rather than being reimplemented.

## Failure modes worth naming

| Situation | Exit | Behaviour |
|---|---|---|
| Done | 0 | result on stdout |
| Command rejected | 1 | the reason on stderr — this one is a fault |
| FreeCAD not running | 3 | "no running instance" |
| Several instances | 4 | list them, require `--pid` |
| Modal dialog open | 75 | informational, naming the dialog; nothing on stderr |
| Floor held elsewhere | 75 | informational, naming the holder; `--wait`, `--steal` |
| FreeCAD exits mid-session | 3 | the disconnect is reported |
| Stale socket file | — | removed and reported, not silently ignored |

## What it is not

A remote protocol. A rendering surface. A replacement for the dock — picking
still happens in the viewport, and `polyline` from a terminal means typing
every coordinate.

## Why it is worth building

An agent reading `fccli history` sees the same canonical, replayable command
text a person sees, and can hand back a corrected line. Existing FreeCAD MCP
servers are write-only RPC over the document object model: the agent fires
`create_object` with a raw property dict and cannot tell that a human is
mid-command. A shared message stream gives both parties one transcript and
one modal state.

## Build order

1. **History moves off the widget** into a session object on the bus.
   Prerequisite; nothing else is honest without it.
2. **The floor**, as engine-level state with the dock as its first holder.
   Nothing else is safe without it, and it is testable headless.
3. **Server**: `QLocalServer`, handshake, `submit`/`cancel`/`state`,
   broadcast of the bus.
4. **Client**: `exec`, `history`, stdin, exit codes. No REPL yet.
5. **Follow mode** — `history -f`, `subscribe`, and the three-client
   acceptance test above. This is where the shared-instance claim gets
   proved rather than asserted.
6. **Completion and validation move server-side**, exposed as `complete`.
   The dock switches to asking rather than computing, which is the change
   that proves the shared answer is genuinely shared.
7. **Shared buffer** — `buffer` ops both ways, the dock rendering rather
   than owning.
8. **REPL** rendering another client's half-typed line —
   [#3](https://github.com/aaronsb/freecad-cli/issues/3), and possibly a
   wontfix: `fccli watch` may be the honest answer.

Steps 1–4 give a working tool. Steps 6–7 are what make a terminal feel
identical to the dock, and they are worth doing in that order: the shared
buffer is only meaningful once completion has one implementation.
