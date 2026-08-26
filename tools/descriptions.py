#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The description spec, checked over the command tree (GH #48, of #47).

The spec's A group asks what a person reads before they type a command:

  A1  the summary is imperative, result-first, and names the inputs
  A2  the synopsis is the verb and its ordered positional arguments
  A3  the argument glosses are distinct and typed, options marked apart
  A4  the body is a faithful reference paragraph, rendered by `man`
  A5  an example is present, and shaped for the command's mode
  A6  siblings in a family agree -- learn box, predict cylinder

A2, A3, A5 and A6 are mechanical and live here. A1 and A4 are reading, and
what this module owes them is a record per command with the text in it:
`--report` writes that, and an agent grades it.

Nothing here models what a verb looks like. `fccli.factory` imports without
FreeCAD, so the registry is *built* and the rules read that. A second model
of step ordering would be a second thing to keep true.

What is built is the generated tier: tier 0, tier 1 and the families, with
no patches discovered (`PatchSet([])`), so the measurement is the tree's own
contribution rather than whichever addons this machine has installed.

The hand-authored typed verbs are not in it, and cannot be. `fccli.verbs`
and `fccli.shell` register into the module-global REGISTRY at import, and
both import FreeCAD at their first line, so there is no FreeCAD-free path
to that tier -- `box` is `corner length width height` there and
`Length Width Height` here. Rather than let a rule answer confidently about
a verb it is not looking at, the fourteen commands those two files claim
are read out of the source by name, and every rule whose answer depends on
step shape records `unread` for them and says so. A shape read live is #47's
runtime tier; this is the static one saying where its sight ends.

Two severities. A fault that silently changes what a command does is a
problem and fails the lint; a fault that wants a person's judgment, or that
the tree carries by the dozen today, is a report line. `--strict-descriptions`
promotes every report to a problem, which is how a workbench gets held to
the whole spec once it has been through it.
"""

import collections
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import command_files as cf  # noqa: E402

MODEMAP = os.path.join(ROOT, "fccli", "modemap.json")

# The two modules that register hand-authored verbs into the global
# REGISTRY at import time. Read as text, for their `gui_command="..."`:
# importing them needs FreeCAD, and writing down their steps here would be
# the second model of verb shape this module exists to avoid. A name is
# the least that can be borrowed, and it is enough to know where to stop.
AUTHORED_SOURCES = (os.path.join(ROOT, "fccli", "verbs.py"),
                    os.path.join(ROOT, "fccli", "shell.py"))
CLAIMS = re.compile(r"""gui_command\s*=\s*["']([A-Za-z_0-9]+)["']""")

# Modes the classification workflow assigns (GH #50). Only `positional`
# takes arguments on the line; the rest are driven by a selection, a task
# panel, or the mouse.
TYPED_MODE = "positional"


def load_modemap(path=MODEMAP):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("commands") or {}
    except (OSError, ValueError):
        return None


def authored_commands(sources=AUTHORED_SOURCES):
    """Commands a hand-written verb owns, by name.

    Empty is not a safe answer -- it would put every one of them back
    under a rule that cannot see them -- so a source that will not read is
    raised rather than shrugged off.
    """
    found = set()
    for path in sources:
        with open(path, encoding="utf-8") as fh:
            found.update(CLAIMS.findall(fh.read()))
    if not found:
        raise ValueError(f"no gui_command= in any of {sources}: the "
                         f"hand-authored tier moved and the rules that "
                         f"stop at it would run over it instead")
    return found


def build_registry(descriptor, dictionary):
    """The verbs the tree produces, without FreeCAD and without patches.

    Returns None when fccli will not import -- the rules then report that
    they did not run rather than passing vacuously.
    """
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        from fccli.grammar import Registry
        from fccli.factory import register_all
        from fccli.patches import PatchSet
    except Exception:
        return None
    registry = Registry()
    register_all(registry, descriptor=descriptor, tier0=True,
                 patches=PatchSet([]), dictionary=dictionary)
    return registry


def _families_of(descriptor, dictionary):
    from fccli.families import families, overrides_of
    over, exclude = overrides_of(dictionary)
    return families(descriptor["commands"], overrides=over, exclude=exclude)


def synopsis(verb):
    """The SYNOPSIS line `man` prints, as one string."""
    parts = [verb.name]
    for step in verb.steps:
        token = f"<{step.id}>"
        parts.append(f"[{token}]" if step.optional else token)
        if step.repeat:
            parts.append("...")
    return " ".join(parts)


def arity(verb):
    """(fewest, most) arguments the synopsis takes.

    Most counts the inline options too: `cylinder 12 40 angle` is three
    tokens against two steps, and that is the grammar working.
    """
    required = sum(1 for s in verb.steps if not s.optional)
    if any(s.repeat or getattr(s, "raw", False) for s in verb.steps):
        # A repeating step takes as many as it is given and a raw one
        # takes the rest of the line: no upper bound to measure against.
        return required, None
    return required, len(verb.steps) + sum(len(s.options) for s in verb.steps)


def _norm(text):
    """A gloss, compared the way a reader compares two of them: case,
    punctuation and spacing are not the difference between them."""
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


class Findings:
    """Problems fail the lint; reports are for a person to read."""

    def __init__(self):
        self.problems = []
        self.reports = []
        self.records = {}
        self.families = {}
        self.types = {}
        self.by_file = {}

    def problem(self, where, text, rule):
        self.problems.append(f"{where}: {text} ({rule})")
        self._note(where, rule, "fail", text)

    def report(self, where, text, rule):
        self.reports.append(f"{where}: {text} ({rule})")
        self._note(where, rule, "report", text)

    def member(self, commands, rule, text):
        """A family's finding, recorded against the members it names."""
        for name in commands:
            record = self.records.get(name)
            if record is None:
                continue
            record["notes"].append(f"{rule}: {text}")
            if record["checks"].get(rule) != "fail":
                record["checks"][rule] = "report"

    def typed(self, tid, rule, verdict, text):
        """A finding about a type, for the types with no command file to
        land in -- Part::Wedge and Part::Helix are tuned in a
        _types.yaml, and a problem invisible in the record is a problem
        the campaign reads the file and misses."""
        entry = self.types.setdefault(tid, {"notes": [], "verdict": "pass"})
        entry["notes"].append(f"{rule}: {text}")
        if entry["verdict"] != "fail":
            entry["verdict"] = verdict

    def _note(self, where, rule, verdict, text):
        record = self.by_file.get(where)
        if record is None:
            return
        record["notes"].append(f"{rule}: {text}")
        # A fail is never softened by a later report on the same rule, so
        # the worst verdict stands.
        if record["checks"].get(rule) != "fail":
            record["checks"][rule] = verdict


def inspect(descriptor, dictionary, files, modemap=None):
    """Check the description spec over a compiled tree.

    ``files`` maps a command name to (relative path, frontmatter, body) --
    the lint's own walk, handed over so the tree is parsed once.
    """
    found = Findings()
    modemap = load_modemap() if modemap is None else modemap
    registry = build_registry(descriptor, dictionary)
    if registry is None:
        # Not a report. A rule that declined to run and said so quietly is
        # the vacuous pass this module refuses everywhere else.
        found.problems.append("fccli would not import, so the description "
                              "rules (A2, A3, A5, A6) did not run (A2)")
        return found
    if modemap is None:
        found.reports.append("fccli/modemap.json is missing, so the "
                             "mode-shaped rules did not run (A5)")
        modemap = {}

    commands = dictionary.get("commands") or {}
    tuned = dictionary.get("types") or {}
    fams = _families_of(descriptor, dictionary)

    # Which verbs reach a command: its own, and the family door with the
    # choice that runs it. Both are real ways to type it, so an example
    # may use either.
    direct = collections.defaultdict(list)
    for name in registry.names():
        verb = registry.get(name)
        if getattr(verb, "gui_command", None):
            direct[verb.gui_command].append(verb)
    through = collections.defaultdict(list)
    for fname, members in fams.items():
        door = registry.get(fname)
        if door is None or getattr(door, "family", None) != fname:
            continue                     # the family lost its name to a verb
        for choice, member in members.items():
            through[member["command"]].append((door, choice))

    authored = authored_commands()

    for name, entry in sorted(commands.items()):
        rel, front, body = files.get(name, (entry.get("file"), {}, ""))
        mode = (modemap.get(name) or {}).get("mode")
        verbs = direct.get(name, [])
        best = _principal(verbs)
        record = {
            "file": rel,
            "verb": best.name if best else None,
            "aliases": list(best.aliases) if best else [],
            "mode": mode,
            "confidence": (modemap.get(name) or {}).get("confidence"),
            "example": entry.get("example"),
            "synopsis": synopsis(best) if best else None,
            "arguments": _arguments(best),
            "options": _options(best),
            "family": [[door.name, choice] for door, choice in
                       through.get(name, [])],
            # A1 and A4 read these. summary is what `man` puts on the NAME
            # line; body is the DESCRIPTION, and seeded says whether it is
            # still the wiki's words or someone has written it.
            "summary": entry.get("summary") or (best.doc if best else None),
            "authored_summary": entry.get("summary"),
            "body": (body or "").strip(),
            "body_authored": cf.edited(front, body) if front else None,
            "wiki": (front.get("generated") or {}).get("wiki") if front else None,
            # A verdict per rule, so the campaign can read the file
            # rather than the lines. A rule downgrades its own entry when
            # it fires; A1 and A4 stay unread until an agent grades them.
            "checks": _verdicts(entry, best, mode, through.get(name, [])),
            "notes": [],
        }
        found.records[name] = record
        found.by_file[rel] = record
        _a1_a4(found, rel, record)
        blind = name in authored
        if blind:
            # The verb a person wrote owns this command, and its steps are
            # behind an import that needs FreeCAD. Say so in the record
            # rather than answer from the generated verb standing in.
            record["authored_verb"] = True
            record["notes"].append(
                "A2/A3: a hand-written verb in fccli/verbs.py or "
                "fccli/shell.py owns this command; its steps need FreeCAD "
                "to read, so the synopsis and summary here are the "
                "generated verb's, not the ones a reader meets, and the "
                "two shape rules did not run. A1 and A4 want the live "
                "verb -- Part_Box reads 'Create a box from a corner and "
                "three dimensions.' there and 'from three dimensions' "
                "here")
            record["checks"]["A2"] = "unread"
            record["checks"]["A3"] = "unread"
        else:
            _a2(found, rel, entry, direct.get(name, []), through.get(name, []))
            _a3(found, rel, name, entry, tuned, best)
        _a5(found, rel, name, entry, mode, best, direct, through,
            registry, blind)

    # Type tuning, from wherever it was written: a command's own file, or
    # a workbench's _types.yaml for a type no command carries. After the
    # records, so a finding lands in the one it belongs to.
    for tid, spec in sorted(tuned.items()):
        _a2_tuning(found, spec.get("file") or tid, tid, spec, descriptor)

    _a6(found, fams, commands, modemap, tuned)
    return found


def _verdicts(entry, verb, mode, doors):
    """What each rule has to say before any of them has spoken.

    `n/a` is not a pass: a command with no example and no synopsis has
    nothing for A2 to be right about, and counting it as clean would be
    the vacuous pass this project has been bitten by before.
    """
    typed = bool(verb and verb.steps)
    return {
        "A1": "unread",         # until an agent has graded the voice
        "A2": "pass" if (entry.get("example") or entry.get("type")) else "n/a",
        "A3": "pass" if typed else "n/a",
        "A4": "unread",         # until an agent has read it against the wiki
        "A5": "pass" if (entry.get("example") or mode == TYPED_MODE) else "n/a",
        "A6": "pass" if doors else "n/a",
    }


def _principal(verbs):
    """The verb a person would call the command by: the one with a
    synopsis if there is one, and the shortest name otherwise.

    A command can be reached by two verbs -- Part_Box is `box`, built from
    Part::Box with its three lengths, and `part_cube`, the launcher that
    lost the short name to it. The typed one is the command's front door.
    """
    if not verbs:
        return None
    return sorted(verbs, key=lambda v: (not v.steps, len(v.name)))[0]


def _arguments(verb):
    if verb is None:
        return []
    return [{"id": s.id, "kind": s.kind, "unit": s.unit if s.kind == "quantity" else None,
             "gloss": s.prompt, "optional": bool(s.optional)} for s in verb.steps]


def _options(verb):
    if verb is None:
        return []
    return [{"name": o.name, "gloss": o.doc}
            for s in verb.steps for o in s.options]


# ------------------------------------------------------------- A1, A4

# English has two one-letter words. A summary that starts with any other
# single letter is not a sentence somebody wrote.
ONE_LETTER_WORDS = {"a", "i"}


def _a1_a4(found, rel, record):
    """The mechanical slice of A1 and A4.

    Both rules are a person's reading -- whether a summary is imperative
    and result-first, whether a body is faithful to the page it came from.
    Neither is decidable here, and the report is where they are graded.
    What is decidable is the damage: a summary that is not a sentence, a
    body that repeats the summary and says nothing else, and a body `man`
    cannot render. Each of the three is a defect a reader meets before any
    question of voice arises.
    """
    summary = (record.get("summary") or "").strip()
    head = summary.split(" ")[0] if summary else ""
    if len(head) == 1 and head.isalpha() and head.lower() not in ONE_LETTER_WORDS:
        found.report(rel, f"the summary is {summary!r} -- the label was "
                          f"stripped off FreeCAD's tooltip and took the "
                          f"start of the verb with it", "A1")
    body = (record.get("body") or "").strip()
    if not body:
        found.report(rel, "there is no body, so `man` shows the summary and "
                          "nothing else", "A4")
        return
    if _norm(body) == _norm(summary):
        found.report(rel, "the body says only what the summary says, so "
                          "`man` prints one line twice", "A4")
    if body.count("[") != body.count("]"):
        found.report(rel, "the body has a link that never closes; `man` "
                          "prints the bracket and the page reads as broken",
                     "A4")


# ---------------------------------------------------------------- A2

def _a2(found, rel, entry, verbs, doors):
    """A2: what the example passes fits what the synopsis takes.

    Measured against the verb the example actually names, which is not
    always the command's own: `view front` is typed at the family door,
    whose synopsis is one choice, and counting its argument against
    Std_ViewFront's own zero-step launcher would call a correct example
    wrong.

    The tuning half of A2 -- a `type` block naming a property the type
    does not have -- is checked once per type in _a2_tuning.
    """
    example = entry.get("example")
    if not example or "\n" in example or _SHELLISH.search(example):
        return                           # A5 has already refused it
    verb = _spoken(example.split()[0], verbs, doors)
    if verb is None:
        return                           # A5 says what is wrong with it
    fewest, most = arity(verb)
    given = len(example.split()) - 1
    if not verb.steps:
        if given:
            # A launcher has no static steps: a task panel names its own
            # fields when it opens, and those become the prompts. So this
            # is worth a look rather than a fault -- but a positional
            # command with arguments and no synopsis is where the two
            # descriptions of it disagree.
            found.report(rel, f"the example passes {given} argument"
                              f"{'s' if given != 1 else ''} to `{verb.name}`, "
                              f"which has no synopsis of its own -- its "
                              f"steps come from the panel at runtime", "A2")
        return
    if given < fewest or (most is not None and given > most):
        found.report(rel, f"the example passes {given} argument"
                          f"{'s' if given != 1 else ''} to a synopsis that "
                          f"takes {_range(fewest, most)}: {synopsis(verb)}",
                     "A2")


def _spoken(head, verbs, doors):
    """The verb an example's first token names, among the ones that reach
    this command. None when it names none of them."""
    for candidate in verbs:
        if candidate.name == head or head in candidate.aliases:
            return candidate
    for door, _choice in doors:
        if door.name == head or head in door.aliases:
            return door
    return None


def _range(fewest, most):
    if most is None:
        return f"{fewest} or more"
    if fewest == most:
        return f"{fewest}"
    return f"{fewest} to {most}"


def _a2_tuning(found, rel, tid, block, descriptor):
    """A2: a `type` block speaks about properties the type has.

    `patches.apply` looks each name up and moves on when it finds
    nothing, so a typo in `steps` costs an argument the caller is never
    asked for -- a problem -- and a typo in `hide`, `options` or
    `prompts` costs a line that does nothing -- a report.

    Every finding is filed twice: against the file that carries the
    tuning, which is a command's own file for five of the seven and a
    workbench's _types.yaml for the other two, and against the type, so
    the two with no command file are still visible in the record.
    """
    entry = (descriptor.get("types") or {}).get(tid) or {}
    params = {p["name"] for p in entry.get("params") or []}
    if not params:
        # A type the harvest read no properties from: nothing to check.
        return

    def problem(text):
        found.problem(rel, text, "A2")
        found.typed(tid, "A2", "fail", text)

    def report(text):
        found.report(rel, text, "A2")
        found.typed(tid, "A2", "report", text)

    seen = {}

    def once(field, value):
        if value in seen:
            problem(f"type.{field} names {value!r}, which type.{seen[value]} "
                    f"already spoke for -- the second mention does nothing")
        seen[value] = field

    for step in block.get("steps") or []:
        once("steps", step)
        if step not in params:
            problem(f"type.steps names {step!r}, which is not a property of "
                    f"{tid} -- the argument is dropped, not asked for")
    for target, sources in (block.get("point") or {}).items():
        for src in sources or []:
            once("point", src)
            if src not in params:
                problem(f"type.point[{target}] collapses {src!r}, which is "
                        f"not a property of {tid} -- the point is built from "
                        f"a property that is not there")
    for field in ("hide", "options"):
        for value in block.get(field) or []:
            once(field, value)
            if value not in params:
                report(f"type.{field} names {value!r}, which is not a "
                       f"property of {tid} -- the line does nothing")
    for value in (block.get("prompts") or {}):
        if value not in params and value not in (block.get("point") or {}):
            report(f"type.prompts names {value!r}, which is not a property "
                   f"of {tid} and no collapsed point -- the prompt is never "
                   f"shown")


# ---------------------------------------------------------------- A3

def _a3(found, rel, name, entry, tuned, verb):
    """A3: the glosses tell the arguments apart.

    Two arguments with the same gloss are two prompts a reader cannot
    choose between -- FreeCAD ships several: Part::Cone documents both
    Radius1 and Radius2 as "The radius of the cone". The cure is a
    `prompts:` override in the command's type block, so where a person has
    tuned the type this is a fault, and where nobody has yet it is the
    report that says which type to tune next.
    """
    if verb is None or not verb.steps:
        return
    authored = isinstance(entry.get("type"), dict) or _tuned_elsewhere(
        tuned, verb)
    by_gloss = collections.defaultdict(list)
    for step in verb.steps:
        by_gloss[_norm(step.prompt)].append(step.id)
        if _norm(step.prompt) == _norm(step.id):
            found.report(rel, f"argument {step.id} is glossed only with its "
                              f"own name", "A3")
    for step in verb.steps:
        for opt in step.options:
            by_gloss[_norm(opt.doc)].append(f"option {opt.name}")
    for gloss, ids in sorted(by_gloss.items()):
        if len(ids) < 2 or not gloss:
            continue
        positional = [i for i in ids if not i.startswith("option ")]
        text = (f"{' and '.join(ids)} share one gloss, {_short(gloss)!r} -- a "
                f"prompts: entry tells them apart")
        if authored and len(positional) > 1:
            found.problem(rel, text, "A3")
        else:
            found.report(rel, text, "A3")


def _short(text, width=60):
    """A gloss, cut where a reader would stop. FreeCAD ships one that runs
    to three hundred characters, and the message is about which two
    arguments share it, not about what it says."""
    text = " ".join((text or "").split())
    return text if len(text) <= width else text[:width - 1] + "\u2026"


def _tuned_elsewhere(tuned, verb):
    """A type tuned by a workbench's _types.yaml rather than by a command
    file: authored either way, so held to the same standard."""
    tid = getattr(verb, "creates", None)
    return bool(tid and tid in tuned)


# ---------------------------------------------------------------- A5

# What makes a line a shell line rather than one typed at the command
# line. Not the backslash: `image_plane C:\images\plan.png 100 75` is a
# path, and refusing it would be a hard failure over somebody's operating
# system.
_SHELLISH = re.compile(r"[|&;<>$`]")


def _a5(found, rel, name, entry, mode, verb, direct, through, registry,
        blind=False):
    """A5: an example, present and shaped for the mode.

    The example is not decoration: verify.py types it at a live FreeCAD
    and stamps the result in the ledger (ADR-501). So an example that
    names a verb this command cannot be reached by is a fault -- it
    verifies something else, or nothing.

    Except where a hand-written verb owns the command (``blind``): the
    door it opens may be named something the generated tier never
    produced, and a name this module cannot see is not a fault it gets to
    declare. It reports there instead.
    """
    example = entry.get("example")
    if not example:
        if mode == TYPED_MODE:
            found.report(rel, "a positional command with no example", "A5")
        return
    if "\n" in example or not example.strip():
        found.problem(rel, "the example is empty or spans more than one "
                           "line; it is one line a person could type", "A5")
        return
    head = example.split()[0]
    if _SHELLISH.search(example) or head in ("fccli", "bin/fccli", "$"):
        found.problem(rel, f"the example {example!r} is a shell line, not a "
                           f"line typed at the command line", "A5")
        return
    if mode and mode != TYPED_MODE:
        found.report(rel, f"an example on a {mode}-mode command: {example!r} "
                          f"-- either the mode is wrong or the example is "
                          f"driving something the mode says it cannot", "A5")
    reached = _reaches(registry, head, example, direct.get(name, []),
                       through.get(name, []))
    say = found.report if blind else found.problem
    if reached is None:
        say(rel, f"the example starts {head!r}, which is no verb this tree "
                 f"registers" + (" -- though a hand-written verb owns this "
                                 "command, so the name may be one only "
                                 "FreeCAD can see" if blind else ""), "A5")
    elif reached is False:
        doors = ", ".join(sorted(
            [v.name for v in direct.get(name, [])] +
            [f"{d.name} {c}" for d, c in through.get(name, [])])) or "nothing"
        say(rel, f"the example starts {head!r}, which does not reach this "
                 f"command; it is typed as {doors}"
                 + (" -- or as whatever the hand-written verb that owns it "
                    "is called" if blind else ""), "A5")


def _reaches(registry, head, example, verbs, doors):
    """Whether the example's first token runs this command.

    None when the token is no verb at all, False when it is somebody
    else's, True when it is this one -- directly, or through the family
    door with the choice that runs it.
    """
    if registry.get(head) is None:
        return None
    for candidate in verbs:
        if candidate.name == head or head in candidate.aliases:
            return True
    tokens = example.split()
    for door, choice in doors:
        if door.name != head and head not in door.aliases:
            continue
        if len(tokens) > 1 and tokens[1] == choice:
            return True
        step = door.steps[0] if door.steps else None
        if step is not None and step.default == choice and len(tokens) == 1:
            return True
    return False


# ---------------------------------------------------------------- A6

def _a6(found, fams, commands, modemap, tuned):
    """A6: a family is learnable from one of its members.

    Four ways a family breaks that promise, none of them a fault on any
    one file, all of them worth a line: half its members carry an example
    and half do not; one member behaves unlike the rest; two members'
    examples are typed by different doors; two tuned siblings put the same
    two arguments in opposite order, which is the one that costs a reader
    who learned the first.
    """
    for fname, members in sorted(fams.items()):
        names = sorted({m["command"] for m in members.values()})
        where = f"family {fname}"
        record = {"members": names, "example": [], "modes": {}, "notes": []}
        found.families[fname] = record
        with_example = [n for n in names if (commands.get(n) or {}).get("example")]
        record["example"] = with_example
        if with_example and len(with_example) < len(names):
            found.reports.append(
                f"{where}: {len(with_example)} of {len(names)} members "
                f"{'carries' if len(with_example) == 1 else 'carry'} an "
                f"example, so the family answers 'how do I call it' for some "
                f"of its choices and not others (A6)")
            record["notes"].append("mixed example presence")
            found.member([n for n in names if n not in with_example], "A6",
                         f"family {fname}: the other members carry an "
                         f"example and this one does not")
        modes = collections.Counter((modemap.get(n) or {}).get("mode")
                                    for n in names)
        record["modes"] = dict(modes)
        if len(names) >= 4 and len(modes) > 1:
            top, count = modes.most_common(1)[0]
            odd = [n for n in names
                   if (modemap.get(n) or {}).get("mode") != top]
            if count >= 0.75 * len(names) and len(odd) <= 2:
                found.reports.append(
                    f"{where}: {count} of {len(names)} members are {top}, but "
                    f"{', '.join(odd)} "
                    f"{'is' if len(odd) == 1 else 'are'} not -- learning one "
                    f"member predicts the wrong thing for these (A6)")
                record["notes"].append(f"mode outlier: {', '.join(odd)}")
                found.member(odd, "A6", f"family {fname}: the other members "
                                        f"are {top} and this one is not")
        shapes = collections.defaultdict(list)
        for name in with_example:
            head = commands[name]["example"].split()[0]
            shapes["the family door" if head == fname else "its own verb"].append(name)
        if len(shapes) > 1:
            spelled = "; ".join(f"{k}: {', '.join(v)}" for k, v in sorted(shapes.items()))
            found.reports.append(
                f"{where}: the examples are typed two ways -- {spelled} (A6)")
            record["notes"].append("mixed example shape")
            found.member(with_example, "A6",
                         f"family {fname}: its members' examples are typed "
                         f"two ways -- {spelled}")
    _a6_order(found, tuned)


def _a6_order(found, tuned):
    """Two tuned types that share argument names, ordered differently.

    `cylinder <Radius> <Height>` and `helix <Pitch> <Height> <Radius>`
    disagree about which of radius and height comes first, and a reader
    who learned one guesses wrong at the other.
    """
    items = sorted((tid, spec.get("steps") or [])
                   for tid, spec in tuned.items())
    for i, (a, sa) in enumerate(items):
        for b, sb in items[i + 1:]:
            shared = [s for s in sa if s in sb]
            if len(shared) < 2:
                continue
            if [s for s in sa if s in shared] != [s for s in sb if s in shared]:
                found.reports.append(
                    f"family {a.split('::')[0]}: {a} orders "
                    f"{' '.join(sa)} and {b} orders {' '.join(sb)} -- they "
                    f"share {' and '.join(shared)} and disagree about which "
                    f"comes first (A6)")


# ---------------------------------------------------------------- report

def write_report(found, path, descriptor):
    """The per-command record, for the campaign to read.

    A1 (voice) and A4 (faithfulness) are not decidable here; what they
    need is every command's summary, body, and where the body came from,
    beside the mechanical verdicts. That is this file.

    Three sections. `commands` is the record per command; `families` is
    what a family looks like across its members; `types` carries the
    tuning findings for the two types tuned in a _types.yaml, which have
    no command record to land in.
    """
    data = {
        "generated_by": "tools/descriptions.py",
        "date": datetime.date.today().isoformat(),
        "freecad": descriptor.get("freecad"),
        "spec": "GH #47 group A; A2/A3/A5/A6 checked, A1/A4 left to read. "
                "A command with authored_verb is one a hand-written verb "
                "owns: its synopsis here is the generated verb standing in, "
                "and A2/A3 are unread rather than judged.",
        "totals": totals(found),
        "families": found.families,
        "types": found.types,
        "commands": found.records,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return data


def totals(found):
    counted = collections.Counter()
    for record in found.records.values():
        for rule, verdict in record["checks"].items():
            counted[f"{rule} {verdict}"] += 1
    counted["commands"] = len(found.records)
    counted["examples"] = sum(1 for r in found.records.values() if r["example"])
    counted["problems"] = len(found.problems)
    counted["reports"] = len(found.reports)
    return dict(sorted(counted.items()))
