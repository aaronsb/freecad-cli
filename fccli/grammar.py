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

    def option_names(self) -> List[str]:
        return [o.name for o in self.options]


@dataclass
class Verb:
    name: str
    steps: List[Step]
    emit: Callable[[Dict[str, Any]], Any]
    aliases: List[str] = field(default_factory=list)
    doc: str = ""
    gui_command: Optional[str] = None  # the QAction this verb usurps, if any


class Registry:
    def __init__(self) -> None:
        self._verbs: Dict[str, Verb] = {}
        self._aliases: Dict[str, str] = {}

    def add(self, verb: Verb) -> Verb:
        self._verbs[verb.name] = verb
        for a in verb.aliases:
            self._aliases[a.lower()] = verb.name
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
        """Rhino's daily path: type a unique prefix, press Enter, it runs.

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
