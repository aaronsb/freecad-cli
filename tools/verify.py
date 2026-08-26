#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Drive each command's example against a running FreeCAD, record the result.

ADR-501. Reads `fccli/dictionary.json` for commands that carry an `example`,
runs each over the socket the way a person would, and stamps a per-command
entry in `fccli/verified.json`: the date, the FreeCAD version, the example,
and the result.

Nothing here imports FreeCAD. It speaks to `bin/fccli`, which speaks the
socket, so a command is verified through the same door a person uses.

The result is what running the example did:

    ok         ran to completion, engine idle, and every object in the
               active document is valid
    invalid    ran to completion but left an invalid object -- FreeCAD
               computed it and rejected the result (ADR-302, GH #51)
    panel      a task panel is open -- the command is not positional and
               belongs to the panel tier
    incomplete the command is still collecting -- the example did not drive
               it to the end, so the example needs fixing
    busy       the floor was held by someone else (EX_TEMPFAIL)
    broken     the example was rejected outright -- a fault, reason in `detail`
    hazard     the command took the instance down or wedged it -- skipped
               by later sweeps unless --force
    no_fixture the command never ran: the operands its selection hint
               names could not be built, so there was nothing to select

A sweep survives its own targets: a command that kills FreeCAD is recorded
as `hazard`, a fresh headless instance is started, and the sweep continues.
The ledger is written after every command, so a stopped sweep loses at most
the command it was on.

`--modemap` drives the drafted examples in `fccli/modemap.json` instead of
the dictionary's authored ones, and records the outcomes in
`modemap_sweep.json` at the repo root. The tree is untouched: a draft earns
its `example:` field only after it passes here. A draft already in the
report is skipped, so the sweep resumes where it stopped.

`--tier` says which mode's drafts. `positional` runs the example on its
own. `selection` builds the fixture the command's `selection_hint` names,
hands it over with `select` (ADR-200), and then runs the verb -- so the
example is the two-part one ADR-200 describes, `select <what>; <verb>`, and
the fixture is built and selected before the verb is judged. Each command
gets a scratch document of its own, so one fixture cannot feed the next.

A run updates only the commands it drove; every other entry is left as it
was, so a sweep of one workbench does not erase the rest of the ledger.
"""

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(ROOT, "bin", "fccli")
DICT = os.path.join(ROOT, "fccli", "dictionary.json")
LEDGER = os.path.join(ROOT, "fccli", "verified.json")
MODEMAP = os.path.join(ROOT, "fccli", "modemap.json")
SWEEP_REPORT = os.path.join(ROOT, "modemap_sweep.json")

# Commands no headless sweep may run. Each has taken an instance down or
# poisoned it, live. GH #61 is the SIGSEGV. The stereo modes switch the
# Coin viewer into a GL mode Xvfb's software renderer does not have, and
# every repaint from then on prints "Unsupported format/type:
# GL_NONE/GL_NONE" -- the spam that once wrote 51GB into /tmp before the
# quota stopped it (GH #62).
_STEREO = "switches the viewer to a stereo GL mode headless GL lacks (GH #62)"
KNOWN_HAZARDS = {
    "Std_ToggleToolBarLock":
        "SIGSEGV: checkable command with no live QAction (GH #61)",
    "Std_TestProgress":
        "modal progress dialog that outlives the client (GH #60)",
    "Std_ViewIvStereoQuadBuff": _STEREO,
    "Std_ViewIvStereoInterleavedColumns": _STEREO,
    "Std_ViewIvStereoInterleavedRows": _STEREO,
    "Std_ViewIvStereoRedGreen": _STEREO,
    # Discovered live by the 2026-08-26 draft sweep: each killed the
    # instance. Recorded here so a fresh checkout does not rediscover
    # them by killing FreeCAD three more times.
    "Std_TestProgress2": "killed the FreeCAD instance (draft sweep)",
    "Std_TestProgress3": "killed the FreeCAD instance (draft sweep)",
    "Test_TestWork": "killed the FreeCAD instance (draft sweep)",
}


# --------------------------------------------------------------- fixtures

# A selection command needs operands. A fixture is the geometry the
# command's `selection_hint` names, built by command lines and handed to
# the command with `select` (ADR-200) -- so the operands arrive through the
# same door the command under test came through, and nothing here reaches
# into FreeCAD's API.
#
# Each recipe is (the lines that build it, what `select` is given). The
# names a recipe selects are FreeCAD's own for a fresh document: the first
# `box` is `Box`, the second `Box001`, and `new_body` over a selected solid
# holds it as `BaseFeature`. A recipe runs in a scratch document of its
# own, so those names come out the same every time.
FIXTURES = {
    "solid": (["box 0,0,0 20 20 10"], "Box"),
    "two_solids": (["box 0,0,0 20 20 10", "box 10,10,5 20 20 10"],
                   "Box, Box001"),
    "three_solids": (["box 0,0,0 20 20 10", "box 10,10,5 20 20 10",
                      "box 40,0,0 20 20 10"], "Box, Box001, Box002"),
    "solid_face": (["box 0,0,0 20 20 10"], "Box.Face6"),
    "solid_edge": (["box 0,0,0 20 20 10"], "Box.Edge1"),
    "two_edges": (["box 0,0,0 20 20 10"], "Box.Edge1, Box.Edge2"),
    "compound": (["box 0,0,0 20 20 10", "box 30,0,0 20 20 10",
                  "select Box, Box001", "compound"], "Compound"),
    # Four Draft lines meeting end to end, joined by `upgrade` into one
    # closed wire. Draft's own closed-wire verbs -- rectangle, polyline,
    # circle -- are all panel-mode, so this is the command line's only
    # route to a closed profile.
    "closed_wire": (["line 0,0,0 20,0,0", "line 20,0,0 20,20,0",
                     "line 20,20,0 0,20,0", "line 0,20,0 0,0,0",
                     "select Line, Line001, Line002, Line003",
                     "upgrade"], "Wire"),
    "two_wires": (["line 0,0,0 20,0,0", "line 20,0,0 20,20,0",
                   "line 20,20,0 0,20,0", "line 0,20,0 0,0,0",
                   "select Line, Line001, Line002, Line003", "upgrade",
                   "line 0,0,30 20,0,30", "line 20,0,30 20,20,30",
                   "line 20,20,30 0,20,30", "line 0,20,30 0,0,30",
                   "select Line004, Line005, Line006, Line007",
                   "upgrade"], "Wire, Wire001"),
    "two_lines": (["line 0,0,0 20,0,0", "line 0,20,10 20,20,10"],
                  "Line, Line001"),
    # A profile and a path: the closed wire first, then a line leaving its
    # plane, which is what a sweep or a pipe asks for.
    "wire_and_spine": (["line 0,0,0 20,0,0", "line 20,0,0 20,20,0",
                        "line 20,20,0 0,20,0", "line 0,20,0 0,0,0",
                        "select Line, Line001, Line002, Line003", "upgrade",
                        "line 0,0,0 0,0,40"], "Wire, Line004"),
    "solid_and_path": (["box 0,0,0 10 10 10", "line 0,0,0 0,0,60"],
                       "Box, Line"),
    # A PartDesign body needs a solid to hold: `new_body` over a selected
    # solid takes it as the body's BaseFeature. That feature is what a
    # dressup, a pattern or a tip move acts on, and its faces and edges are
    # what the body's own hints name.
    "body_feature": (["box 0,0,0 20 20 10", "select Box", "new_body"],
                     "BaseFeature"),
    "body_face": (["box 0,0,0 20 20 10", "select Box", "new_body"],
                  "BaseFeature.Face6"),
    "body_edge": (["box 0,0,0 20 20 10", "select Box", "new_body"],
                  "BaseFeature.Edge1"),
    # A sketch inside the body. `draft_to_sketch` leaves its sketch at the
    # document root, and `duplicate_object` is the verb that copies a
    # selected object into the active body, so the copy is the sketch the
    # body's hints name.
    "body_sketch": (["new_body",
                     "line 0,0,0 20,0,0", "line 20,0,0 20,20,0",
                     "line 20,20,0 0,20,0", "line 0,20,0 0,0,0",
                     "select Line, Line001, Line002, Line003", "upgrade",
                     "select Wire", "draft_to_sketch",
                     "select Sketch", "duplicate_object"], "Sketch001"),
    "body_two_sketches": (["new_body",
                           "line 0,0,0 20,0,0", "line 20,0,0 20,20,0",
                           "line 20,20,0 0,20,0", "line 0,20,0 0,0,0",
                           "select Line, Line001, Line002, Line003",
                           "upgrade", "select Wire", "draft_to_sketch",
                           "select Sketch", "duplicate_object",
                           "line 2,2,30 18,2,30", "line 18,2,30 18,18,30",
                           "line 18,18,30 2,18,30", "line 2,18,30 2,2,30",
                           "select Line004, Line005, Line006, Line007",
                           "upgrade", "select Wire001", "draft_to_sketch",
                           "select Sketch002", "duplicate_object"],
                          "Sketch001, Sketch003"),
    "group": (["new_group"], "Group"),
    "link": (["box 0,0,0 20 20 10", "select Box", "make_link"], "Link"),
    "linked_source": (["box 0,0,0 20 20 10", "select Box", "make_link"],
                      "Box"),
}

# Workbenches this tier does not fixture. Each needs a starting point no
# command line can make today: a mesh or a point cloud (the importers and
# converters are panel-mode), a TechDraw page with a view on it, an FEM
# analysis with a mesh and a solver, a CAM job with a tool controller, an
# Arch or BIM model, a spreadsheet with a cell selection, an open sketch
# editor. Sketcher is the largest of them and the clearest: its commands
# act on geometry inside a sketch in edit mode, which the command line
# cannot enter (GH #53 is the panel tier that would).
#
# A workbench is punted whole rather than hint by hint, because the missing
# thing is the workbench's own subject, not the wording of one hint.
PUNT_WORKBENCHES = {
    "Sketcher": "acts on geometry inside a sketch in edit mode",
    "TechDraw": "needs a drawing page with views on it",
    "Arch": "needs an Arch/BIM model",
    "BIM": "needs an Arch/BIM model",
    "IFC": "needs an IFC project",
    "FEM": "needs an analysis with a mesh, a solver or a result",
    "CAM": "needs a job with a model and a tool controller",
    "Mesh": "needs a mesh; the mesh importers are panel-mode",
    "MeshPart": "needs a mesh; the mesh importers are panel-mode",
    "Reen": "needs a point cloud or a mesh",
    "Points": "needs a point cloud",
    "Robot": "needs a robot and a trajectory",
    "Spreadsheet": "acts on a cell selection, which is not an object",
    "Assembly": "needs an assembly with parts in it",
    "Inspection": "needs a mesh or a nominal geometry pair",
}

# Which fixture a hint names, for the workbenches the tier does cover. The
# hints are prose, one per command, 301 distinct phrasings over 383
# commands, so the read is by phrase: ordered rules, first match winning,
# and a narrow phrase sits above the phrase that contains it.
#
# A rule scoped to a workbench matches only that workbench's commands --
# "a sketch" in PartDesign means one inside the active body, and the same
# words in Part mean one at the document root.
#
# A rule mapping to None is a hint whose operand this tier cannot build
# even though its workbench is covered: a mesh, a spreadsheet cell, a
# focused macro, an object nested in a container. Those commands are the
# panel or manual tier's, and the sweep says so rather than driving them
# against the wrong operands.
HINT_RULES = [
    # A hint that offers a shape as an alternative to a mesh takes the
    # shape, so it must be read before the mesh rule turns it away.
    (None, r"shapes or meshes|shapes converted from meshes", "solid"),
    (None, r"\bmesh\b|\bmeshes\b|point cloud", None),
    (None, r"\bcells?\b", None),
    (None, r"\bmacro\b", None),
    (None, r"nested inside another", None),
    (None, r"\bDimensions?\b", None),
    (None, r"section plane|SectionPlane", None),
    (None, r"not just a face|whole part", "solid"),
    (None, r"links pointing to it", "linked_source"),

    # PartDesign: what a body's hints name lives inside the body.
    ("PartDesign", r"features? of the active body|"
                   r"feature in the active body|features? to pattern",
     "body_feature"),
    ("PartDesign", r"edges? or faces? of the active body", "body_edge"),
    ("PartDesign", r"two or more sketches|loft order|\bspine\b|"
                   r"\bpath sketch\b", "body_two_sketches"),
    ("PartDesign", r"\bsketch\b|\bprofile\b", "body_sketch"),
    ("PartDesign", r"faces? of the (active )?body|faces? of the solid",
     "body_face"),
    ("PartDesign", r"single-solid object|duplicate into the active body|"
                   r"objects? or subelements", "solid"),

    # Shapes, by what the hint asks for. A hint that names a second
    # operand -- a path, a spine, a stencil -- says so before it names the
    # first, so those rules come first.
    (None, r"\bspine\b|extrusion paths?|\bpath sketch\b",
     "wire_and_spine"),
    (None, r"\bpath object\b|then the path\b", "solid_and_path"),
    (None, r"exactly three objects", "three_solids"),
    (None, r"two edges or wires|two wires", "two_lines"),
    (None, r"loft order|two or more profiles|profiles? \(points|"
           r"transversal sections", "two_wires"),
    (None, r"two overlapping|two solids|two shapes|"
           r"two or more (overlapping )?(solids|shapes|shape objects|"
           r"objects|intersecting|walled)|two or more intersecting|"
           r"two or more walled|object to slice first|base solid first|"
           r"three or more|then a point object", "two_solids"),
    (None, r"\bcompound\b|\bfusion\b", "compound"),
    (None, r"\bLink\b", "link"),
    (None, r"\bgroups?\b", "group"),
    (None, r"closed wire|closed 2D|closed coplanar|closed sketch|"
           r"2D profile|2D shape|2D layout|planar object|wire-based|"
           r"\bwires\b|\bsketch\b|\bwire\b", "closed_wire"),
    (None, r"subelements? \(vertices, edges, or faces\)|shape element|"
           r"individual edges or faces|edges or faces\b", "solid_face"),
    (None, r"two edges", "two_edges"),
    (None, r"faces? of a solid|faces? of the features|one or more faces|"
           r"planar face|\ba face\b|\bfaces\b", "solid_face"),
    (None, r"one or more edges|straight edge|\ban edge\b|\bedges\b",
     "solid_edge"),
    (None, r"one or more objects|one or more shapes|one or more solid|"
           r"one or more geometr|one or more shape objects|"
           r"one or more Draft|one or more items|one shape object|"
           r"shapes in the active document|whole part|Part-based|"
           r"Part shape|\ba shape\b|\ba solid\b|\ba single object\b|"
           r"\ban object\b|\bthe object\b|\bobjects\b|\bfeature",
     "solid"),
]


def fixture_for(cid, hint):
    """The fixture a command's selection hint names.

    Returns (name, recipe lines, what `select` is given). A hint this tier
    does not build answers (None, [], why not) -- the command belongs to
    the panel or manual tier, and the sweep records that reason rather
    than guessing an operand.
    """
    workbench = cid.split("_")[0]
    punt = PUNT_WORKBENCHES.get(workbench)
    if punt:
        return None, [], punt
    text = (hint or "").strip()
    if not text:
        return None, [], "no selection hint to build from"
    for scope, pattern, name in HINT_RULES:
        if scope is not None and scope != workbench:
            continue
        if not re.search(pattern, text, re.I):
            continue
        if name is None:
            return None, [], f"no fixture for a hint naming {text!r}"
        lines, selection = FIXTURES[name]
        return name, list(lines), selection
    return None, [], f"no rule reads the hint {text!r}"


def fccli(*args, **kw):
    kw.setdefault("stdin", subprocess.DEVNULL)
    kw.setdefault("timeout", 60)
    proc = subprocess.run([sys.executable, CLIENT, *args],
                          capture_output=True, text=True, **kw)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _exec(line):
    return fccli("exec", line)


def build_fixture(lines, run=None):
    """A scratch document holding the fixture, ready to be consumed.

    ``lines`` is the recipe and the `select` that hands it over. The
    document reset is best-effort -- `close!` has nothing to close on the
    first command -- and every recipe line after it must succeed: an
    operand the harness could not present is the harness's failure, not
    the command's, so the caller records `no_fixture` rather than blaming
    the verb.

    Returns (ok, detail); the detail names the line that faulted.
    """
    run = run or _exec
    run("close!")                       # drop the last command's scratch
    for line in ["new verify"] + list(lines):
        code, _out, err = run(line)
        if code != 0:
            return False, f"{line} -- {err or f'exit {code}'}"[:200]
    return True, ""


def verb_line(example):
    """The command half of a two-part selection example.

    ADR-200 writes a selection command's example as `select <what>;
    <verb> <params>`. The select half is setup -- `build_fixture` has
    already run it -- so what is left to judge is the half after it.
    """
    _select, _, verb = example.partition(";")
    return verb.strip() or example.strip()


def selection_targets(modemap):
    """What the selection tier drives, and what it cannot.

    Returns (targets, fixtures, punted). ``targets`` is {cid: example} in
    ADR-200's two-part form for every selection command whose hint this
    tier can build; ``fixtures`` is {cid: recipe lines}, the select line
    last; ``punted`` is {cid: reason} for the rest, so the report says why
    a command was not driven instead of leaving a hole.
    """
    targets, fixtures, punted = {}, {}, {}
    for cid, entry in modemap["commands"].items():
        if entry.get("mode") != "selection":
            continue
        example = entry.get("example")
        name, lines, gives = fixture_for(cid, entry.get("selection_hint"))
        if name is None:
            punted[cid] = gives     # with no fixture, that slot is the reason
            continue
        if not example:
            punted[cid] = "the mode map drafted no example to run"
            continue
        select = f"select {gives}"
        targets[cid] = f"{select}; {example}"
        fixtures[cid] = lines + [select]
    return targets, fixtures, punted


def running():
    return fccli("ls")[0] == 0


def start_headless():
    """Start a fresh headless instance, output to the void.

    DEVNULL, not a log file: a poisoned instance can write tens of
    megabytes of repaint errors a second, and a sweep must survive its
    own targets without filling a disk.
    """
    code, _out, _err = fccli("start", "--headless", "--timeout", "90",
                             timeout=120)
    time.sleep(1)
    return code == 0 and running()


def _snapshot():
    """The session's state, as the JSON the server sent.

    The server's own facts, not a scrape of their human rendering
    (ADR-302).
    """
    _, out, _ = fccli("--json", "state")
    try:
        return json.loads(out)
    except ValueError:
        return {}


def classify(code, engine, panel, invalid):
    """The result, from the exec exit code and the state after it.

    ``panel`` is the server's word that a task panel is open. ``invalid``
    is what the run left invalid. A 75 exit means the command never ran
    at all -- the floor or a dialog belongs to someone else -- and an
    open panel may be that very dialog, so busy outranks panel. A panel
    outranks the engine reading: a panel driven from the command line
    keeps the engine collecting, and that is the panel tier, not a short
    example. `ok` requires a clean exit AND nothing left invalid -- a
    command that computes an object FreeCAD rejects has not verified,
    however cleanly it returned.
    """
    if code == 75:
        return "busy"
    if panel:
        return "panel"
    if engine != "idle":
        return "incomplete"
    if code != 0:
        return "broken"
    if invalid:
        return "invalid"
    return "ok"


def _invalid(snap):
    active = next((d for d in snap.get("documents") or []
                   if d.get("active")), {})
    return active.get("invalid") or []


def verify_one(example):
    """Run one example, classify what happened. Leaves the engine idle.

    Invalidity is judged on the delta: what this run made invalid, not
    what it found already broken. An invalid run is undone, so one bad
    example cannot mark every example after it.
    """
    fccli("cancel")                       # clear whatever the last one left
    before = _invalid(_snapshot())
    code, _out, err = fccli("exec", example)
    snap = _snapshot()
    fresh = [n for n in _invalid(snap) if n not in before]
    result = classify(code, snap.get("engine") or "",
                      snap.get("panel"), fresh)
    if result in ("incomplete", "panel"):
        fccli("cancel")
    if result == "invalid":
        fccli("exec", "undo")
        return result, ", ".join(fresh)
    return result, (err if result in ("incomplete", "broken") else "")


def _load(path):
    """The store, or a stop. A store that fails to parse ends the run:
    overwriting it would throw away every result it still holds."""
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path))
    except ValueError as exc:
        sys.exit(f"verify: {path} is unreadable ({exc}) -- "
                 f"repair or remove it")


def resumable(targets, entries):
    """Which targets a resumed sweep still runs.

    A result already recorded for the same example is an answer and
    stands -- except `busy`, the floor's state rather than the draft's,
    and `no_fixture`, the harness's own gap rather than the command's,
    both of which are retried; and `hazard`, which stays in the targets
    so plan() reports the skip.
    """
    return {c: e for c, e in targets.items()
            if entries.get(c, {}).get("example") != e
            or entries[c].get("result") in ("hazard", "busy", "no_fixture")}


def plan(targets, prior, force=False, start_at=None):
    """Split targets into what this sweep runs and what it skips.

    ``prior`` is the record of earlier sweeps, {cid: entry}. A command in
    KNOWN_HAZARDS or recorded `hazard` is skipped; --force runs it anyway.
    """
    run, skipped = {}, {}
    for cid, example in sorted(targets.items()):
        if start_at and cid < start_at:
            continue
        reason = KNOWN_HAZARDS.get(cid)
        if reason is None and prior.get(cid, {}).get("result") == "hazard":
            reason = prior[cid].get("detail", "recorded hazard")
        if reason and not force:
            skipped[cid] = reason
            continue
        run[cid] = example
    return run, skipped


def _healthy():
    """The instance answers with facts.

    ``fccli ls`` is not enough: it exits 0 for a live *process*, even one
    whose server no longer answers -- which is exactly the wedged case.
    """
    try:
        return bool(_snapshot())
    except subprocess.TimeoutExpired:
        return False


def _restart():
    """A working headless instance, whatever is there now.

    A wedged instance still holds its socket and would block the start,
    so a FreeCAD that no longer answers is killed first -- and only a
    FreeCAD: the pid comes from a socket filename, and a recycled pid
    must not take the signal. An instance that does answer is reused
    rather than doubled. Returns (ok, started_new): reuse is not
    ownership, and the caller must not quit an instance it only reused.
    """
    try:
        _, out, _ = fccli("--json", "ls", timeout=90)
        rows = json.loads(out)
    except (subprocess.TimeoutExpired, ValueError):
        rows = []
    killed = False
    for row in rows if isinstance(rows, list) else []:
        if row.get("reachable") or not row.get("pid"):
            continue
        try:
            with open(f"/proc/{int(row['pid'])}/comm") as fh:
                comm = fh.read().strip().lower()
        except (OSError, ValueError):
            continue
        if "freecad" not in comm:
            continue
        try:
            os.kill(int(row["pid"]), signal.SIGKILL)
            killed = True
        except OSError:
            pass
    if killed:
        # Killed is not gone: the corpse answers kill(pid, 0) and holds
        # its socket entry until its parent reaps it, so poll.
        for _ in range(20):
            if not running():
                break
            time.sleep(0.5)
    started_new = False
    if not running():
        if not start_headless():
            return False, False
        started_new = True
    if not _healthy():
        return False, started_new
    fccli("exec", "new verify")
    return True, started_new


def _restart_owned(owned):
    """The sweep's restart hook: ownership is a fact the restart updates.

    An instance this sweep started, first or mid-sweep, is quit at the
    end; one it merely reused belongs to whoever started it, and `quit!`
    against a reused instance discards their unsaved documents.
    """
    ok, started_new = _restart()
    if started_new:
        owned["it"] = True
    return ok


def sweep(targets, record, run_one=None, alive=None, healthy=None,
          restart=None, setup=None):
    """Run every target, restart a dead or wedged instance, checkpoint
    each result.

    ``record(cid, example, result, detail)`` is called after every
    command, hazards included -- it owns persistence, so a stopped sweep
    keeps everything already run. ``setup(cid)`` prepares what the
    command needs and returns (ok, detail); the selection tier builds its
    fixture there. A setup that fails on a healthy instance is
    `no_fixture` and the sweep moves on; one that fails because the
    instance is gone is a hazard like any other. The hooks default to the
    real client; they exist so this loop is testable without a FreeCAD.
    Returns (tally, finished, restarts).
    """
    run_one = run_one or verify_one
    alive = alive or running
    healthy = healthy or _healthy
    restart = restart or _restart
    tally, restarts = {}, 0
    total = len(targets)

    def note(cid, example, result, detail):
        record(cid, example, result, detail)
        tally[result] = tally.get(result, 0) + 1

    for i, (cid, example) in enumerate(sorted(targets.items()), 1):
        if setup is not None:
            try:
                ready, why = setup(cid)
            except subprocess.TimeoutExpired:
                ready, why = False, "client timed out; instance wedged"
            if not ready:
                # A recipe that faulted on a live instance is the
                # harness's gap. One that faulted because the instance
                # died is the hazard the next command would hit too.
                try:
                    dead = not healthy()
                except subprocess.TimeoutExpired:
                    dead = True
                if dead:
                    note(cid, example, "hazard", f"fixture: {why}")
                    print(f"[{i}/{total}] {'hazard':10} {cid} -- "
                          f"restarting FreeCAD", flush=True)
                    restarts += 1
                    if not restart():
                        print("verify: restart failed, stopping",
                              file=sys.stderr)
                        return tally, False, restarts
                    continue
                note(cid, example, "no_fixture", why)
                print(f"[{i}/{total}] {'no_fixture':10} {cid}  ({why})",
                      flush=True)
                continue
        try:
            result, detail = run_one(example)
        except subprocess.TimeoutExpired:
            result, detail = "hazard", "client timed out; instance wedged"
        if result != "hazard":
            try:
                if not healthy():
                    result = "hazard"
                    detail = ("left the instance unresponsive" if alive()
                              else "killed the FreeCAD instance")
            except subprocess.TimeoutExpired:
                result, detail = "hazard", "left the instance unresponsive"
        note(cid, example, result, detail)
        if result == "hazard":
            print(f"[{i}/{total}] {'hazard':10} {cid} -- restarting FreeCAD",
                  flush=True)
            restarts += 1
            if not restart():
                print("verify: restart failed, stopping", file=sys.stderr)
                return tally, False, restarts
            continue
        print(f"[{i}/{total}] {result:10} {cid}  ({example})", flush=True)
    return tally, True, restarts


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Verify command examples (ADR-501).")
    ap.add_argument("--only", help="verify one command id, e.g. Part_Box")
    ap.add_argument("--modemap", action="store_true",
                    help="drive the mode map's drafts instead, recording to "
                         "modemap_sweep.json; the tree and the ledger are "
                         "untouched")
    ap.add_argument("--tier", choices=("positional", "selection"),
                    default="positional",
                    help="which mode's drafts --modemap drives: positional "
                         "runs the example alone, selection builds the "
                         "fixture the hint names and selects it first")
    ap.add_argument("--start-at", metavar="COMMAND",
                    help="skip every command id before this one")
    ap.add_argument("--force", action="store_true",
                    help="run commands recorded as hazards")
    args = ap.parse_args(argv)

    version = json.load(open(DICT)).get("freecad")
    fixtures, punted = {}, {}
    if args.modemap:
        modemap = json.load(open(MODEMAP))
        if args.tier == "selection":
            targets, fixtures, punted = selection_targets(modemap)
        else:
            targets = {cid: e["example"]
                       for cid, e in modemap["commands"].items()
                       if e.get("mode") == "positional" and e.get("example")}
        store_path = SWEEP_REPORT
        store = _load(store_path)
        entries = store
        prior = dict(entries)
        if not args.force:
            targets = resumable(targets, entries)
    else:
        if args.tier != "positional":
            sys.exit("verify: --tier selection drives the mode map's drafts; "
                     "pass --modemap")
        data = json.load(open(DICT))
        targets = {cid: e["example"] for cid, e in data["commands"].items()
                   if e.get("example")}
        store_path = LEDGER
        store = _load(store_path)
        entries = store.setdefault("commands", {})
        prior = dict(entries)

    if args.only:
        targets = {k: v for k, v in targets.items() if k == args.only}
        punted = {k: v for k, v in punted.items() if k == args.only}

    run, skipped = plan(targets, prior, force=args.force,
                        start_at=args.start_at)
    for cid, reason in sorted(skipped.items()):
        print(f"  {'skipped':10} {cid}  ({reason})")

    today = datetime.date.today().isoformat()

    def record(cid, example, result, detail):
        entry = {"example": example, "result": result}
        if not args.modemap:
            entry["date"] = today
            entry["freecad"] = version
        if detail:
            entry["detail"] = detail[:200]
        entries[cid] = entry
        if not args.modemap:
            store["date"] = today
            store["freecad"] = version
        # Written beside and swapped in whole: a checkpoint interrupted
        # mid-dump must not cost the results it was checkpointing.
        tmp = store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(store, fh, indent=1, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, store_path)

    # Skips are recorded too, so the report says why a command was not run.
    for cid, reason in skipped.items():
        record(cid, targets[cid], "hazard", reason)
    # So is a hint this tier does not build: the report answers "why was
    # this command not driven" for every selection command, not just the
    # ones the fixture vocabulary reaches.
    for cid, reason in punted.items():
        example = (modemap["commands"][cid].get("example") or "")
        record(cid, example, "no_fixture", reason)
    if punted:
        print(f"  {len(punted)} selection commands have no fixture this "
              f"tier can build")

    if not run:
        print("nothing to verify -- no examples, or all already recorded")
        return 0

    started = False
    if not running():
        print("starting a headless FreeCAD ...")
        if not start_headless():
            print("could not start FreeCAD", file=sys.stderr)
            return 3
        started = True

    if "panel" not in _snapshot():
        print("this FreeCAD predates ADR-302 and cannot report panel or "
              "validity facts -- restart it with the current addon",
              file=sys.stderr)
        return 3

    # The selection tier builds a fixture per command and judges only the
    # verb after it; the positional tier runs its example whole.
    hooks = {}
    if fixtures:
        hooks = {"setup": lambda cid: build_fixture(fixtures[cid]),
                 "run_one": lambda example: verify_one(verb_line(example))}

    owned = {"it": started}
    fccli("exec", "new verify")
    try:
        tally, finished, restarts = sweep(
            run, record, restart=lambda: _restart_owned(owned), **hooks)
    finally:
        if owned["it"] and running():
            fccli("cancel")
            fccli("exec", "quit!")

    summary = ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))
    note = (f", {restarts} restart" + ("s" if restarts > 1 else "")
            if restarts else "")
    print(f"\n{len(run)} run, {len(skipped)} skipped ({summary}{note}). "
          f"{os.path.relpath(store_path, ROOT)}")
    return 0 if finished else 3


if __name__ == "__main__":
    sys.exit(main())
