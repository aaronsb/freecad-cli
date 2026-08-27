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
    manual     the command is nobody's to drive: ADR-501's fourth mode is
               one a person confirms and the harness only records
    cancelled  the line abandoned the command it named: a token that would
               not parse at a step matched another verb, and the engine ran
               that one instead (GH #72)

The panel tier adds five of its own, because a panel command can fail in
ways a positional one cannot (GH #53):

    no_panel    the verb ran and opened no panel -- the mode map has this
                command in the wrong tier
    mouse_panel a panel opened that the command line cannot drive: nothing
                to type into, or no way to finish. It is a mode; the
                harness closes it and says so
    bad_field   the draft named a field the panel does not have. The
                detail is the engine's complaint, which names the ones it
                does have
    stuck_panel a panel neither `done` nor `cancel` would close. The
                instance is no longer fit to judge anything, so the sweep
                restarts it -- recorded against the command that left it,
                and not against the ones it would otherwise have spoiled
    blocked     a command that ran while one of those was still up, so it
                was never judged. The sweep restarts, and a later pass
                runs it again on an instance where the answer means
                something

A sweep survives its own targets: a command that kills FreeCAD is recorded
as `hazard`, a fresh headless instance is started, and the sweep continues.
The ledger is written after every command, so a stopped sweep loses at most
the command it was on.

The ledger sweep is mode-routed: `fccli/modemap.json` says how each
authored example is driven, and the entry records which (GH #54). A
positional example runs bare. A selection example runs behind the fixture
its hint names, and only its verb half is judged (ADR-200). A panel
example is driven through the panel step. A `manual` one is not driven at
all. Every entry carries its `mode`, so an entry says what kind of driving
produced it -- and an entry recorded in a mode the command is no longer
in, or against an older FreeCAD, is re-run by the next sweep. That, with
the checkpoint after every command, is what makes `make verify` resumable:
stop it and start it again and it picks up where it stopped.

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

`panel` builds the same fixtures and then drives the task panel the verb
opens: it reads the fields off the engine, sets the `name=value` pairs the
draft carries, and `done`s. A draft with no pairs still runs -- the verb,
the fields, and `done` -- so every panel command gets an answer and the
report says which had parameters to set. The field names the panel
answered with are kept in the report beside the result.

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
    # Guarded, and still skipped. The command line refuses it now
    # (panels.run_command, GH #61), so a sweep that ran it would record a
    # refusal rather than lose the instance -- but the refusal is the only
    # thing standing between this command and a dead FreeCAD. Given a live
    # action, which MainWindow's own popup menu builds, `runCommand` does
    # not segfault and aborts a second way instead: an event-filter
    # recursion out of the toolbar relayout, `Unrecoverable stack
    # overflow`. Two fatal paths, one of them guarded, is not a command to
    # verify by running.
    "Std_ToggleToolBarLock":
        "refused by the command line, and fatal a second way if it is not "
        "(GH #61)",
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
    # Discovered live by the 2026-08-26 panel sweep, the same way.
    "BIM_Door": "killed the FreeCAD instance (panel sweep)",
}


# A command whose whole effect is a write to the operator's settings, and
# which the sweep must not run whatever it is asked -- including --force,
# which means "run the commands recorded as dangerous to the instance",
# not "write my preferences".
#
# `Draft_Snap_Lock` is GH #74. Every `Draft_Snap_*` command and
# `Draft_ShowSnapBar` derive from `Draft_Snap_Base`, whose IsActive is
# `Gui.Snapper.isEnabled("Lock")` -- so one bit gates the availability of
# eight of this sweep's commands. Activated toggles that bit and
# `save_snap_state` writes it to `snapModes` in the user's parameters, so
# it outlives the process: a sweep that ran this one left Lock off, and
# the *next* sweep read eight commands as `is not available here` and
# blamed whatever happened to precede them. That is why the failures moved
# with no local cause, why replaying the predecessors never reproduced
# them, and why a scratch profile always passed.
#
# Skipped rather than fixed at the command, because there is nothing wrong
# with the command: a person who types `snap_lock` means to toggle
# snapping, and it does. What is wrong is a verification sweep changing
# the world it is measuring.
WRITES_SETTINGS = {
    "Draft_Snap_Lock":
        "toggles the Draft snap Lock and saves it to the operator's "
        "parameters, which gates eight other commands' availability in "
        "the next sweep (GH #74)",
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
    # Two bodies, the second left active: `new_body` activates what it
    # makes, so the body selected here is the tool and the one it is
    # combined into is the active one -- which is the shape a PartDesign
    # boolean asks for. Authored for the panel tier (GH #53); no
    # selection hint reads its way here.
    "two_bodies": (["box 0,0,0 20 20 10", "select Box", "new_body",
                    "box 10,10,5 20 20 10", "select Box001", "new_body"],
                   "Body"),
    # A body with an additive feature inside it. A BaseFeature is neither
    # additive nor subtractive, and PartDesign's transform features refuse
    # to pattern one -- "Only additive and subtractive features can be
    # transformed". A tier-1 verb builds its object at the document root,
    # so `additive_box` alone leaves the feature outside the body and the
    # same commands answer "Selection is not in the active body";
    # `duplicate_object` is what puts a copy inside it. Authored for the
    # panel tier (GH #53).
    "body_additive": (["new_body", "additive_box 20 20 10",
                       "select AdditiveBox", "duplicate_object"],
                      "AdditiveBox001"),
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


# The state the harness restores before every command, in the order it has
# to happen in. `close!` drops the last command's scratch document, a fresh
# one is opened, and only then can Part's selection gate be lifted:
# `no_selection_filters` needs an active document and answers "is not
# available here" without one, which is how a first attempt at this left
# the gate standing.
#
# The gate is a mode and not a document. `vertex_selection` and its two
# siblings turn one on, closing the document does not clear it, and with
# one on `select Box` answers `= select Box` and selects nothing -- after
# which every command that needs a selection says "is not available here".
# One live sweep ran `Part_VertexSelection` at command 141 of 266 and
# charged the 20 commands after it with its consequences (GH #73).
PREPARE = ["close!", "new verify", "no_selection_filters"]

# Which of those lines may fail without the fixture having failed. There is
# nothing to close before the first command and, on most commands, no gate
# to lift. The document is not on the list: without one there is nothing to
# build the fixture in.
BEST_EFFORT = ("close!", "no_selection_filters")


def build_fixture(lines, run=None):
    """A scratch document holding the fixture, ready to be consumed.

    ``lines`` is the recipe and the `select` that hands it over. The
    ``PREPARE`` runs first, and two of its three lines are best-effort:
    there is nothing to close before the first command and usually no
    selection gate to lift. Every other line must succeed -- an
    operand the harness could not present is the harness's failure, not
    the command's, so the caller records `no_fixture` rather than blaming
    the verb.

    Returns (ok, detail); the detail names the line that faulted.
    """
    run = run or _exec
    for line in PREPARE + list(lines):
        code, _out, err = run(line)
        if code != 0 and line not in BEST_EFFORT:
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


def select_half(example):
    """The setup half of a two-part selection example (ADR-200).

    The other side of `verb_line`: `select Box, Box001; part_cut` is one
    line a person types as two, and this is the first of them -- what puts
    the operands in place before the verb is judged. A one-part example
    has no setup half and answers "".
    """
    select, sep, _verb = (example or "").partition(";")
    return select.strip() if sep else ""


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

    Invalidity outranks the exit code, which is the other way round from
    how this read before GH #57. The engine now reports an object FreeCAD
    rejected as an error of its own, so a non-zero exit is what an invalid
    run looks like from out here, and reading the code first would have
    filed all fourteen named instances as `broken` -- the vaguer of the
    two answers, and the one that does not name the object. A run that
    also raised keeps its message: `verify_one` puts anything stderr said
    beyond the rejection into the detail.
    """
    if code == 75:
        return "busy"
    if panel:
        return "panel"
    if engine != "idle":
        return "incomplete"
    if invalid:
        return "invalid"
    if code != 0:
        return "broken"
    return "ok"


def _invalid(snap):
    active = next((d for d in snap.get("documents") or []
                   if d.get("active")), {})
    return active.get("invalid") or []


# The engine's own word for a command it abandoned mid-line. A token at a
# step that will not parse as that step's value, but does match a verb's
# name, cancels the command and starts that verb instead: `loft standard`
# answers "loft cancelled" and runs `standard_views` (GH #72). When the verb
# it escaped to takes no steps, the line exits 0 with the engine idle and
# nothing invalid -- every reading `classify` makes says the command
# verified, and this line is the only thing that says otherwise. It is what
# earned `subtractive_pipe standard constant transformed` an `ok` for
# running a view command.
_CANCELLED = re.compile(r"^(\S+) cancelled\s*$", re.M)


def cancelled_in(out):
    """The command the engine says it abandoned while running this line.

    Read rather than matched against the verb that was typed, because a
    verb may be reached by an abbreviation (ADR-301) and the engine names
    what it cancelled by its full name. One line is run at a time, so any
    cancellation in it is this line's.
    """
    hit = _CANCELLED.search(out or "")
    return hit.group(1) if hit else ""


# The tail of the engine's own word for an object FreeCAD rejected (GH
# #57). The engine reports it as an error, so an invalid run exits
# non-zero as a matter of course and stderr carries this line.
_REJECTION = "the result is not usable"


def rejection_only(err):
    """Whether the engine's invalidity report is all stderr had to say.

    A run that only left something invalid says so and nothing else, and
    the object names are the whole diagnosis. A run that *raised* and left
    something invalid has `<verb> failed: ...` on stderr as well, and that
    is what the reader needs -- filing it under `invalid` must not swallow
    it.
    """
    lines = [ln for ln in (err or "").splitlines() if ln.startswith("error:")]
    return bool(lines) and all(_REJECTION in ln for ln in lines)


def verify_one(example):
    """Run one example, classify what happened. Leaves the engine idle.

    Invalidity is judged on the delta: what this run made invalid, not
    what it found already broken. An invalid run is undone, so one bad
    example cannot mark every example after it.
    """
    fccli("cancel")                       # clear whatever the last one left
    before = _invalid(_snapshot())
    code, out, err = fccli("exec", example)
    snap = _snapshot()
    fresh = [n for n in _invalid(snap) if n not in before]
    result = classify(code, snap.get("engine") or "",
                      snap.get("panel"), fresh)
    if result in ("incomplete", "panel"):
        fccli("cancel")
    if result == "invalid":
        fccli("exec", "undo")
    abandoned = cancelled_in(out)
    if abandoned and result != "busy":
        # The engine dropped the command under test, so no reading after
        # that is about it -- the same argument `blocked` makes. `busy` is
        # left alone because nothing of this line ran at all.
        return "cancelled", (f"the engine cancelled {abandoned}; what ran "
                             f"was another verb this line's own arguments "
                             f"matched (GH #72)")
    if result == "invalid":
        extra = "" if rejection_only(err) else err
        return result, ", ".join(fresh) + (f"; {extra}" if extra else "")
    return result, (err if result in ("incomplete", "broken") else "")


# ----------------------------------------------------------------- panels

# A panel command is not a dead end. It opens a task panel, the engine
# offers that panel's fields as one repeating `name=value` step, and
# `done` applies what was set (GH #53). Three of the engine's own answers
# are all this tier needs to drive one:
#
#   the panel's fields   listed when it opens, and again in the complaint
#                        when a name is not on it
#   `done` in options    the step that takes assignments is the one that
#                        offers `done`, so the state says whether a panel
#                        is being driven or merely showing
#   the delta-invalidity read (C3), unchanged from the selection tier
#
# Nothing here is written per command, for the same reason panels.py has
# nothing per command: a panel names its own fields.

# A name no .ui file gives a widget. Typed at a panel, it makes the engine
# answer with the names the panel does have -- a question asked by getting
# it wrong on purpose, which is the mechanism GH #53 names.
PROBE_NAME = "__fccli_probe"

# `panels.offered` caps the complaint at six names and glues an ellipsis
# to the sixth, so the probe alone under-reports a wide panel. The block
# the engine prints when the panel opens carries all of them. Both are
# read: the probe because it is the answer to a question, the block
# because it is complete.
_ANNOUNCED = re.compile(r"^\s*\d+ to set(?: now)?:\s*$")
_NOT_ON_PANEL = re.compile(r"is not on this panel -- (.+?)\s*$")
# Mirrors panels.ASSIGNMENT, and for the same reason: no space before the
# `=` is what tells `radius=3`, which is an assignment, from the `A = north`
# inside `label=Wall A = north`, which is prose. A copy rather than an
# import because nothing in this file may import FreeCAD's Qt.
_ASSIGNMENT = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=")


def split_pairs(example):
    """A panel draft, split into the verb and the fields it sets.

    `part_fillet filletstartradius=3` is one line a person can type and
    history can recall, and it is also the two things this tier does in
    turn: run the verb, then set that field. A value runs to the next
    `name=` or to the end of the line, because a value can hold spaces --
    `3/4 in`, `Center of mass / centroid`.
    """
    text = example or ""
    marks = list(_ASSIGNMENT.finditer(text))
    if not marks:
        return text.strip(), []
    pairs = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        pairs.append((mark.group(1), text[mark.end():end].strip()))
    return text[:marks[0].start()].strip(), pairs


def announced_fields(text):
    """The names from the block the engine prints when a panel opens.

    `3 to set:` and then the names in padded columns, which is the whole
    list however wide the panel is. The heading is followed by indented
    rows and then by the unindented hint line, which ends the block.
    """
    names, reading = [], False
    for line in (text or "").splitlines():
        if _ANNOUNCED.match(line):
            reading = True
            continue
        if not reading:
            continue
        if not line.startswith((" ", "\t")) or not line.strip():
            reading = False
            continue
        names.extend(line.split())
    return names


def probed_fields(text):
    """The names from the complaint, and whether it kept some back.

    A complaint listing more than six ends in an ellipsis glued to the
    sixth name, so the caller is told the list is short rather than
    left believing a panel has six fields when it has eight.
    """
    hit = _NOT_ON_PANEL.search(text or "")
    if not hit:
        return [], False
    listed = hit.group(1).strip()
    short = listed.endswith("...")
    names = [n.strip() for n in listed.rstrip(".").split(",")]
    return [n for n in names if n], short


def _fault(err):
    """The first thing the engine called an error, without its prefix.

    A run at a panel step answers on stderr with the fault, if there was
    one, and then `incomplete: still wants name=value` either way -- so
    the presence of an `error:` line is what tells a written field from a
    refused one.
    """
    for line in (err or "").splitlines():
        if line.startswith("error: "):
            return line[len("error: "):].strip()
    return ""


def panel_fields(run, out):
    """What this panel answers to, asked of the engine two ways.

    ``out`` is what the verb printed, which holds the announced block.
    The probe is sent regardless: it is the answer to a question rather
    than a reading of a notice, and on a narrow panel the two agree,
    which is worth knowing when they stop agreeing.
    """
    announced = announced_fields(out)
    _code, _out, err = run(f"{PROBE_NAME}=1")
    probed, short = probed_fields(err)
    if short or len(announced) > len(probed):
        # The block is the complete list; the complaint is capped at six.
        return sorted(set(announced) | set(probed))
    return sorted(set(probed) | set(announced))


def _cancel():
    return fccli("cancel")


def cleared(snapshot, cancel, tries=3):
    """Close whatever panel is up, and confirm it is really gone.

    Asking is not enough. `Mesh_FromPartShape` opens a Tessellation panel
    that neither `done` nor `cancel` closes, and every command after it
    was answered "a dialog is already open in the task panel" or reported
    inactive -- 17 of them, in one live sweep, every one recorded against
    the wrong command. So the harness confirms, and a panel that will not
    close becomes a fact about the instance rather than about whatever
    ran next.
    """
    for _ in range(tries):
        cancel()
        if not snapshot().get("panel"):
            return True
    return False


def verify_panel(example, run=None, snapshot=None, cancel=None):
    """Drive one panel draft: open, set what it names, `done`.

    A verb the engine abandoned mid-line (GH #72) reaches this tier as
    `no_panel`, since a cancelled verb opens no panel, so the read
    `verify_one` makes is not repeated here.

    C1 for panels. The verb runs on its own, the panel's fields are read
    off the engine, the draft's `name=value` pairs are set one at a time
    so a refused name is attributed to the pair that was refused, and
    `done` applies it. What the run left is judged by the same
    delta-invalidity read as every other tier (C3).

    Returns (result, detail, extra). ``extra`` carries the field names the
    panel answered with, which is the half of GH #50 the mode map does not
    have yet, and which is what makes a refused name diagnosable.

    Beyond the shared vocabulary this tier says five more things:

        no_panel     the verb ran and no panel opened -- the mode map
                     calls this command a panel command and the verb is
                     not one
        mouse_panel  a panel opened that the command line cannot drive:
                     nothing to type into, or no way to finish. The
                     engine says which; either way it is a mode, and the
                     harness closes it
        bad_field    the draft named a field the panel does not have. The
                     detail is the engine's complaint, which names the
                     fields it does have
        stuck_panel  a panel that would not close, whatever was pressed.
                     Every command after one of those is answered as
                     though it were the one at fault, so the sweep
                     restarts on it
        blocked      one of those was still up when this ran, so nothing
                     here is about this command. Retried by a later sweep

    No path leaves a panel on screen without saying so (C4). One is
    closed on the way in, because a panel left by anything else would be
    adopted by the next verb typed; one is closed again on any ending
    that is not a clean apply; and a close is confirmed rather than
    assumed, so a panel that will not close is reported instead of being
    charged to whatever ran next.
    """
    run = run or _exec
    snapshot = snapshot or _snapshot
    cancel = cancel or _cancel

    def close_out(result, detail, extra):
        """Leave nothing open, and say plainly when that failed (C4)."""
        if cleared(snapshot, cancel):
            return result, detail, extra
        said = f"{result}: {detail}" if detail else result
        return "stuck_panel", f"{said}; and the panel would not close", extra

    if not cleared(snapshot, cancel):
        # Something before this left a panel nothing can close, and every
        # command run against it is answered as though it were the one at
        # fault. This one has not been judged at all, which is a different
        # thing from having failed: the sweep restarts, and a later pass
        # runs it on an instance where the answer means something.
        return ("blocked",
                "a panel left open before this command would not close", {})
    before = _invalid(snapshot())
    verb, pairs = split_pairs(verb_line(example))
    code, out, err = run(verb)
    if code == 75:
        # The floor or a dialog belongs to somebody else. Nothing here
        # opened it, so nothing here closes it.
        return "busy", "", {}
    snap = snapshot()
    engine = snap.get("engine") or ""
    options = snap.get("options") or []
    # The step that takes assignments is the one that offers `done`. A
    # verb still collecting something else has not opened a panel, and a
    # panel showing with the engine idle is not being driven by anything.
    if engine != "collecting" or "done" not in options:
        return _without_panel(snap, code, err, before, close_out)
    fields = panel_fields(run, out)
    extra = {"fields": fields}
    for name, value in pairs:
        code, out, err = run(f"{name}={value}")
        if code == 75:
            return close_out("busy", "", extra)
        fault = _fault(err)
        if fault:
            # `is not on this panel` is the engine naming the names it
            # does have; anything else is the value being refused.
            kind = ("bad_field" if "is not on this panel" in fault
                    else "broken")
            return close_out(kind, fault, extra)
        # A choice can swap the page under whatever comes next, and the
        # engine re-announces when it does.
        for name_now in announced_fields(out):
            if name_now not in fields:
                fields.append(name_now)
    code, out, err = run("done")
    snap = snapshot()
    fresh = [n for n in _invalid(snap) if n not in before]
    result = classify(code, snap.get("engine") or "",
                      snap.get("panel"), fresh)
    if result in ("incomplete", "panel", "busy"):
        # `done` did not finish it. Whatever is still up is not the next
        # command's to inherit.
        return close_out(result, (_fault(err) or err), extra)
    if result == "invalid":
        run("undo")
        return result, ", ".join(fresh), extra
    if result == "broken":
        return result, (_fault(err) or err), extra
    return result, "", extra


def _without_panel(snap, code, err, before, close_out):
    """What to say when the verb did not end up at a panel step.

    Two answers, and the difference matters to GH #50. A verb that opened
    no panel is a command the mode map has in the wrong tier -- including
    one still collecting something that is not a panel field, which is a
    positional verb the mode map called a panel. A panel that opened with
    nothing to type into, or with no way to finish, is a mode; the
    engine's own words for both are in panels.py. The detail carries what
    the verb did either way: the fault it was refused with, the object it
    left invalid, or that it simply ran.
    """
    engine = snap.get("engine") or ""
    if snap.get("panel"):
        return close_out("mouse_panel",
                         (_fault(err) or
                          "a panel with no way in from here"), {})
    if engine == "collecting":
        return close_out("no_panel",
                         f"no panel; still wants {snap.get('prompt')}", {})
    fresh = [n for n in _invalid(snap) if n not in before]
    inner = classify(code, engine, False, fresh)
    if inner == "invalid":
        return "no_panel", f"no panel; left invalid: {', '.join(fresh)}", {}
    if inner == "broken":
        return "no_panel", f"no panel; {_fault(err) or err}", {}
    return "no_panel", "no panel; the verb ran to completion", {}


# Panels this tier must not press OK on. Not hazards -- none of them
# harms the instance -- but each applies outside the document it was run
# in, and the harness has no business writing those: a style panel writes
# FreeCAD's own preferences, which are FreeCAD's (docs/conventions.md),
# and a post-processor writes a file to a path somebody chose. Punted with
# the reason, so the accounting still answers for them.
PANEL_OFF_LIMITS = {
    "Draft_SetStyle": "applies Draft's default style preferences, which "
                      "are the operator's",
    "Draft_SelectPlane": "writes the working plane and its grid "
                         "preferences, which are the operator's",
    "CAM_Post": "writes a G-code file to a chosen path",
    "CAM_ExportTemplate": "writes a job template file to a chosen path",
}


def panel_operands(cid, entry):
    """What a panel command's operands are, if it needs any.

    Returns (lines, gives, why_not). ``lines`` of None is a punt and
    ``why_not`` says which: a panel that applies outside its document, a
    `panel_fixture` naming nothing, or a hint this tier cannot build.
    ``gives`` of None with no lines is a panel that asks for no operands
    -- a scratch document, and nothing in it.

    Shared by the panel tier and the mode-routed ledger, because the two
    ask the same question of the same mode map entry and must not answer
    it two ways.
    """
    off_limits = PANEL_OFF_LIMITS.get(cid)
    if off_limits:
        return None, None, off_limits
    authored = entry.get("panel_fixture")
    if authored:
        if authored not in FIXTURES:
            return None, None, f"panel_fixture names no fixture: {authored}"
        lines, gives = FIXTURES[authored]
        return list(lines), gives, ""
    if entry.get("needs_selection"):
        name, lines, gives = fixture_for(cid, entry.get("selection_hint"))
        if name is None:
            return None, None, gives  # with no fixture, that slot is the reason
        return list(lines), gives, ""
    return [], None, ""


def panel_targets(modemap):
    """What the panel tier drives, and what it cannot.

    Returns (targets, fixtures, punted), the same three the selection
    tier returns. A panel command that names operands gets the selection
    tier's fixture for them, because many need one -- a fillet needs a
    solid with an edge selected before its panel has anything to fillet.
    One that names none is driven in a scratch document of its own and
    nothing else.

    A command the mode map drafted no `name=value` pairs for is still
    driven: the verb, the fields the panel answers with, and `done`. That
    is C1 without parameters, and it is worth more than a punt -- it says
    whether the panel opens, what it offers and whether it applies, for
    every panel command rather than only the drafted ones. Parameters
    need a draft, so the report says which commands had one.

    An authored draft may name its fixture outright with `panel_fixture`,
    a key in FIXTURES. A panel takes its operands from the selection like
    any other command, but the mode map's `needs_selection` was
    classified from the wiki and is wrong where a panel asks for operands
    the page does not mention -- Part_Fillet's page describes a dialog and
    the dialog fillets nothing unless an edge was selected first. Naming
    the fixture is the authored answer to that, and it leaves the
    classification it disagrees with legible instead of overwriting it.
    """
    targets, fixtures, punted = {}, {}, {}
    for cid, entry in modemap["commands"].items():
        if entry.get("mode") != "panel":
            continue
        lines, gives, why = panel_operands(cid, entry)
        if lines is None:
            punted[cid] = why
            continue
        draft = (entry.get("example") or "").strip()
        verb = (entry.get("verb") or "").strip()
        if not draft and not verb:
            punted[cid] = "the mode map named no verb to run"
            continue
        line = draft or verb
        if gives is None:
            targets[cid] = line
            fixtures[cid] = []       # a scratch document, and nothing in it
            continue
        select = f"select {gives}"
        targets[cid] = f"{select}; {line}"
        fixtures[cid] = lines + [select]
    return targets, fixtures, punted


# ------------------------------------------------------------ the ledger

# The modes the harness drives. The fourth ADR-501 names, `manual`, is a
# person's: the harness records what they confirmed and drives nothing.
DRIVEN_MODES = ("positional", "selection", "panel")


def drive(mode, example, positional=None, panel=None):
    """Run one authored example the way its mode is driven.

    The mode map answers which (GH #50). A positional example is the whole
    line and runs bare. A selection example's operands were built and
    selected by the setup, so what is left to judge is the verb half
    (ADR-200) -- driving the whole line would run `select` twice and judge
    the select rather than the verb. A panel example goes through the
    panel step: the verb, the fields the panel answers with, the draft's
    `name=value` pairs, and `done` (GH #53).

    This is the whole of what `make verify` gained: before it, every
    example ran bare, so a selection example judged its own `select` line
    and a panel example was recorded `panel` for opening the panel it is
    supposed to open.

    A mode with no route here is refused rather than driven bare. Nothing
    reaches it today -- `ledger_targets` punts `manual` and every mode it
    does not know before a target is made -- but driving an unrouted mode
    bare is the exact bug this function was extracted to make visible, and
    a fifth mode added to the map later would inherit it in silence.
    """
    positional = positional or verify_one
    panel = panel or verify_panel
    if mode == "panel":
        return panel(example)
    if mode == "selection":
        return positional(verb_line(example))
    if mode == "positional":
        return positional(example)
    raise ValueError(
        f"no way to drive a {mode!r} command: the ledger drives "
        f"{', '.join(DRIVEN_MODES)} and punts everything else, so a mode "
        f"arriving here is one nothing routes")


def ledger_targets(commands, modemap, tier=None):
    """What `make verify` drives, and in which mode.

    ``commands`` is the dictionary's, so the examples are the authored
    ones: the ledger is a record of authored examples and nothing else
    (ADR-501), and the drafts belong to `modemap_sweep.json`. ``modemap``
    is {cid: entry} and says how each is driven.

    Returns (targets, fixtures, modes, punted). ``fixtures`` is the setup
    a command needs before its example -- the recipe lines and the
    `select` that hands them over, empty for a positional one. ``modes``
    is the mode every target and every punt was read in, which is what the
    ledger stamps. ``punted`` is {cid: reason} for an authored example the
    harness cannot drive on its own: a selection or panel hint whose
    operands this vocabulary does not build, or a mode that is a person's
    to confirm.

    A selection example's setup ends with the example's own `select` half,
    not with the fixture's canonical one, so the example is driven exactly
    as it is written. A `select` naming something the recipe did not build
    is `no_fixture` with the line that faulted -- which is the disagreement
    said out loud rather than papered over by substituting a select that
    works.
    """
    targets, fixtures, modes, punted = {}, {}, {}, {}
    for cid, entry in commands.items():
        example = (entry.get("example") or "").strip()
        if not example:
            continue
        spec = modemap.get(cid) or {}
        # A command the mode map does not classify is driven the way the
        # ledger drove every command before the mode map existed: bare.
        mode = spec.get("mode") or "positional"
        if tier and mode != tier:
            continue
        modes[cid] = mode
        if mode == "positional":
            targets[cid], fixtures[cid] = example, []
            continue
        if mode == "selection":
            name, lines, gives = fixture_for(cid, spec.get("selection_hint"))
            if name is None:
                punted[cid] = gives
                continue
        elif mode == "panel":
            lines, gives, why = panel_operands(cid, spec)
            if lines is None:
                punted[cid] = why
                continue
        else:
            punted[cid] = (f"mode {mode}: a person confirms this one and the "
                           f"harness records it (ADR-501)")
            continue
        select = select_half(example) or (f"select {gives}" if gives else "")
        targets[cid] = example
        fixtures[cid] = list(lines) + ([select] if select else [])
    return targets, fixtures, modes, punted


def ledger_hooks(fixtures, modes, build=None, route=None):
    """The two hooks a mode-routed ledger sweep gives `sweep`.

    Extracted so the wiring itself is checkable. A `run_one` that ignored
    the mode would drive every example bare and stamp the result as
    verified -- which is the state GH #54 found: a selection example
    judging its own `select` line, a panel example recorded `panel` for
    opening the panel it exists to open.
    """
    build = build or build_fixture
    route = route or drive
    return {"setup": lambda cid: build(fixtures[cid]),
            "run_one": lambda cid, example: route(modes[cid], example)}


def punt_result(mode):
    """What a command the harness did not drive is recorded as.

    A hint whose operands this vocabulary cannot build is the harness's
    own gap: `no_fixture`, which a later sweep with a wider vocabulary
    retries. A mode only a person can confirm is not a gap at all -- it is
    `manual`, ADR-501's fourth mode, and it stands until a person answers
    it.
    """
    return "no_fixture" if mode in DRIVEN_MODES else "manual"


def by_mode(entries):
    """The ledger, counted by mode and result.

    A ledger of one number says how much is verified; a ledger of nine
    says what kind of verification each part of it is. A selection `ok` and
    a positional `ok` are different facts, and the campaign is spent
    moving commands between them, so the tally that answers for it is the
    two-way one. The modes come out in ADR-501's order -- positional,
    selection, panel, then what neither drives.
    """
    counts = {}
    for entry in entries.values():
        key = (entry.get("mode") or "-", entry.get("result") or "-")
        counts[key] = counts.get(key, 0) + 1
    order = {m: i for i, m in enumerate(DRIVEN_MODES)}
    return [f"{mode:11} {result:11} {n}"
            for (mode, result), n in
            sorted(counts.items(),
                   key=lambda kv: (order.get(kv[0][0], len(order)), kv[0][0],
                                   -kv[1], kv[0][1]))]


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


def resumable(targets, entries, version=None, modes=None):
    """Which targets a resumed sweep still runs.

    A result already recorded for the same example is an answer and
    stands -- except `busy`, the floor's state rather than the draft's,
    and `no_fixture`, the harness's own gap rather than the command's,
    both of which are retried -- as is `blocked`, a command a panel left
    by something else stood in front of, which is no answer about the
    command at all; and `hazard`, which stays in the targets so plan()
    reports the skip.

    ``version`` is the FreeCAD this sweep is about to run against. It is
    what makes the ledger resumable without freezing it: an entry stamped
    against an older FreeCAD is stale (ADR-501) and runs again, so a sweep
    stopped halfway resumes where it stopped and a sweep after an upgrade
    starts over. ``modes`` is the mode each target is driven in now; an
    entry recorded in a different one -- or in none, which is every entry
    a mode-blind sweep wrote -- asserts something about a driving that no
    longer happens, and runs again too.
    """
    again = ("hazard", "busy", "no_fixture", "blocked")
    todo = {}
    for cid, example in targets.items():
        entry = entries.get(cid) or {}
        if (entry.get("example") != example
                or entry.get("result") in again
                or (version is not None and entry.get("freecad") != version)
                or (modes is not None and entry.get("mode") != modes.get(cid))):
            todo[cid] = example
    return todo


def plan(targets, prior, force=False, start_at=None):
    """Split targets into what this sweep runs and what it skips.

    ``prior`` is the record of earlier sweeps, {cid: entry}. A command in
    KNOWN_HAZARDS or recorded `hazard` is skipped; --force runs it anyway.
    A command in WRITES_SETTINGS is skipped even then: --force answers for
    the instance, and this one answers for the operator's parameters.
    """
    run, skipped = {}, {}
    for cid, example in sorted(targets.items()):
        if start_at and cid < start_at:
            continue
        if cid in WRITES_SETTINGS:
            skipped[cid] = WRITES_SETTINGS[cid]
            continue
        reason = KNOWN_HAZARDS.get(cid)
        if reason is None and prior.get(cid, {}).get("result") == "hazard":
            reason = prior[cid].get("detail", "recorded hazard")
        if reason and not force:
            skipped[cid] = reason
            continue
        run[cid] = example
    return run, skipped


def precondition(snap):
    """Why this instance cannot be swept, if it cannot.

    Two different failures used to share one message. An instance that
    never came up answers nothing at all, and `"panel" not in {}` is true,
    so a start that failed was reported as a FreeCAD too old to report
    panel facts -- which sent the reader to the addon rather than to the
    start. One check tells them apart.
    """
    if not snap:
        return ("no answer from the instance -- it may not have come up; "
                "`fccli ls` says what is running")
    if "panel" not in snap:
        return ("this FreeCAD predates ADR-302 and cannot report panel or "
                "validity facts -- restart it with the current addon")
    return None


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


def _quit():
    """Shut this instance down, and wait until it is gone."""
    fccli("cancel")
    fccli("exec", "quit!")
    for _ in range(20):
        if not running():
            return True
        time.sleep(0.5)
    return False


def _restart_owned(owned):
    """The sweep's restart hook: ownership is a fact the restart updates.

    An instance this sweep started, first or mid-sweep, is quit at the
    end; one it merely reused belongs to whoever started it, and `quit!`
    against a reused instance discards their unsaved documents.

    A panel that will not close is not a wedge, and `_restart` is built
    for wedges: an instance that still answers is reused, which is right
    when the old one is unreachable and wrong here, because this one
    answers every question and refuses every command. Live, that reuse
    turned 9 commands that each left such a panel into 90 results -- 81
    of them commands that never ran. So an instance the sweep started is
    quit and replaced. One it borrowed is not the sweep's to quit, and
    the sweep stops rather than filling a report with the same fact 80
    times.
    """
    if running() and _snapshot().get("panel") and not cleared(_snapshot,
                                                              _cancel):
        if not owned.get("it"):
            print("verify: a panel is open that will not close, and this "
                  "FreeCAD is not the sweep's to quit", file=sys.stderr)
            return False
        _quit()
    ok, started_new = _restart()
    if started_new:
        owned["it"] = True
    return ok


# Results after which the instance is no longer fit to judge the next
# command. A hazard took it down or wedged it; a stuck panel stands
# between every later command and FreeCAD, and is not the next command's
# fault however much it looks like it; `blocked` is a command that ran
# against exactly that and so was never judged.
RESTART_AFTER = ("hazard", "stuck_panel", "blocked")


def sweep(targets, record, run_one=None, alive=None, healthy=None,
          restart=None, setup=None, restart_every=None):
    """Run every target, restart a dead or wedged instance, checkpoint
    each result.

    ``record(cid, example, result, detail, extra)`` is called after
    every command, hazards included -- it owns persistence, so a stopped
    sweep keeps everything already run. ``run_one(cid, example)`` answers
    (result, detail) or (result, detail, extra) -- it takes the command id
    because a mode-routed sweep drives one command one way and the next
    another, and the mode is the command's; ``extra`` is what the tier learned
    that is neither of those, and the panel tier puts the field names the
    panel answered with there. ``setup(cid)`` prepares what the
    command needs and returns (ok, detail); the selection tier builds its
    fixture there. A setup that fails on a healthy instance is
    `no_fixture` and the sweep moves on; one that fails because the
    instance is gone is a hazard like any other. The hooks default to the
    real client; they exist so this loop is testable without a FreeCAD.

    A result that is not `ok` records `after`: the command this instance
    ran before it, or None when the instance was fresh. That is what turns
    "it failed late in the sweep" into a name to try, and it is the only
    way the report can tell an order-dependent failure from a property of
    the command.

    ``restart_every`` starts a fresh instance after every N commands.
    Something in a long sweep breaks a fixture: in one 136-command panel
    sweep, `upgrade` stopped joining four lines into a wire (exit 0,
    nothing built) and a body stopped being the active body, and both
    worked again on a fresh instance. The cause is not known. Command
    volume is not it -- 40 builds of that recipe and five workbench
    borrows on one instance, 330 commands deep, reproduced none of it
    (PR #70 review) -- so the likelier shape is residue from one
    particular command. A bounded lifetime is what makes a reading
    reproducible while that is open; it is off unless asked for, because
    a sweep that restarts constantly cannot see the effect at all.

    Returns (tally, finished, restarts).
    """
    run_one = run_one or (lambda _cid, example: verify_one(example))
    alive = alive or running
    healthy = healthy or _healthy
    restart = restart or _restart
    tally, restarts = {}, 0
    total = len(targets)
    # The last command this instance ran. A result that is not `ok` and
    # that a rerun on a fresh instance passes was broken by something, and
    # the thing that ran before it is the first place to look. The sweep
    # has the ordering, so it can name that command instead of leaving
    # "the instance was old" standing as an explanation. None means
    # nothing preceded it -- the instance was fresh.
    previous = None

    def note(cid, example, result, detail, extra=None):
        if result != "ok":
            extra = dict(extra or {}, after=previous)
        record(cid, example, result, detail, extra)
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
                    previous = None          # a fresh instance, nothing before
                    continue
                note(cid, example, "no_fixture", why)
                print(f"[{i}/{total}] {'no_fixture':10} {cid}  ({why})",
                      flush=True)
                previous = cid               # the recipe ran, so it counts
                continue
        extra = None
        try:
            # Two values or three: a tier with nothing extra to say keeps
            # the shorter contract.
            result, detail, *rest = run_one(cid, example)
            extra = rest[0] if rest else None
        except subprocess.TimeoutExpired:
            result, detail = "hazard", "client timed out; instance wedged"
        if result not in RESTART_AFTER:
            try:
                if not healthy():
                    result = "hazard"
                    detail = ("left the instance unresponsive" if alive()
                              else "killed the FreeCAD instance")
            except subprocess.TimeoutExpired:
                result, detail = "hazard", "left the instance unresponsive"
        note(cid, example, result, detail, extra)
        if result in RESTART_AFTER:
            print(f"[{i}/{total}] {result:10} {cid} -- restarting FreeCAD",
                  flush=True)
            restarts += 1
            if not restart():
                print("verify: restart failed, stopping", file=sys.stderr)
                return tally, False, restarts
            previous = None
            continue
        print(f"[{i}/{total}] {result:10} {cid}  ({example})", flush=True)
        previous = cid
        if restart_every and i % restart_every == 0 and i < total:
            restarts += 1
            if not restart():
                print("verify: restart failed, stopping", file=sys.stderr)
                return tally, False, restarts
            previous = None
    return tally, True, restarts


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Verify command examples (ADR-501).")
    ap.add_argument("--only", help="verify one command id, e.g. Part_Box")
    ap.add_argument("--modemap", action="store_true",
                    help="drive the mode map's drafts instead, recording to "
                         "modemap_sweep.json; the tree and the ledger are "
                         "untouched")
    ap.add_argument("--tier", choices=DRIVEN_MODES, default=None,
                    help="one mode only: positional runs the example alone, "
                         "selection builds the fixture the hint names and "
                         "selects it first, panel runs the verb and then "
                         "drives the task panel it opens with name=value and "
                         "done. A --modemap sweep defaults to positional, "
                         "since its tiers are driven one at a time; the "
                         "ledger defaults to every mode the mode map names")
    ap.add_argument("--start-at", metavar="COMMAND",
                    help="skip every command id before this one")
    ap.add_argument("--force", action="store_true",
                    help="run commands recorded as hazards")
    ap.add_argument("--restart-every", type=int, metavar="N",
                    help="start a fresh instance after every N commands. "
                         "Something in a long sweep breaks a fixture that "
                         "works on a fresh instance -- cause open, see the "
                         "`after` field each failure records")
    args = ap.parse_args(argv)

    data = json.load(open(DICT))
    version = data.get("freecad")
    modemap = json.load(open(MODEMAP))
    fixtures, modes, punted = {}, {}, {}
    if args.modemap:
        tier = args.tier or "positional"
        source = modemap["commands"]
        if tier == "selection":
            targets, fixtures, punted = selection_targets(modemap)
        elif tier == "panel":
            targets, fixtures, punted = panel_targets(modemap)
        else:
            targets = {cid: e["example"] for cid, e in source.items()
                       if e.get("mode") == "positional" and e.get("example")}
        store_path = SWEEP_REPORT
        store = _load(store_path)
        entries = store
        prior = dict(entries)
        if not args.force:
            targets = resumable(targets, entries)
    else:
        source = data["commands"]
        targets, fixtures, modes, punted = ledger_targets(
            source, modemap["commands"], tier=args.tier)
        store_path = LEDGER
        store = _load(store_path)
        entries = store.setdefault("commands", {})
        prior = dict(entries)
        if not args.force:
            targets = resumable(targets, entries, version=version,
                                modes=modes)

    if args.only:
        targets = {k: v for k, v in targets.items() if k == args.only}
        punted = {k: v for k, v in punted.items() if k == args.only}

    run, skipped = plan(targets, prior, force=args.force,
                        start_at=args.start_at)
    for cid, reason in sorted(skipped.items()):
        print(f"  {'skipped':10} {cid}  ({reason})")

    today = datetime.date.today().isoformat()

    def record(cid, example, result, detail, extra=None):
        entry = {"example": example, "result": result}
        # What the tier learned beyond its verdict. The panel tier's field
        # names are the half GH #50 does not have, so they are kept even
        # when the draft that found them failed.
        entry.update(extra or {})
        if not args.modemap:
            entry["date"] = today
            entry["freecad"] = version
            # The mode is what the driving was, and the entry means
            # different things in each: ADR-501's schema has the field for
            # that reason, and the resume rule reads it back.
            if modes.get(cid):
                entry["mode"] = modes[cid]
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
    # So is a command the harness cannot drive on its own: the report
    # answers "why was this one not driven" for every command in the tier,
    # not just the ones the fixture vocabulary reaches. A mode only a
    # person can confirm is `manual`, not the harness's own gap.
    for cid, reason in punted.items():
        example = (source[cid].get("example") or "")
        record(cid, example, punt_result(modes.get(cid, "selection")), reason)
    if punted:
        print(f"  {len(punted)} commands were not driven; the report says "
              f"why for each")

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

    stopped = precondition(_snapshot())
    if stopped:
        print(f"verify: {stopped}", file=sys.stderr)
        return 3

    # The selection tier builds a fixture per command and judges only the
    # verb after it; the panel tier does the same and then drives the
    # panel the verb opens; the positional tier runs its example whole.
    #
    # A ledger sweep does all three in one pass, per command, because its
    # targets are of every mode at once -- which is the whole of GH #54's
    # ledger half. Every command gets a scratch document, positional ones
    # included: in a mixed sweep the command before this one may have built
    # a fixture, and a positional result that depends on which fixture
    # preceded it is not reproducible.
    hooks = {}
    if args.modemap and tier in ("selection", "panel"):
        one = (lambda _cid, example: verify_panel(example)) \
            if tier == "panel" \
            else (lambda _cid, example: verify_one(verb_line(example)))
        hooks = {"setup": lambda cid: build_fixture(fixtures[cid]),
                 "run_one": one}
    elif not args.modemap:
        hooks = ledger_hooks(fixtures, modes)

    owned = {"it": started}
    fccli("exec", "new verify")
    try:
        tally, finished, restarts = sweep(
            run, record, restart=lambda: _restart_owned(owned),
            restart_every=args.restart_every, **hooks)
    except KeyboardInterrupt:
        # The checkpoint is what makes this safe, so say what it holds
        # rather than leaving a traceback to be read as a lost sweep. The
        # instance still gets shut down: that is the `finally` below.
        print(f"\nstopped. {os.path.relpath(store_path, ROOT)} holds "
              f"{len(entries)} results -- run again to resume where this "
              f"stopped.", file=sys.stderr)
        return 130
    finally:
        if owned["it"] and running():
            fccli("cancel")
            fccli("exec", "quit!")

    summary = ", ".join(f"{n} {k}" for k, n in sorted(tally.items()))
    note = (f", {restarts} restart" + ("s" if restarts > 1 else "")
            if restarts else "")
    print(f"\n{len(run)} run, {len(skipped)} skipped ({summary}{note}). "
          f"{os.path.relpath(store_path, ROOT)}")
    if not args.modemap:
        # The whole ledger, not just this run's part of it: what the
        # campaign holds is the question the tally answers.
        for line in by_mode(entries):
            print(f"  {line}")
    return 0 if finished else 3


if __name__ == "__main__":
    sys.exit(main())
