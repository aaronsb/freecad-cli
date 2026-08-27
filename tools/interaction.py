#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The grammar and UX spec, checked over the command tree (GH #49, of #47).

The spec's D group asks what happens as a person types, rather than what
they read first:

  D1  every choice is resolvable -- no value another spelling takes
  D2  options render distinctly from the step's own prompt (GH #56)
  D3  completion offers the right pool at each position
  D4  a verb is reachable by its meaningful word, and hijacks nothing
  D5  units echo correctly

D1, D3, D4 and the static half of D5 live here. D2 is a rendering question
-- what the prompt line looks like with an option on it -- and belongs with
the widget, not with the tree.

The architecture is descriptions.py's, deliberately. Nothing here models
what a verb looks like: `fccli.factory` imports without FreeCAD, so the
registry is *built* and the rules read it, and `fccli.completion` and
`fccli.families` are called rather than re-derived. Two models of verb
shape would be two things to keep true, and the second one always rots.

The same is true one level down. D1's collision rule needs to know which
command lost a choice to another, and `families()` overwrites the loser
without a word. Rather than restate its placement policy here -- the
CamelCase split, the excluded heads, the minimum size -- it is called twice,
once over the commands in order and once reversed, so the first writer wins
one run and the last writer wins the other. A choice whose member differs
between the two collided, and both sides are named. The rule that decides
where a command lands stays in one file.

Two severities, on descriptions.py's line: a fault that silently changes
what a command does is a problem and fails the lint; a fault that wants a
person's judgment, or that the tree carries by the dozen today, is a report
line. `--strict-grammar` promotes every report to a problem.

Where the two tiers fall is a judgment call per rule, and each is argued at
the rule. The criterion is the consequence: what earns the problem tier is
a fault the person never hears about. Most of the D group's live faults are
loud -- the engine prints `expected one of [...]` and refuses -- and those
are reports. Four classes are above the line, and three of them are empty
today, which is why this lint can be added to `make check` without breaking
it. The fourth is the choice collision: `save as` runs one of Std_SaveAs
and IFC_SaveAs and nothing says which, which is silent, so the rule is a
problem and the four instances the tree carries are grandfathered by name
in KNOWN_COLLISIONS. The 1003 verbs unreachable by their meaningful word
and the 264 dimensionless steps carrying millimetres are reports, and the
report is the campaign's worklist. The shadowed choices were 21 of those
reports and are now none: the matcher takes an exact value before a prefix
(GH #55), so a value another value begins is reachable, and what D1 has
left to find is two spellings of one word in a single door.

The blind spots are named rather than guessed at. `fccli.verbs` and
`fccli.shell` register hand-written verbs into the global REGISTRY at
import, and both import FreeCAD at their first line, so that tier does not
exist in a FreeCAD-free build. Fourteen commands are claimed by name
(descriptions.py's `authored_commands`), and every rule whose answer
depends on step shape records `unread` for them. Sixty-seven verb names and
aliases are claimed the same way -- an alias counts, because `register_all`
refuses a generated verb on a taken alias exactly as it does on a taken
name -- and a generated verb or family door standing on one of them is a
verb this lint can see and an operator cannot. Eighteen do, including the
family doors `select` and `sel`, whose choices are fiction. Said in the
record, not silently judged.
"""

import ast
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import descriptions as dsc  # noqa: E402

COMPLETION = os.path.join(ROOT, "fccli", "completion.py")

# The names a hand-written verb answers to, in the two files that register
# them. Read as text for the same reason descriptions.py reads
# `gui_command=` there: importing needs FreeCAD, and writing the names down
# here would be the second model this module exists to avoid.
#
# Both halves, because `register_all` refuses a generated verb on a taken
# alias exactly as it does on a taken name. Reading only `name=` left
# `exit`, `help` and `sel` -- aliases of the hand-written `quit`, `man` and
# `select` -- out of the blind tier, and the lint shipped a D4 line about
# `help` as though it were a word a person could reach Std_OnlineHelp by.
#
# In source order, so an alias is attributed to the name most recently seen
# before it -- which is how every one of these is written, and is what lets
# the record say `exit` is `quit` rather than leaving a reader to find out.
CLAIMS = re.compile(r"""\bname\s*=\s*["'](?P<name>[a-z_][a-z_0-9]*)["']"""
                    r"""|\baliases\s*=\s*\[(?P<aliases>[^\]]*)\]""")
ALIAS_ITEM = re.compile(r"""["']([a-z_][a-z_0-9]*)["']""")
# What a hand-written step says its candidates come from.
DECLARED_SOURCE = re.compile(r"""\bcompletes\s*=\s*["']([a-z_]+)["']""")

# The units the harvest can put on a step: KIND_BY_PROPERTY's whole
# vocabulary. `parse_quantity` reads anything that is not "deg" as a
# length, and `units._internal_unit` asks FreeCAD what a unit is, so a
# unit outside this set is one nothing in the chain was written for.
# The units the harvest can write, plus the empty one. A step that echoes
# in nothing is a property FreeCAD gives no dimension, carried through as
# the absence it is rather than defaulted to millimetres -- `parse_quantity`
# appends nothing to a bare number, which is the correct reading and the
# cure for the class below, not a member of it (GH #78, ADR-203).
HARVEST_UNITS = {"", "mm", "mm^2", "mm^3", "deg"}

# Properties FreeCAD gives no dimension. The harvest maps each to
# ("quantity", "") and omits the unit, and `_step_from_param` reads the
# omission as its default of millimetres -- so a turn count, an iteration
# limit and a tolerance all arrive as lengths. Named here rather than
# inferred from the absent unit, because two of the property types the
# harvest leaves unitless *are* dimensioned at runtime.
DIMENSIONLESS = {
    "App::PropertyFloat", "App::PropertyFloatConstraint",
    "App::PropertyPrecision", "App::PropertyPercent",
    "App::PropertyInteger", "App::PropertyIntegerConstraint",
}
# Derived choice collisions this tree is known to carry: family.choice ->
# the two commands, and the issue that owns the fix. A collision is a
# problem whichever way the spelling arose -- `save as` runs one of two
# commands and nothing anywhere says which -- so these four are
# grandfathered rather than the class being demoted, which is what makes
# the *next* one fail the lint the day it appears. The idiom is
# verify.py's KNOWN_HAZARDS: a short list, an issue beside each entry,
# and the rule above the line.
#
# An entry the tree no longer collides on is reported so the list gets
# pruned. A grandfather list nobody prunes is how a rule quietly stops
# being one.
KNOWN_COLLISIONS = {
    "save.as": "Std_SaveAs and IFC_SaveAs (GH #33)",
    "move.view": "TechDraw_MoveView and BIM_MoveView (GH #33)",
    "poly.cut": "Points_PolyCut and Mesh_PolyCut (GH #33)",
    "section.by_plane":
        "Mesh_SectionByPlane and MeshPart_SectionByPlane (GH #33)",
}

# A Quantity property carries its unit on the instance, not on the type,
# so the harvest cannot know it and neither can this module. The runtime
# tier reads it off the object.
RUNTIME_UNIT = {"App::PropertyQuantity", "App::PropertyQuantityConstraint"}


def known_sources(path=COMPLETION):
    """The completion pools `from_source` knows, read out of the function.

    A step's `completes` names one of these; anything else falls through
    to `return []` and Tab offers nothing where the step said it had a
    pool. The names are taken from the function's own comparisons rather
    than listed here, so a pool added or renamed there is not a fact this
    module has to be told separately.

    Empty is not a safe answer -- it would call every declared source
    unknown -- so a function that reads as comparing against nothing is
    raised rather than shrugged off.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    found = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "from_source"):
            continue
        for cmp_ in ast.walk(node):
            if not (isinstance(cmp_, ast.Compare)
                    and isinstance(cmp_.left, ast.Name)
                    and cmp_.left.id == "source"):
                continue
            for other in cmp_.comparators:
                if isinstance(other, ast.Constant) and isinstance(other.value, str):
                    found.add(other.value)
    if not found:
        raise ValueError(f"{path}: from_source compares `source` against no "
                         f"string, so the pool names moved and D3 would call "
                         f"every declared source unknown")
    return found


def authored_verbs(sources=dsc.AUTHORED_SOURCES):
    """Every name a hand-written verb answers to: name -> source file.

    A generated verb or a family door standing on one of these is one this
    lint sees and an operator does not: live, `register_all` refuses the
    generated name and the hand-written verb keeps it. An alias counts --
    live, `help` is `man` and `sel` is `select`, and a generated verb of
    either name never registers.

    Empty is not a safe answer, for the same reason it is not in
    `authored_commands`: it would quietly declare the blind spot absent.
    Each half is required, so losing one of the two patterns is not a
    quieter lint but a failing one.
    """
    found = {}
    for path in sources:
        where = os.path.relpath(path, ROOT).replace(os.sep, "/")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        owner, names, aliases = None, 0, 0
        for match in CLAIMS.finditer(text):
            if match.group("name"):
                owner = match.group("name")
                names += 1
                found.setdefault(owner, (owner, where))
                continue
            for alias in ALIAS_ITEM.findall(match.group("aliases")):
                aliases += 1
                found.setdefault(alias, (owner, where))
        if not names or not aliases:
            raise ValueError(
                f"{os.path.relpath(path, ROOT)}: read {names} name= and "
                f"{aliases} aliases= -- the hand-authored tier moved, and "
                f"the names this lint reports on would be names nobody "
                f"meets")
    return found


def declared_sources(sources=dsc.AUTHORED_SOURCES):
    """Every `completes=` a hand-written step declares: source -> where.

    The generated tier declares none -- a harvested property has no pool
    but its own enumerations -- so this is the only tier D3's source rule
    has anything to read. Empty is a legitimate answer here: a release
    that removed the last one is a tree with no sources to check, not a
    reader that lost them, and the count is reported either way.
    """
    found = collections.defaultdict(list)
    for path in sources:
        where = os.path.relpath(path, ROOT).replace(os.sep, "/")
        with open(path, encoding="utf-8") as fh:
            for source in DECLARED_SOURCE.findall(fh.read()):
                found[source].append(where)
    return found


class Findings(dsc.Findings):
    """descriptions.Findings, plus the sections the D group writes.

    `records` is keyed and shaped as descriptions.py keys and shapes it,
    so `write_report` merges the two into one record per command rather
    than leaving the campaign two files to join by hand.
    """

    def __init__(self):
        super().__init__()
        self.choices = {}     # a choice step, and what is unreachable in it
        self.words = {}       # a meaningful word, and who answers to it
        self.quantities = {}  # a quantity step, and the unit it echoes in
        self.blind = []       # what this lint cannot see, said out loud

    def _note(self, where, rule, verdict, text):
        """A report against a file never downgrades `unread` to a verdict.

        `unread` is a rule saying it is not looking at this command, and a
        later line about the generated verb standing in does not change
        that: the reports filed against Part_Box's file are about the
        thousand-verb tier, and `box` is `corner length width height` to
        the person reading the record. Without this, a rule that declined
        to answer would be recorded as having answered.
        """
        record = self.by_file.get(where)
        if record is not None and record["checks"].get(rule) == "unread":
            record["notes"].append(f"{rule}: {text}")
            return
        super()._note(where, rule, verdict, text)


def inspect(descriptor, dictionary, files=None, registry=None):
    """Check the grammar spec over a compiled tree.

    ``files`` maps a command name to (relative path, frontmatter, body),
    the lint's own walk. Only the path is read here; the signature matches
    descriptions.inspect so the two are called the same way.

    ``registry`` is for a test that wants to put a fault in one. Built
    from the descriptor and the dictionary when it is not given.
    """
    found = Findings()
    files = files or {}
    if registry is None:
        registry = dsc.build_registry(descriptor, dictionary)
    if registry is None:
        # Not a report. A rule that declined to run and said so quietly is
        # the vacuous pass this module refuses everywhere else.
        found.problems.append("fccli would not import, so the grammar rules "
                              "(D1, D3, D4, D5) did not run (D1)")
        return found

    commands = dictionary.get("commands") or {}
    claimed = dsc.authored_commands()
    written = authored_verbs()

    # Which verb runs which command, and which family door reaches it.
    # Both are ways a person types it, and D4 needs both before it can say
    # a command is unreachable by its meaningful word.
    direct = collections.defaultdict(list)
    for name in registry.names():
        verb = registry.get(name)
        if getattr(verb, "gui_command", None):
            direct[verb.gui_command].append(verb)
    fams = dsc._families_of(descriptor, dictionary)
    through = collections.defaultdict(list)
    for fname, members in fams.items():
        door = registry.get(fname)
        if door is None or getattr(door, "family", None) != fname:
            continue                     # the family lost its name to a verb
        for choice, member in members.items():
            through[member["command"]].append((door, choice))

    for name, entry in sorted(commands.items()):
        rel = files.get(name, (entry.get("file"),))[0] or entry.get("file")
        verb = dsc._principal(direct.get(name, []))
        record = {
            "file": rel,
            "verb": verb.name if verb else None,
            "family": [[door.name, choice] for door, choice in
                       through.get(name, [])],
            "checks": {"D1": "n/a", "D3": "n/a", "D4": "n/a", "D5": "n/a"},
            "notes": [],
        }
        found.records[name] = record
        found.by_file[rel] = record
    _blind_tier(found, claimed, written, registry, fams)
    # The step kinds, imported now rather than at module scope: the whole
    # of fccli is behind an import that may fail, and a lint that cannot be
    # imported is one nothing runs. Past the registry check, it cannot.
    from fccli.grammar import CHOICE, QUANTITY
    _d1(found, registry, fams, descriptor, dictionary, commands, CHOICE)
    _d3(found, registry, CHOICE)
    _d4(found, registry, through, descriptor, commands, claimed, written)
    _d5(found, registry, descriptor, QUANTITY)
    return found


def _declined(found, command):
    """Whether the rules have already said they are not looking at this one.

    A hand-written verb owns the command, so a finding about the generated
    verb standing in is a finding about a verb nobody meets. Read off the
    record rather than off a verdict, because a verdict is what the
    finding would be about to change.
    """
    record = found.records.get(command)
    return record is not None and record.get("authored_verb") is not None


# ------------------------------------------------------- the blind tier

def _blind_tier(found, claimed, written, registry, fams):
    """Say what this lint is not looking at, before any rule speaks.

    Two shapes. A command a hand-written verb owns has a step list behind
    an import that needs FreeCAD, so all four rules record `unread` for
    it: the choices, the pools, the name and the units here are the
    generated verb's. And a generated verb or family door standing on a
    name a person also wrote is a verb this lint sees and an operator does
    not: live, `register_all` refuses the generated name.
    """
    for command, (verb, where) in sorted(claimed.items()):
        record = found.records.get(command)
        if record is None:
            continue
        record["authored_verb"] = verb
        for rule in ("D1", "D3", "D4", "D5"):
            record["checks"][rule] = "unread"
        record["notes"].append(
            f"D1/D3/D4/D5: the hand-written verb `{verb}` in {where} owns "
            f"this command, and reading its steps needs FreeCAD. The name, "
            f"the choices, the pools and the units here are the generated "
            f"verb's, not the ones a person meets, so all four rules "
            f"declined. `n/a` would have been the claim that it has no "
            f"choice step and no quantity, which is a thing this module "
            f"cannot see either way")
    taken = sorted(set(written) & set(registry.names()))
    for name in taken:
        verb = registry.get(name)
        door = getattr(verb, "family", None)
        owner, source = written[name]
        found.blind.append({"verb": name, "written_in": source,
                            "authored_verb": owner, "family_door": door})
        found.report(source,
                     f"the name `{name}` is "
                     + (f"the hand-written verb `{owner}`"
                        if owner == name else
                        f"an alias of the hand-written verb `{owner}`")
                     + ", and the generated tier builds a verb of the "
                       "same name"
                     + (f" -- the family door `{door}` and its "
                        f"{len(fams.get(door) or {})} choices do not exist "
                        f"live, so what D1 says about them is about a door "
                        f"nobody opens" if door else
                        "; live, register_all refuses the generated one, so "
                        "what D4 says about this name is about a verb "
                        "nobody meets"), "D4")


# ---------------------------------------------------------------- D1

def _d1(found, registry, fams, descriptor, dictionary, commands, CHOICE):
    """D1: every listed choice is a value some input selects.

    Two ways a choice set breaks that, and they are not the same fault.

    *Shadowing.* The engine takes a choice by prefix and insists on one
    hit, so an exact value that begins a longer one can never be selected:
    `view iso` is `iso` and `isometric` both, and the engine refuses with
    `expected one of [...]`. GH #55 is that instance, found live. It runs
    over both kinds of choice set -- a family door's members and a
    harvested enumeration's values -- because the matcher is the same one:
    `TextStyle` can be set to Bold-Italic and never to Bold.

    *Collision.* Two commands slug to one spelling, and `families()`
    writes the second over the first without a word. `save as` runs one of
    Std_SaveAs and IFC_SaveAs, and the other is gone from the family with
    nothing said anywhere.

    The severity split follows the consequence, not the provenance.
    Shadowing is loud -- the person reads a refusal and can try the longer
    word -- and the tree carries twenty-one, so it is a report naming the
    value and what swallowed it. A collision is silent in the full sense:
    no refusal, no message, the wrong command simply runs, and one of the
    two files ships describing something nobody can reach. That is a
    problem however the spelling arose. The harm is identical either way,
    so provenance would be a line about whom to blame drawn where the
    criterion asks what happens.

    The four the tree carries are grandfathered by name in
    KNOWN_COLLISIONS rather than the class being demoted, so a new one --
    the next addon, the next FreeCAD release -- fails the lint the day it
    appears instead of joining a report nobody diffs. D1 exists because
    #55 sat unnoticed; a report is where it sat. An authored spelling gets
    no grandfathering at all.
    """
    seen_doors = set()
    for fname, members in sorted(fams.items()):
        door = registry.get(fname)
        if door is None or getattr(door, "family", None) != fname:
            continue
        seen_doors.add(id(door))
        for step in door.steps:
            if step.kind == CHOICE and step.choices:
                _shadowing(found, step, f"the family door `{fname}`", fname,
                           lambda c: _where(commands,
                                            (members.get(c) or {}).get("command"),
                                            None, fname),
                           lambda c: (members.get(c) or {}).get("command"))
    for name in registry.names():
        verb = registry.get(name)
        if id(verb) in seen_doors:
            continue
        for step in verb.steps:
            if step.kind != CHOICE or not step.choices:
                continue
            command = getattr(verb, "gui_command", None)
            rel = _where(commands, command, getattr(verb, "creates", None), name)
            _shadowing(found, step, f"`{name} <{step.id}>`", name,
                       lambda c, r=rel: r, lambda c, x=command: x)
    _collisions(found, fams, descriptor, dictionary, commands)


def _where(commands, command, creates, fallback):
    """Where a finding is filed.

    A command's own file when there is one. A type built by no command has
    none -- its tuning would go in a workbench's _types.yaml -- so the type
    stands in, which is the same place descriptions.py files a finding it
    cannot give a file to.
    """
    rel = (commands.get(command) or {}).get("file") if command else None
    return rel or creates or fallback


def _shadowing(found, step, subject, key, where, owner):
    """Values in one choice set that no input selects.

    `grammar.match_choice` is the engine's own matcher, called rather than
    restated: this rule is about what the accept path does with a typed
    value, and a copy of a two-line comparison is the easiest kind to let
    drift. It used to be a copy, and a reviewer's mutant proved the copy
    could be made case-sensitive without the suite or the tree's output
    moving a line.

    Calling it is also what re-aimed the rule when the matcher moved. The
    fault it was written for was a value another value begins -- `iso`
    beside `isometric` (GH #55) -- and the matcher now settles that one
    itself by taking an exact value first. What is left is two choices
    that differ only in case: those are exact together, so each selects
    two and neither is reachable. A family door merges the `also:`
    spellings of every command under it, so that is where two spellings of
    one word meet. Because the rule asks the matcher rather than the old
    question, it followed the fix without being rewritten, and reverting
    the matcher brings the shadow class back into this report.
    """
    from fccli.grammar import match_choice
    for value in step.choices:
        hits = match_choice(step.choices, value)
        if len(hits) == 1:
            continue
        others = [h for h in hits if h != value]
        entry = found.choices.setdefault(key, {"step": step.id,
                                               "choices": len(step.choices),
                                               "unreachable": []})
        entry["unreachable"].append({"value": value, "swallowed_by": others,
                                     "command": owner(value)})
        found.report(where(value),
                     f"{subject} lists {value!r}, and typing it also selects "
                     f"{_and(repr(x) for x in others)} -- the step insists "
                     f"on one hit, so {value!r} is a value no input selects",
                     "D1")


def _and(items):
    """A list, as a person would read it out."""
    items = list(items)
    if len(items) < 3:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _collisions(found, fams, descriptor, dictionary, commands):
    """Two commands under one spelling: the second wins, silently.

    `families()` is called a second time over the commands reversed rather
    than its placement policy being restated here. The first writer wins
    one run and the last writer wins the other, so a choice whose member
    differs between the two is one two commands wanted, and both are named.
    """
    from fccli.families import families, overrides_of, slug
    over, exclude = overrides_of(dictionary)
    backwards = families(dict(reversed(list(descriptor["commands"].items()))),
                         overrides=over, exclude=exclude)
    authored = set()
    for name, entry in (dictionary.get("commands") or {}).items():
        fam, choice = entry.get("family"), entry.get("choice")
        if not (isinstance(fam, str) and choice):
            continue
        for spelling in [choice] + list(entry.get("also") or []):
            authored.add((slug([fam]), slug([spelling])))
    seen = set()
    for fname, members in sorted(fams.items()):
        for choice, member in sorted(members.items()):
            other = ((backwards.get(fname) or {}).get(choice) or {}).get("command")
            if not other or other == member["command"]:
                continue
            key = f"{fname}.{choice}"
            seen.add(key)
            wrote = (fname, choice) in authored
            known = KNOWN_COLLISIONS.get(key)
            rel = _where(commands, member["command"], None, fname)
            text = (f"`{fname} {choice}` is two commands, {member['command']} "
                    f"and {other} -- one is written over the other where the "
                    f"family is built, so the choice runs a command the "
                    f"other's file still describes")
            if wrote:
                # No grandfathering for a spelling the tree wrote: a file
                # asked for the word and a different command answers to it.
                found.problem(rel, text + "; the tree authored this spelling",
                              "D1")
            elif known:
                found.report(rel, text + f"; known and grandfathered as "
                                         f"{known}, so a family:/choice: "
                                         f"override in one of the two files "
                                         f"is what closes it", "D1")
            else:
                found.problem(rel, text + "; a family:/choice: override in "
                                          "one of the two files is the cure",
                              "D1")
    for key, why in sorted(KNOWN_COLLISIONS.items()):
        if key not in seen:
            found.reports.append(
                f"choices: `{key.replace('.', ' ')}` is grandfathered as {why} "
                f"and no longer collides -- prune it from KNOWN_COLLISIONS, "
                f"or the day those two names come back the rule will let "
                f"them (D1)")
            entry = found.choices.setdefault(fname, {
                "step": "target", "choices": len(members), "unreachable": []})
            entry.setdefault("collisions", []).append(
                {"choice": choice, "commands": [member["command"], other],
                 "authored": wrote})


# ---------------------------------------------------------------- D3

def _d3(found, registry, CHOICE):
    """D3: at each position, the step has a pool to offer.

    Static approximation, and the word is doing work. What completion
    offers depends on the document, the open panel and the working
    directory, none of which exist here. What is decidable is whether
    each step *resolves to a pool at all* -- three ways it does not:

    A source that is not one. `completes` names a pool and
    `completion.from_source` answers `[]` to anything it does not know, so
    a typo costs the whole pool and says nothing. A problem: the step
    declared a pool and there is none. The generated tier declares no
    sources at all -- a harvested property has no pool but its own
    enumerations -- so the thirteen in `fccli/shell.py` are read out of the
    source text, the same way descriptions.py reads that tier's names.

    A choice step with nothing in it. FreeCAD ships enumeration properties
    the harvest read no values from; the step then insists on one of a set
    it cannot show, and `expected one of []` is what a person gets. Loud,
    and five live, so a report.

    A position that is not the one being typed. `completion.step_for`
    finds the step by counting tokens, and an inline option is a token
    that consumes no step -- so after one is typed, the pool offered is
    the next step's. 125 verbs carry options. One report line rather than
    125: the fault is in how position is counted, not in any of them.
    """
    known = known_sources()
    for source, wheres in sorted(declared_sources().items()):
        if source in known:
            continue
        found.problem(sorted(set(wheres))[0],
                      f"a step completes from {source!r}, which "
                      f"from_source does not know -- it answers [] and Tab "
                      f"offers nothing where the step said it had a pool",
                      "D3")
    empty, with_options = [], []
    for name in registry.names():
        verb = registry.get(name)
        command = getattr(verb, "gui_command", None)
        record = found.records.get(command)
        where = ((record or {}).get("file")
                 or getattr(verb, "creates", None) or name)
        for step in verb.steps:
            if step.completes and step.completes not in known:
                found.problem(where, f"`{name} <{step.id}>` completes from "
                                     f"{step.completes!r}, which from_source "
                                     f"does not know -- it answers [] and the "
                                     f"step offers nothing", "D3")
            if (step.kind == CHOICE and not step.choices
                    and not step.options and not step.completes):
                empty.append((name, step.id, command, where))
            if step.options:
                with_options.append((name, command))
    for name, sid, command, where in empty:
        if _declined(found, command):
            continue                     # a hand-written verb owns this one
        found.report(where, f"`{name} <{sid}>` takes one of a closed set and "
                            f"has none to take -- the harvest read no values "
                            f"off the enumeration, so the step can be skipped "
                            f"and never answered", "D3")
    for name, command in with_options:
        record = found.records.get(command)
        if record is None or _declined(found, command):
            continue
        record["checks"]["D3"] = "report"
        record["notes"].append(
            f"D3: `{name}` takes an inline option, and completion.step_for "
            f"finds the step by counting tokens -- once an option is typed "
            f"the pool offered is the next step's")
    if with_options:
        sample = ", ".join(sorted({n for n, _ in with_options})[:3])
        found.reports.append(
            f"completion: {len(with_options)} verbs take an inline option "
            f"({sample}, ...), and completion.step_for finds the step by "
            f"counting tokens on the line. An option consumes no step, so "
            f"from the token after one the pool offered belongs to the next "
            f"step (D3)")


# ---------------------------------------------------------------- D4

def _d4(found, registry, through, descriptor, commands, claimed, written):
    """D4: a verb answers to the word it is about.

    A tier-0 verb is named from FreeCAD's menu label, so `Mesh_PolyCut` is
    `poly_cut` and the word that means it is `cut`. Three questions, three
    severities.

    *Did the tree get the name it asked for?* A command file's `verb:` or
    `aliases:` is a promise, and the registry is where it is kept or not.
    Rule 4 of the tree lint checks these against each other; nothing
    checks them against the verbs that get built, so an alias eaten by a
    family door or a hand-written verb resolves to somebody else's command
    and the file still documents it. Silent, and empty today: a problem.

    *Is the verb reachable by its meaningful word?* 1003 are not -- you
    must type the qualified name, or find it by substring (ADR-301), which
    completes but does not run. Wholesale, so the verdict goes in the
    record and the report gets one line with the count. A verb reachable
    through a family door by that word is reachable: `Std_ViewFront` is
    `view front`, and 118 are saved that way.

    *Does a generic word answer for the wrong workbench?* `cut` is the
    meaningful word of six verbs and resolves to `Mesh_PolyCut`. Which
    workbench a person *expects* is a judgment nothing here can make, so
    what is reported is the mechanical half: the word, who answers to it,
    which workbench that is, and how many others it shadowed. A family
    door winning the word is the design working -- `view` is meant to be
    the door -- and is not reported.

    And #21: `completion.domain_of` reads the domain off the command-name
    prefix, so `use <domain>` scopes by prefix rather than by the
    workbench that shipped the command. 79 commands ship under a
    workbench their prefix does not name. Report, grouped: the fix is
    `domain_of`'s, not any command file's.
    """
    for name, entry in sorted(commands.items()):
        record = found.records.get(name)
        rel = (record or {}).get("file") or name
        for asked in ([entry["verb"]] if entry.get("verb") else []) + \
                list(entry.get("aliases") or []):
            got = registry.get(asked)
            if got is None:
                found.problem(rel, f"the file asks for the name {asked!r} and "
                                   f"no verb answers to it -- the line is "
                                   f"documented and cannot be typed", "D4")
            elif getattr(got, "gui_command", None) != name:
                found.problem(rel, f"the file asks for the name {asked!r} and "
                                   f"it runs `{got.name}`"
                                   + (f" ({got.gui_command})"
                                      if got.gui_command else " instead")
                                   + " -- the name was taken before this "
                                     "command got it", "D4")

    doors = {door.name for doors_ in through.values() for door, _ in doors_}
    claimants = collections.defaultdict(list)
    for name in registry.names():
        claimants[_meaningful(name)].append(name)

    unreachable = 0
    for name in registry.names():
        verb = registry.get(name)
        word = _meaningful(name)
        command = getattr(verb, "gui_command", None)
        record = found.records.get(command)
        if word == name:
            if record is not None and record["checks"]["D4"] == "n/a":
                record["checks"]["D4"] = "pass"
            continue
        if registry.resolve_prefix(word) == [name]:
            if record is not None and record["checks"]["D4"] == "n/a":
                record["checks"]["D4"] = "pass"
            continue
        by_door = [f"{door.name} {choice}"
                   for door, choice in through.get(command, [])
                   if choice == word] if command else []
        if by_door:
            if record is not None and record["checks"]["D4"] == "n/a":
                record["checks"]["D4"] = "pass"
                record["notes"].append(
                    f"D4: `{name}` does not answer to {word!r}, but "
                    f"`{by_door[0]}` does")
            continue
        unreachable += 1
        found.words.setdefault(word, {"claimants": [], "answers_to": None})
        if record is not None and record["checks"]["D4"] == "n/a":
            record["checks"]["D4"] = "report"
            record["notes"].append(
                f"D4: `{name}` is not reachable by {word!r} -- the qualified "
                f"name is the only way to run it, and an aliases: entry is "
                f"the cure")
    if unreachable:
        found.reports.append(
            f"naming: {unreachable} verbs are not reachable by their "
            f"meaningful word -- the qualified name runs them and substring "
            f"completion finds them (ADR-301), but the word alone does not "
            f"resolve. Each carries the verdict in its own record (D4)")

    for word, names in sorted(claimants.items()):
        if len(names) < 2:
            continue
        hits = registry.resolve_prefix(word)
        if len(hits) != 1 or hits[0] not in names:
            continue
        winner = hits[0]
        found.words[word] = {"claimants": sorted(names), "answers_to": winner}
        if winner in doors:
            continue                     # the family door is meant to win
        won = registry.get(winner)
        if winner in written or getattr(won, "gui_command", None) in claimed:
            # The name a person types for this one is the hand-written
            # verb's, not the generated verb's, and this module is not
            # looking at it. Recorded as blind rather than reported: a
            # hijack by a verb nobody meets is not a hijack.
            found.words[word]["blind"] = True
            continue
        shops = {n: _workbench(registry, descriptor, n) for n in names}
        if len(set(shops.values())) < 2:
            continue
        rel = _where(commands, getattr(won, "gui_command", None),
                     getattr(won, "creates", None), winner)
        others = len(names) - 1
        # Appended rather than filed against the winner's record: winning
        # the word is what `cylinder` is supposed to do, and marking
        # Part_Cylinder down for it would put the verdict on the one verb
        # in the group that is behaving. The verbs that need an alias
        # already carry theirs from the reachability loop above.
        found.reports.append(
            f"naming: {word!r} is the meaningful word of {len(names)} verbs "
            f"across {len(set(shops.values()))} workbenches, and answers for "
            f"`{winner}` ({shops[winner] or 'no workbench'}, {rel}). The "
            f"other {others} {'is' if others == 1 else 'are'} reachable only "
            f"by the qualified name; an aliases: entry is what gives "
            f"{'it' if others == 1 else 'one of them'} a word of its own "
            f"(D4)")

    astray = collections.defaultdict(list)
    from fccli import completion as _completion
    for name in registry.names():
        verb = registry.get(name)
        command = getattr(verb, "gui_command", None)
        if not command:
            continue
        shop = (descriptor["commands"].get(command) or {}).get("workbench")
        domain = _completion.domain_of(verb)
        if domain and shop and domain.lower() != _plain(shop):
            astray[(domain, shop)].append(name)
    for (domain, shop), names in sorted(astray.items()):
        found.reports.append(
            f"domains: {len(names)} commands are prefixed {domain}_ and ship "
            f"in {shop} ({', '.join(sorted(names)[:3])}, ...). domain_of "
            f"reads the prefix, so `use {shop.replace('Workbench', '').lower()}` "
            f"does not scope them and `use {domain.lower()}` names a "
            f"workbench nobody switches to -- GH #21 (D4)")


def _meaningful(name):
    """The word a verb is about: the last of its underscore-joined parts.

    `poly_cut` is about cutting, `sketcher_horizontal_dimension` about a
    dimension. Wrong for a few -- `2d_offset` is about offsetting and the
    last part is right, `1_front` about the front and the last part is
    also right -- and wrong for none this rule then judges harshly: the
    finding it produces is "an aliases: entry would help here".
    """
    return name.rsplit("_", 1)[-1]


def _workbench(registry, descriptor, name):
    command = getattr(registry.get(name), "gui_command", None)
    if not command:
        return None
    return (descriptor["commands"].get(command) or {}).get("workbench")


def _plain(workbench):
    text = str(workbench or "")
    return (text[:-9] if text.endswith("Workbench") else text).lower()


# ---------------------------------------------------------------- D5

def _d5(found, registry, descriptor, QUANTITY):
    """D5: a quantity echoes in the unit it was read in.

    The lineage runs harvest -> descriptor -> step -> parse -> echo.
    Statically this module can read the first three, and the checks are
    where each link can break.

    *A unit nothing was written for.* `parse_quantity` reads a hint of
    "deg" as an angle and everything else as a length; `units._internal_unit`
    asks FreeCAD what the unit is and falls back to echoing it verbatim.
    A unit outside the harvest's own vocabulary is one no link in the
    chain was built for, and it echoes wrong rather than failing. Empty
    today: a problem.

    *A unit the factory did not carry through.* The descriptor says what
    unit the property is in; the step is built from it. A step whose unit
    is not the harvested one is the factory having dropped or changed it,
    which changes what a typed number means. Empty today: a problem.

    *A dimensionless property in millimetres.* The harvest gives an
    undimensioned property no unit at all, and `_step_from_param` reads
    the absence as its default of millimetres. So `additive_helix Turns`
    is a length: a bare `3` gets the schema's preferred length appended,
    and under ImperialBuilding that is `3in`, which FreeCAD converts to
    76.2 turns. 264 steps, so a report -- and the sharpest thing in it,
    because it is silent and it is wrong by a factor of 25.4.

    What is left to runtime. Whether the echoed string survives being read
    back is `units._round_trips`, and it needs FreeCAD's parser and the
    operator's schema: `getUserPreferred` renders compound imperial
    (`3" + 7/8"`) that does not parse, and the fallback chain that catches
    it can only be exercised live. So can the round trip through
    `Up`-recall, which is the reason the chain exists. And a
    PropertyQuantity carries its unit on the instance rather than the
    type, so what unit six of these steps are actually in is a question
    only an object can answer -- they are counted here and judged there.
    """
    params = {}
    for tid, entry in descriptor.get("types", {}).items():
        for param in entry.get("params") or []:
            params[(tid, param["name"])] = param
    census = collections.Counter()
    astray = collections.defaultdict(list)
    for name in sorted(registry.names()):
        verb = registry.get(name)
        tid = getattr(verb, "creates", None)
        command = getattr(verb, "gui_command", None)
        record = found.records.get(command)
        rel = (record or {}).get("file") or name
        blind = _declined(found, command)
        for step in verb.steps:
            if step.kind != QUANTITY:
                continue
            census[step.unit] += 1
            param = params.get((tid, step.id)) if tid else None
            found.quantities.setdefault(name, []).append(
                {"step": step.id, "unit": step.unit,
                 "property": (param or {}).get("property_type"),
                 "harvested": (param or {}).get("unit")})
            if step.unit not in HARVEST_UNITS:
                found.problem(rel, f"`{name} <{step.id}>` echoes in "
                                   f"{step.unit!r}, which the harvest cannot "
                                   f"produce -- parse_quantity reads anything "
                                   f"but 'deg' as a length, so the number "
                                   f"typed and the number stored are not the "
                                   f"same quantity", "D5")
            if param is None:
                continue
            if param.get("unit") and param["unit"] != step.unit:
                found.problem(rel, f"`{name} <{step.id}>` echoes in "
                                   f"{step.unit!r} and the descriptor harvested "
                                   f"{param['unit']!r} from {param['property_type']} "
                                   f"-- the factory did not carry the unit "
                                   f"through", "D5")
            if blind:
                continue
            if param["property_type"] in DIMENSIONLESS and step.unit == "mm":
                astray[param["property_type"]].append((name, step.id))
                if record is not None and record["checks"]["D5"] == "n/a":
                    record["checks"]["D5"] = "report"
                if record is not None:
                    record["notes"].append(
                        f"D5: `{name} <{step.id}>` is a "
                        f"{param['property_type']} and echoes in mm -- the "
                        f"harvest gave it no unit and the factory's default "
                        f"is millimetres")
            elif record is not None and record["checks"]["D5"] == "n/a":
                record["checks"]["D5"] = "pass"
    for ptype, steps in sorted(astray.items()):
        sample = ", ".join(f"{n} {s}" for n, s in sorted(steps)[:3])
        found.reports.append(
            f"units: {len(steps)} steps over {ptype} echo in mm ({sample}, "
            f"...). FreeCAD gives the property no dimension, the harvest "
            f"writes no unit, and _step_from_param reads the absence as its "
            f"default -- so a bare number takes the schema's preferred "
            f"length. A typed 3 is 3 under Standard, 3in under Building US "
            f"and stored as 76.2, and 3thou under US customary and stored "
            f"as 0.0762: wrong by 25.4 one way and 1/39.4 the other, "
            f"depending on a preference (D5)")
    runtime = sum(1 for rows in found.quantities.values() for row in rows
                  if row["property"] in RUNTIME_UNIT)
    if runtime:
        found.reports.append(
            f"units: {runtime} steps come from a Quantity property, which "
            f"carries its unit on the instance rather than the type. What "
            f"unit they echo in is a question only a live object answers, "
            f"and it is #47's runtime tier, not this one (D5)")
    found.quantities["_census"] = dict(sorted(census.items()))


# ---------------------------------------------------------------- report

def sections(found):
    """The D group's own sections of the report artifact."""
    return {
        "choices": found.choices,
        "words": found.words,
        "quantities": found.quantities,
        "blind": found.blind,
    }


def totals(found):
    counted = collections.Counter()
    for record in found.records.values():
        for rule, verdict in record["checks"].items():
            counted[f"{rule} {verdict}"] += 1
    counted["problems"] = len(found.problems)
    counted["reports"] = len(found.reports)
    return dict(sorted(counted.items()))
