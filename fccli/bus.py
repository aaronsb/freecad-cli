# SPDX-License-Identifier: LGPL-2.1-or-later

"""The typed message stream.

Everything the engine wants to say goes through here as a ``Message``. The
dock widget is one subscriber; an ANSI socket adapter or an MCP server would
be others, reading the identical stream.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

# Message kinds.
PROMPT = "prompt"    # engine wants input; payload: text, options, kind
OPTIONS = "options"  # the legal option keywords at this step
ECHO = "echo"        # a command line, as typed or as reconstructed
LIVE = "live"        # the command being built, rewritten in place
INFO = "info"        # chatter, optionally carrying a semantic role:
                     #   head value ok warn bad dim quiet
ERROR = "error"      # something did not parse or did not resolve
RESULT = "result"    # a command completed; payload includes replay text
STATE = "state"      # engine idle/collecting transitions
CLEAR = "clear"      # a console builtin asking for a wiped scrollback
BUFFER = "buffer"    # the line someone is typing, and who is typing it


@dataclass
class Message:
    kind: str
    text: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


class Bus:
    """Minimal synchronous pub/sub.

    Deliberately not a Qt signal: the engine must stay importable without a
    GUI so the grammar can be driven headless from ``freecadcmd``.
    """

    def __init__(self) -> None:
        self._subs: List[Callable[[Message], None]] = []

    def subscribe(self, fn: Callable[[Message], None]) -> Callable[[], None]:
        self._subs.append(fn)
        return lambda: self._subs.remove(fn)

    def emit(self, kind: str, text: str = "", **data: Any) -> None:
        msg = Message(kind=kind, text=text, data=data)
        for fn in list(self._subs):
            try:
                fn(msg)
            except Exception as exc:  # a bad subscriber must not kill a command
                import traceback
                traceback.print_exc()
                del exc
