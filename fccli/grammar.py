# SPDX-License-Identifier: LGPL-2.1-or-later

"""Verb descriptors, as data.

One registry feeds three frontends: the dock widget's contextual completer,
a generated MCP tool schema, and a headless scripting API. Keeping these
declarative rather than hand-coded is what lets the same definition serve
all three.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Step kinds.
POINT = "point"
QUANTITY = "quantity"
SELECTION = "selection"
CHOICE = "choice"
TEXT = "text"
PATH = "path"


@dataclass
class Option:
    """An inline keyword accepted at a step, alongside the step's own input."""

    name: str
    doc: str = ""
    # Mutates engine state; returns True if the step is finished.
    action: Optional[Callable[[Any], bool]] = None
    # Whether typing it belongs in the line history recalls. False for one
    # that only says "that is all" -- a line naming its own parameters is
    # already complete, and `done` recorded into it was read back as part
    # of the last value.
    record: bool = True
    # Whether this option names a property the command will set, rather
    # than a way to answer or finish the step in front of it. The two read
    # differently on the prompt line, and gluing both into one bracket
    # made `The height of the cylinder [Angle]` say that height is an
    # angle (GH #56). See Step.prompt_hint.
    sets: bool = False
    # The value this option carries, as the step it would have been. None
    # for an option with nothing to give it: a boolean, where the keyword
    # alone says all there is to say, and the ways out of a step (`Close`,
    # `done`, `cancel`).
    #
    # An option that names a non-boolean property wrote `True` to it --
    # 1 degree onto an Angle whose default is 360 -- because the action
    # behind it was `_flag` under another name and there was no grammar
    # for a value (GH #81). The step is what says how to read one:
    # `angle=180` at a cylinder is the same reading as `180` at an angle
    # step, done by the same code (ADR-204).
    takes: Optional["Step"] = None


@dataclass
class Step:
    id: str
    kind: str
    prompt: str
    repeat: bool = False
    min_count: int = 1
    relative_to: Optional[str] = None
    options: List[Option] = field(default_factory=list)
    choices: List[str] = field(default_factory=list)
    default: Any = None
    unit: str = "mm"          # how a QUANTITY value is echoed back
    optional: bool = False    # bare Enter skips it, leaving the value None
    # Consume the rest of the line verbatim rather than one whitespace token.
    # For steps whose value is itself a command, a path, or a sentence.
    raw: bool = False
    # Where this step's candidates come from, when they are not the step's
    # own options or choices: "verbs", "objects", "aliases", "schemas".
    # A step whose value is a command name says so rather than being
    # guessed at by position.
    completes: Optional[str] = None
    # Where this step sits when the engine has to ask for it. Lower is
    # sooner. Points default late, so a pick is what commits a command
    # whose numbers were typed. An explicit value overrides that.
    prompt_order: Optional[int] = None
    # Run when a value lands, before the next step is asked for. A step
    # that stands for a field in an open task panel writes it there and
    # then, so the model moves as the command is answered rather than all
    # at once at the end -- which is what a panel does for a mouse, and
    # what makes cancelling it mean something. Returns a complaint, or None.
    on_accept: Optional[Callable[[Any, "Step", Any, Any], Optional[str]]] = None
    # Whether this step's value is a count rather than a measurement. The
    # property behind it takes an int and refuses a float, so a fraction
    # typed here is refused at the prompt rather than rounded at the write
    # (GH #78, ADR-203).
    integral: bool = False

    def option_names(self) -> List[str]:
        """The words a person types for this step's options.

        The word, not the name: an option that carries a value is typed
        `angle=`, and every caller of this asks what may be typed --
        completion's pool, the prompt payload, the socket's state, `man`'s
        step listing. Offering `angle` where `angle=` is what works is the
        fault GH #71 was, in the one place that advertises it (ADR-204).
        """
        return [o.name.lower() + "=" if o.takes is not None else o.name
                for o in self.options]

    def prompt_hint(self) -> str:
        """What follows this step's own prompt on the prompt line.

        Two populations shared one bracket, and read as one. What you may
        type *instead of* answering keeps it -- `[Close/Undo]` at a
        polyline's next point are alternatives to a point, and belong
        beside the thing they replace. A property the command will also
        set is not an alternative to anything, and glued into the same
        bracket it read as a hint about the value being asked for:
        `The height of the cylinder [Angle]` (GH #56, ADR-303).

        The renderers all call this rather than joining the names
        themselves. There were three of them -- the dock, the socket
        client's prompt, and its `still wants` line -- and one prompt.
        """
        instead = [o.name for o in self.options if not o.sets]
        also = [o.name.lower() + ("=" if o.takes is not None else "")
                for o in self.options if o.sets]
        line = f" [{'/'.join(instead)}]" if instead else ""
        if also:
            line += "  ·  also " + ", ".join(also)
        return line


# `angle=180`. The whole token is one assignment: the name up to the first
# `=`, and everything after it is the value, `=` and all. Anchored, unlike
# `panels.ASSIGNMENT`, which cuts several pairs out of one raw line and has
# to find its split points inside prose.
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)


def assignment(text) -> Optional[tuple]:
    """`angle=180` -> `('angle', '180')`, or None when it is not one."""
    found = ASSIGNMENT.match(text or "")
    return (found.group(1), found.group(2)) if found else None


def settable(options, name):
    """Which of a verb's settable options a typed name means.

    Returns ``(option, complaint)``. Both None means the name is no option
    of this command's, which is not an error here -- a `label=` at a text
    step is the step's own value.

    Unique prefix, exact first, which is the rule verbs, choices and panel
    fields already follow. `panels.resolve` says the same thing about a
    panel's fields, and says it about widgets rather than about options.
    """
    wanted = (name or "").strip().lower()
    if not wanted:
        return None, None
    exact = [o for o in options if o.name.lower() == wanted]
    if len(exact) == 1:
        return exact[0], None
    hits = exact or [o for o in options if o.name.lower().startswith(wanted)]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, None
    return None, (f"{name!r} names {len(hits)} of this command's options "
                  f"({', '.join(o.name for o in hits)}) -- "
                  f"use the one you mean by its full name")


def value_shape(step) -> str:
    """What an option's value looks like, for the line that asks for one."""
    if step is None:
        return "<value>"
    if step.kind == CHOICE and step.choices:
        shown = "|".join(step.choices[:4])
        return f"<{shown}{'|...' if len(step.choices) > 4 else ''}>"
    return {QUANTITY: "<number>", SELECTION: "<object>", POINT: "<x,y,z>",
            PATH: "<path>"}.get(step.kind, "<text>")


def whole_number(value) -> Optional[int]:
    """The integer a value stands for, or None when it stands for no integer.

    Everything this program parses is a float -- `parse_quantity` hands
    back `Quantity.Value` -- and FreeCAD's integer properties take an int
    and refuse a float outright, whatever the float holds: `Occurrences =
    4.0` raises where `Occurrences = 4` lands (GH #78). So the two have to
    be told apart, and in one place: the engine refuses a fraction at the
    prompt and the factory coerces at the write, and they have to agree on
    what a whole number is.

    Tolerant, because a quantity that arrives through a unit conversion
    lands a few ulps off the number that was typed -- 4in in millimetres
    and back is not exactly 4.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    nearest = round(number)
    if math.isclose(number, nearest, rel_tol=1e-9, abs_tol=1e-9):
        return int(nearest)
    return None


def match_choice(choices, text) -> List[str]:
    """Which of a choice step's values a typed token selects.

    Prefix, case-insensitive, and an exact value wins outright. The accept
    path insists on exactly one: a token that matches two is ambiguous and
    one that matches none is not a choice at all. Without the exact tier a
    value that begins a longer one selected nothing -- `view iso` could not
    reach `iso` because `isometric` is listed beside it (GH #55), while
    `view isometric` worked. The head does this already:
    `Registry.resolve_prefix` returns the exact name before it looks at
    prefixes, so a verb whose name starts another verb's is still typeable.
    A choice step now reads the same way.

    What no input selects is therefore two choices that differ only in
    case. Those are exact together, so neither is reachable, and that is
    the fault the D1 lint is left looking for.

    One function because there were four copies of the comparison: the
    accept path, the restart guard, and two in the highlighter. The lint
    that checks every choice is resolvable (GH #49) reads it here rather
    than restating it, so it cannot end up answering a question about a
    matcher the engine no longer uses.
    """
    lowered = text.lower()
    exact = [c for c in choices if c.lower() == lowered]
    if exact:
        return exact
    return [c for c in choices if c.lower().startswith(lowered)]


# What a step gets when it does not say. Selections come first -- pick the
# thing, then say what to do to it -- and points come last, so everything
# typeable is out of the way before the viewport is asked for anything.
DEFAULT_ORDER = {SELECTION: 0, CHOICE: 10, TEXT: 10, PATH: 10,
                 QUANTITY: 20, POINT: 90}


def order_of(step) -> int:
    if step.prompt_order is not None:
        return step.prompt_order
    return DEFAULT_ORDER.get(step.kind, 50)


@dataclass
class Verb:
    name: str
    steps: List[Step]
    emit: Callable[[Dict[str, Any]], Any]
    aliases: List[str] = field(default_factory=list)
    doc: str = ""
    gui_command: Optional[str] = None  # the QAction this verb usurps, if any
    creates: Optional[str] = None      # the document type it produces, if any
    # Which family the factory built this from, for the ones it did. Carried
    # rather than looked up by name: the family table holds every family in
    # the descriptor, including those register_all refused because a
    # hand-written verb already owned the name, so matching by name handed
    # `point` the TechDraw annotation family and `move` nothing at all.
    family: Optional[str] = None
    # Wrap the command in a document transaction, so one typed line is one
    # undo step. False for verbs that manage documents rather than edit them.
    transactional: bool = True
    # Whether running this belongs in the history ring. False for verbs
    # whose whole job is the ring itself -- "history clear" recorded into
    # the history it just emptied is noise.
    record: bool = True
    # Whether the factory made this rather than a person writing it. Said
    # outright, because it stopped being visible from the outside: every
    # generated verb now shares its emit with the hand-written panel verbs,
    # so the module that emit came from answers a different question than
    # it used to.
    generated: bool = False
    # Steps a verb only learns once it has started. A task panel names its
    # own parameters, and which ones it is showing depends on what has been
    # chosen in it, so they cannot be declared here. Called with the engine,
    # returns steps to ask for -- or None, leaving the verb as it stands.
    open: Optional[Callable[[Any], Optional[List["Step"]]]] = None
    # Undo whatever open() set up, when the command is cancelled rather
    # than finished. A panel left on screen with half a command in it is
    # worse than one that was never opened.
    abort: Optional[Callable[[Any], None]] = None
    # The command's own page, from fccli/lib/commands (ADR-100): what `man`
    # shows below the one-line doc. Empty for a verb with no file.
    manual: str = ""
    # The authored canonical invocation from the same file (ADR-501): the
    # line `make verify` drives and the line `man` shows. It is the
    # command's, not the verb's, so a command reachable through two doors
    # carries it on both and `man` prints it on the one it names.
    example: str = ""
    # Declared preconditions and panel handling from the same file. Read
    # by nothing yet; the engine's refusal and the panel decision come
    # with the prompt-context work.
    requires: List[str] = field(default_factory=list)
    panel: Optional[str] = None
    # The .fccli file this verb runs, when it is a script (ADR-601).
    script: Optional[str] = None
    # Which workbench brought this command: the harvested name for one the
    # descriptor knows, and the one that was activating for a command an
    # addon registered at runtime. It is the domain `use` scopes by. The
    # command-name prefix used to stand in for it, which put every Arch_
    # command in a domain called Arch that no workbench answers to, and
    # left an addon whose commands carry no prefix at all in no domain
    # (GH #21).
    workbench: Optional[str] = None


class Registry:
    def __init__(self) -> None:
        self._verbs: Dict[str, Verb] = {}
        self._aliases: Dict[str, str] = {}

    def add(self, verb: Verb) -> Verb:
        self._verbs[verb.name] = verb
        for a in verb.aliases:
            self._aliases[a.lower()] = verb.name
        return verb

    def reindex(self) -> None:
        """Rebuild the alias table from the verbs themselves.

        ``add`` only ever inserts, so an alias removed from a verb keeps
        resolving until the table is rebuilt.
        """
        self._aliases = {}
        for verb in self._verbs.values():
            for alias in verb.aliases:
                self._aliases[alias.lower()] = verb.name

    def remove(self, name: str) -> Optional[Verb]:
        verb = self._verbs.pop(name, None)
        if verb is not None:
            for a in verb.aliases:
                if self._aliases.get(a.lower()) == name:
                    del self._aliases[a.lower()]
        return verb

    def get(self, token: str) -> Optional[Verb]:
        t = token.lower()
        if t in self._verbs:
            return self._verbs[t]
        if t in self._aliases:
            return self._verbs[self._aliases[t]]
        return None

    def names(self) -> List[str]:
        return sorted(self._verbs)

    def resolve_prefix(self, token: str) -> List[str]:
        """Type a unique prefix, press Enter, it runs.

        Exact names and aliases win outright over prefix matches.
        """
        t = token.lower()
        if t in self._verbs:
            return [t]
        if t in self._aliases:
            return [self._aliases[t]]
        hits = [n for n in self._verbs if n.startswith(t)]
        hits += [self._aliases[a] for a in self._aliases if a.startswith(t)]
        return sorted(set(hits))

    def by_gui_command(self, cmd: str) -> Optional[Verb]:
        for v in self._verbs.values():
            if v.gui_command == cmd:
                return v
        return None


REGISTRY = Registry()
