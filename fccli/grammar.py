"""Verb descriptors, as data.

One registry feeds three frontends: the dock widget's contextual completer,
a generated MCP tool schema, and a headless scripting API. Keeping these
declarative rather than hand-coded is what lets the same definition serve
all three.
"""

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

    def option_names(self) -> List[str]:
        return [o.name for o in self.options]


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
    # Wrap the command in a document transaction, so one typed line is one
    # undo step. False for verbs that manage documents rather than edit them.
    transactional: bool = True


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
