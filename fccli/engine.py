"""The command engine.

A verb is a sequence of getters. Each getter accepts a typed value, a
viewport pick, or an option keyword through the same door, and Enter means
"advance with what you have". Every value that lands is recorded in typed
form, so a fully mouse-driven command can be replayed from history as text.
"""

from typing import Any, Dict, List, Optional

from . import bus as _bus
from .grammar import (CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT,
                      Registry, Step, Verb)
from .parsing import format_point, format_quantity, parse_point, parse_quantity

IDLE = "idle"
COLLECTING = "collecting"


def _open_transaction(verb, label):
    """One typed line, one undo step.

    Objects created outside a transaction never reach the undo stack, and
    UndoMode is off by default on a document nobody has told otherwise, so
    both are set here rather than left to each emitter.
    """
    if not verb.transactional:
        return None
    import FreeCAD as App
    doc = App.ActiveDocument
    if doc is None:
        return None
    try:
        doc.UndoMode = 1
        doc.openTransaction(label[:120])
    except Exception:
        return None
    return doc


def _commit_transaction(doc):
    import FreeCAD as App
    # A verb may have switched or closed the document under us.
    if doc is None or doc is not App.ActiveDocument:
        return
    try:
        doc.commitTransaction()
    except Exception:
        pass


def _abort_transaction(doc):
    import FreeCAD as App
    if doc is None or doc is not App.ActiveDocument:
        return
    try:
        doc.abortTransaction()
    except Exception:
        pass


class Engine:
    def __init__(self, bus: _bus.Bus, registry: Registry, picker=None) -> None:
        self.bus = bus
        self.registry = registry
        self.picker = picker
        self.state = IDLE
        self.verb: Optional[Verb] = None
        self.step_index = 0
        self.values: Dict[str, Any] = {}
        self.replay: List[str] = []
        self.flags: Dict[str, Any] = {}

    # ---------------------------------------------------------------- query

    def current_step(self) -> Optional[Step]:
        if self.state != COLLECTING or self.verb is None:
            return None
        if self.step_index >= len(self.verb.steps):
            return None
        return self.verb.steps[self.step_index]

    def wants_numeric(self) -> bool:
        """Step-aware key routing.

        When a getter is open for a point or a quantity, digits are input.
        When idle, digits belong to FreeCAD -- 1 through 6 are the standard
        views, and no verb name starts with a digit.
        """
        step = self.current_step()
        return step is not None and step.kind in (POINT, QUANTITY)

    def last_point(self) -> Optional[Any]:
        for step in reversed(self.verb.steps if self.verb else []):
            v = self.values.get(step.id)
            if isinstance(v, list) and v:
                return v[-1]
            if v is not None and hasattr(v, "x"):
                return v
        return None

    def option_names(self) -> List[str]:
        step = self.current_step()
        return step.option_names() if step else []

    # ----------------------------------------------------------------- run

    def submit(self, text: str) -> None:
        """Enter was pressed with ``text`` on the input line."""
        text = text.strip()
        if self.state == IDLE:
            if text:
                self._start(text)
            return
        if not text:
            self._terminate_step()
            return
        self._feed_text(text)

    def cancel(self) -> None:
        if self.state == IDLE:
            return
        name = self.verb.name if self.verb else "?"
        self._stop_picking()
        self._reset()
        self.bus.emit(_bus.INFO, f"{name} cancelled")
        self._announce()

    def feed_point(self, vec) -> None:
        """A viewport pick arrived."""
        step = self.current_step()
        if step is None or step.kind != POINT:
            return
        self._accept(step, vec, format_point(vec))

    # ------------------------------------------------------------- internal

    def _start(self, text: str) -> None:
        parts = text.split()
        token, rest = parts[0], parts[1:]
        force = token.endswith("!")
        if force:
            token = token[:-1]
        hits = self.registry.resolve_prefix(token)
        if not hits:
            self.bus.emit(_bus.ERROR, f"unknown command: {token}")
            return
        if len(hits) > 1:
            self.bus.emit(_bus.ERROR,
                          f"ambiguous: {token} -> {', '.join(hits)}")
            return
        self.verb = self.registry.get(hits[0])
        self.state = COLLECTING
        self.step_index = 0
        self.values = {}
        self.flags = {"force": force}
        self.replay = [self.verb.name + ("!" if force else "")]
        self._emit_live()
        for tok in rest:  # inline arguments, e.g. "line 0,0,0 10,0,0"
            if self.state == COLLECTING:
                self._feed_text(tok)
        if self.state == COLLECTING and self._only_optional_left():
            # Nothing required remains, so the command is already complete.
            # "save", "new" and "help" run on Enter rather than stopping to
            # prompt for an argument the caller chose not to give.
            self._finish()
            return
        self._announce()

    def _feed_text(self, text: str) -> None:
        step = self.current_step()
        if step is None:
            return
        if self._is_restart(text, step):
            return
        for opt in step.options:
            if opt.name.lower().startswith(text.lower()):
                self.replay.append(opt.name.lower())
                done = opt.action(self) if opt.action else False
                self._emit_live()
                if done:
                    self._finish()
                else:
                    self._announce()
                return

        if step.kind == POINT:
            res = parse_point(text, self.last_point())
            if not res.ok:
                self.bus.emit(_bus.ERROR, res.error)
                return
            self._accept(step, res.value, format_point(res.value))
        elif step.kind == QUANTITY:
            res = parse_quantity(text)
            if not res.ok:
                self.bus.emit(_bus.ERROR, res.error)
                return
            self._accept(step, res.value, format_quantity(res.value, step.unit))
        elif step.kind in (TEXT, PATH):
            self._accept(step, text, text)
        elif step.kind == CHOICE:
            hits = [c for c in step.choices if c.lower().startswith(text.lower())]
            if len(hits) != 1:
                self.bus.emit(_bus.ERROR, f"expected one of {step.choices}")
                return
            self._accept(step, hits[0], hits[0])
        else:
            self._accept(step, text, text)

    def _is_restart(self, text: str, step: Step) -> bool:
        """A verb name typed mid-command cancels the current one and starts it.

        Only when the token cannot be read as input for the open step, so
        "c" stays the Close option inside polyline rather than becoming
        the circle verb.
        """
        if step.kind in (TEXT, PATH):
            return False        # these steps accept arbitrary text by design
        token = text.split()[0].lower()
        if any(o.name.lower().startswith(token) for o in step.options):
            return False
        if step.kind in (POINT, QUANTITY):
            probe = (parse_point(text, self.last_point()) if step.kind == POINT
                     else parse_quantity(text))
            if probe.ok:
                return False
        hits = self.registry.resolve_prefix(token)
        if len(hits) != 1:
            return False
        self.bus.emit(_bus.INFO, f"{self.verb.name} cancelled")
        self._stop_picking()
        self._reset()
        self._start(text)
        return True

    def _accept(self, step: Step, value, typed: str) -> None:
        if step.repeat:
            self.values.setdefault(step.id, []).append(value)
        else:
            self.values[step.id] = value
        self.replay.append(typed)
        self._emit_live()
        if not step.repeat:
            self.step_index += 1
        if self.step_index >= len(self.verb.steps):
            self._finish()
        else:
            self._announce()

    def _terminate_step(self) -> None:
        """Bare Enter: advance past a repeating step, or run the verb."""
        step = self.current_step()
        if step is None:
            return
        if step.repeat:
            got = len(self.values.get(step.id, []))
            if got < step.min_count:
                self.bus.emit(_bus.ERROR,
                              f"need at least {step.min_count} more for {step.id}")
                return
            self.step_index += 1
            if self.step_index >= len(self.verb.steps):
                self._finish()
            else:
                self._announce()
            return
        if step.default is not None:
            self._accept(step, step.default, str(step.default))
            return
        if step.optional:
            self.values[step.id] = None
            self.step_index += 1
            if self.step_index >= len(self.verb.steps):
                self._finish()
            else:
                self._announce()
            return
        self.bus.emit(_bus.ERROR, f"{step.prompt} is required")

    def _finish(self) -> None:
        verb, values, flags = self.verb, self.values, dict(self.flags)
        replay = " ".join(self.replay)
        self._stop_picking()
        self._reset()
        doc = _open_transaction(verb, replay)
        try:
            obj = verb.emit({**values, "_flags": flags, "_engine": self})
        except Exception as exc:
            _abort_transaction(doc)
            self.bus.emit(_bus.ERROR, f"{verb.name} failed: {exc}")
            self._announce()
            return
        _commit_transaction(doc)
        self.bus.emit(_bus.RESULT, replay,
                      verb=verb.name, replay=replay, object=obj)
        self._announce()

    def _only_optional_left(self) -> bool:
        remaining = self.verb.steps[self.step_index:] if self.verb else []
        return all(s.optional or s.default is not None for s in remaining)

    def _emit_live(self) -> None:
        self.bus.emit(_bus.LIVE, " ".join(self.replay))

    def _reset(self) -> None:
        self.state = IDLE
        self.verb = None
        self.step_index = 0
        self.values = {}
        self.replay = []
        self.flags = {}

    def _announce(self) -> None:
        step = self.current_step()
        if step is None:
            self.bus.emit(_bus.PROMPT, "", step_kind=None, options=[], idle=True)
            self._stop_picking()
            return
        self.bus.emit(_bus.PROMPT, step.prompt, step_kind=step.kind,
                      options=step.option_names(), idle=False)
        if step.kind == POINT and self.picker:
            self.picker.start(self.feed_point, last=self.last_point())
        else:
            self._stop_picking()

    def _stop_picking(self) -> None:
        if self.picker:
            self.picker.stop()
