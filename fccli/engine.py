# SPDX-License-Identifier: LGPL-2.1-or-later

"""The command engine.

A verb is a sequence of getters. Each getter accepts a typed value, a
viewport pick, or an option keyword through the same door, and Enter means
"advance with what you have". Every value that lands is recorded in typed
form, so a fully mouse-driven command can be replayed from history as text.
"""

from typing import Any, Dict, List, Optional

from . import bus as _bus
from . import modals
from .grammar import (CHOICE, PATH, POINT, QUANTITY, SELECTION, TEXT,
                      Registry, Step, Verb, order_of)
from .parsing import format_point, format_quantity, parse_point, parse_quantity

IDLE = "idle"
COLLECTING = "collecting"


def _selection_text(objects):
    """How a selection reads back in history: by label, so it replays."""
    return ",".join(o.Label for o in objects)


def current_selection():
    """What is selected in FreeCAD right now, as objects.

    Asked of the GUI rather than tracked here: somebody can select in the
    tree, in the viewport, or with a previous command, and all three are
    the same answer.
    """
    try:
        import FreeCADGui as Gui
        selection = getattr(Gui, "Selection", None)
        if selection is None:
            return []
        return list(selection.getSelection())
    except Exception:
        return []


def _resolve_names(text):
    """Labels or names typed at a selection step, as objects."""
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        if doc is None:
            return []
        wanted = [w.strip().lower() for w in text.split(",") if w.strip()]
        return [o for o in doc.Objects
                if o.Label.lower() in wanted or o.Name.lower() in wanted]
    except Exception:
        return []


def _open_transaction(verb, label, panel=False):
    """One typed line, one undo step.

    Objects created outside a transaction never reach the undo stack, and
    UndoMode is off by default on a document nobody has told otherwise, so
    both are set here rather than left to each emitter.

    A panel keeps its own undo and puts everything back on Cancel, so one
    wrapped around it would nest -- but only when a panel actually opened.
    Declaring every command verb non-transactional to cover that took undo
    grouping away from the 970 of them that open nothing.
    """
    if not verb.transactional or panel:
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
    def __init__(self, bus: _bus.Bus, registry: Registry, picker=None,
                 dry: bool = False) -> None:
        self.bus = bus
        self.registry = registry
        self.picker = picker
        # A dry engine resolves, parses and validates exactly as the live one
        # does, then stops instead of emitting. Same code path, so what it
        # accepts is what the live engine would accept.
        self.dry = dry
        self.state = IDLE
        self.verb: Optional[Verb] = None
        self.step_index = 0
        self.done: set = set()
        self.values: Dict[str, Any] = {}
        # Steps for this invocation, when the verb only learned them by
        # starting. None means the verb's own declared steps stand.
        self.steps: Optional[List[Step]] = None
        # Whether a command typed here is running right now. Not the same
        # as state: _finish resets to IDLE before calling emit, so for the
        # whole of the part that actually runs a command the engine reads
        # idle. Anything asking "did the command line cause this?" -- the
        # test suite's dialog watchdog, the socket's busy check -- wants
        # this rather than state.
        self.driving = 0
        self.replay: List[str] = []
        # Which replay tokens came from the viewport rather than the
        # keyboard. A command driven half by mouse can then hand back the
        # half you typed, and complete the rest from history.
        self.picked: List[int] = []
        # What Enter on an empty prompt would repeat.
        self.repeat_hint: Optional[str] = None
        self.flags: Dict[str, Any] = {}
        # Above zero while a script runs its lines: the call is the one
        # history line, the lines inside are not recorded. script_depth
        # counts scripts inside scripts, so one that runs itself stops.
        self.suppress_record = 0
        self.script_depth = 0

    # ---------------------------------------------------------------- query

    def prompt_sequence(self) -> List[Step]:
        """The verb's steps in the order they will be asked for.

        Declaration order says how a command reads; this says how it is
        filled in. A point sorts last, so `circle 20` types the size and
        then waits for a click -- and Up recalls `circle 20` to place the
        next one.
        """
        if self.verb is None:
            return []
        return sorted(self.steps if self.steps is not None else self.verb.steps,
                      key=order_of)

    def pending(self) -> List[Step]:
        """Steps still to fill, in prompt order."""
        return [s for s in self.prompt_sequence() if not self._is_filled(s)]

    def _is_filled(self, step: Step) -> bool:
        if step.id in self.done:
            return True
        got = self.values.get(step.id)
        if step.repeat:
            return False        # repeats end on Enter, not on a value
        return got is not None

    def current_step(self) -> Optional[Step]:
        if self.state != COLLECTING or self.verb is None:
            return None
        remaining = self.pending()
        return remaining[0] if remaining else None

    def wants_numeric(self) -> bool:
        """Step-aware key routing.

        When a getter is open for a point or a quantity, digits are input.
        When idle, digits belong to FreeCAD -- 1 through 6 are the standard
        views, and no verb name starts with a digit.
        """
        step = self.current_step()
        return step is not None and step.kind in (POINT, QUANTITY)

    def last_point(self) -> Optional[Any]:
        """The most recent point placed, for snapping and the rubber band.

        Only a point step holds a point. Scanning every step for anything
        list-shaped handed back the last selected object for any verb with
        a selection step -- `move` gave Draft's snapper a Part::Sphere
        where it wanted a vector, on every mouse move, which raises inside
        Draft after it has already half-configured its own tracker.
        """
        for step in reversed(self.prompt_sequence()):
            if step.kind != POINT:
                continue
            v = self.values.get(step.id)
            if isinstance(v, list) and v:
                v = v[-1]
            if v is not None and hasattr(v, "x") and hasattr(v, "y"):
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
            elif self.repeat_hint:
                # Enter on an empty prompt repeats the last command, the way
                # it does in Rhino and AutoCAD. With points asked for last,
                # that is the placement loop: click, Enter, click again.
                self._start(self.repeat_hint)
            return
        if not text:
            self._terminate_step()
            return
        self._feed_text(text)

    def cancel(self) -> None:
        if self.state == IDLE:
            return
        name = self.verb.name if self.verb else "?"
        self._abort_verb()
        self._stop_picking()
        self._reset()
        self.bus.emit(_bus.INFO, f"{name} cancelled")
        self._announce()

    def feed_point(self, vec) -> None:
        """A viewport pick arrived."""
        step = self.current_step()
        if step is None or step.kind != POINT:
            return
        self._accept(step, vec, format_point(vec), picked=True)

    # ------------------------------------------------------------- internal

    def _start(self, text: str) -> None:
        parts = text.split()
        token, rest = parts[0], parts[1:]
        force = token.endswith("!")
        if force:
            token = token[:-1]
        hits = self.registry.resolve_prefix(token)
        if not hits and ("/" in token or token.startswith(".")):
            # A path is a script to run: ./tower 20, plinth/tower 20.
            hits = self.registry.resolve_prefix("run")
            rest = [token] + rest
            token = "run"
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
        self.done = set()
        self.values = {}
        self.steps = None
        self.flags = {"force": force}
        self.replay = [self.verb.name + ("!" if force else "")]
        self.picked = []
        self._emit_live()
        if self.verb.open is not None and not self.dry:
            # A verb that finds out what to ask for by starting. A task
            # panel names its own parameters, and which it shows depends on
            # what has been chosen in it, so there is nothing to declare.
            # Not under `check`. open() runs the command, so checking one
            # would move the model, print "nothing was run", and leave a
            # task dialog registered -- which blocks every panel command
            # after it. `check` reports on the verb it can see instead.
            name = self.verb.name
            try:
                # Armed here as well as around emit. open() is where a
                # command actually runs now, so it is where a command that
                # refuses the request says so -- and a modal raised with
                # nothing armed waits for a click nobody is there to make,
                # which is the whole of what modals.py exists to stop.
                self.driving += 1
                with modals.intercepted(force=force) as caught:
                    found = self.verb.open(self)
            except Exception as exc:
                self._abort_verb()
                self._reset()
                self.bus.emit(_bus.ERROR, f"{name}: {exc}")
                self._announce()
                return
            finally:
                self.driving -= 1
            if caught:
                self._abort_verb()
                self._reset()
                self.bus.emit(_bus.ERROR, f"{name}: {caught.fault}")
                self._announce()
                return
            for notice in caught.notices:
                self.bus.emit(_bus.INFO, notice)
            if found:
                self.steps = list(found)
        while rest and self.state == COLLECTING:
            step = self.current_step()
            if step is not None and step.raw:
                # The rest of the line is one value, not a token each.
                self._feed_text(" ".join(rest))
                break
            token = rest.pop(0)
            # An inline argument goes to the step whose kind it matches, so
            # "circle 0,0,0 20" and "circle 20 0,0,0" both work and a
            # remembered line replays whatever order it was typed in.
            self._feed_text(token, step=self._step_for_token(token))
        if (self.state == COLLECTING and self.steps is not None
                and self.values):
            # A line that named its parameters is a whole command, the way
            # `circle 0,0,0 5` is. Given none, it prompts.
            self._finish()
            return
        if (self.state == COLLECTING and self.steps is None
                and self._only_optional_left()):
            # Nothing required remains, so the command is already complete.
            # "save", "new" and "help" run on Enter rather than stopping to
            # prompt for an argument the caller chose not to give.
            #
            # Not for steps a verb found by starting. Every field a panel
            # offers is optional -- ten parameters, and a command usually
            # means two -- so this would commit the panel unread.
            self._finish()
            return
        self._announce()

    def _step_for_token(self, token: str):
        """Which pending step an inline argument belongs to.

        A coordinate is recognisably a coordinate and a scalar is
        recognisably a scalar, so they are matched by kind. Steps of the
        same kind stay positional among themselves -- a box's three lengths
        are told apart by order and nothing else.
        """
        remaining = self.pending()
        if not remaining:
            return None
        head = remaining[0]
        if any(o.name.lower().startswith(token.lower()) for o in head.options):
            return head
        looks_like_point = "," in token or token[:1] in "@<" or (
            token[:1].lower() == "r" and token[1:2].isdigit())
        wanted = POINT if looks_like_point else None
        if wanted is None and parse_quantity(token, unit_hint="").ok:
            wanted = QUANTITY
        if wanted is None:
            return head
        match = next((s for s in remaining if s.kind == wanted), None)
        return match or head

    def _feed_text(self, text: str, step=None) -> None:
        # A value goes to the step whose kind it matches, whether it arrived
        # inline or at a prompt. Typing a coordinate while a length is being
        # asked for fills the coordinate: the command line can see which is
        # which, so it should not make the caller keep track.
        step = step if step is not None else self._step_for_token(text)
        if step is None:
            return
        if self._is_restart(text, step):
            return
        for opt in step.options:
            if opt.name.lower().startswith(text.lower()):
                if opt.record:
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
            res = parse_quantity(text, unit_hint=step.unit)
            if not res.ok:
                self.bus.emit(_bus.ERROR, res.error)
                return
            self._accept(step, res.value, format_quantity(res.value, step.unit))
        elif step.kind == SELECTION:
            found = _resolve_names(text)
            if not found:
                self.bus.emit(_bus.ERROR, f"no object called {text!r}")
                return
            self._accept(step, found, _selection_text(found))
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
        if step.raw or step.kind in (TEXT, PATH):
            return False        # these steps accept arbitrary text by design
        token = text.split()[0].lower()
        if any(o.name.lower().startswith(token) for o in step.options):
            return False
        if step.kind in (POINT, QUANTITY):
            probe = (parse_point(text, self.last_point()) if step.kind == POINT
                     else parse_quantity(text))
            if probe.ok:
                return False
        if step.kind == CHOICE and step.choices:
            # A choice the step declares is input, whatever else shares its
            # name. `view sketch` used to cancel view and run the sketch
            # verb; 242 verb-and-choice pairs read that way, including
            # `constrain coincident` and `additive helix`.
            if any(c.lower().startswith(token) for c in step.choices):
                return False
        if step.kind == SELECTION and _resolve_names(text):
            # An object that exists is input, and FreeCAD's default labels
            # are the verb names: Box, Cylinder, Sphere, Cone, Line, Circle,
            # Point. Typing `Box` at move's selection step cancelled move
            # and started the box verb asking for a Length, which made
            # _resolve_names unreachable for exactly the labels FreeCAD
            # hands out.
            return False
        hits = self.registry.resolve_prefix(token)
        if len(hits) != 1:
            return False
        self.bus.emit(_bus.INFO, f"{self.verb.name} cancelled")
        self._abort_verb()
        self._stop_picking()
        self._reset()
        self._start(text)
        return True

    def _accept(self, step: Step, value, typed: str, picked: bool = False
                ) -> None:
        if picked:
            self.picked.append(len(self.replay))
        if step.repeat:
            self.values.setdefault(step.id, []).append(value)
        else:
            self.values[step.id] = value
            self.done.add(step.id)
        self.replay.append(typed)
        if step.on_accept is not None and not self.dry:
            complaint = step.on_accept(self, step, value, typed)
            if complaint:
                # Taken back. values is what says a line was answered, and
                # a line that was refused had not been -- a typo'd field
                # name reported its error and then pressed the panel's OK,
                # because the value was already recorded by the time the
                # complaint arrived.
                self.replay.pop()
                if step.repeat:
                    held = self.values.get(step.id) or []
                    if held:
                        held.pop()
                    if not held:
                        self.values.pop(step.id, None)
                else:
                    self.values.pop(step.id, None)
                    self.done.discard(step.id)
                self.bus.emit(_bus.ERROR, complaint)
                self._emit_live()
                self._announce()
                return
        self._emit_live()
        if not self.pending():
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
            self.done.add(step.id)
            if not self.pending():
                self._finish()
            else:
                self._announce()
            return
        if step.kind == SELECTION:
            picked = current_selection()
            if not picked:
                self.bus.emit(_bus.ERROR,
                              "nothing selected -- select in the tree or the "
                              "viewport, or name it")
                return
            self._accept(step, picked, _selection_text(picked))
            return
        if step.default is not None:
            self._accept(step, step.default, str(step.default))
            return
        if step.optional:
            self.values[step.id] = None
            self.done.add(step.id)
            if not self.pending():
                self._finish()
            else:
                self._announce()
            return
        self.bus.emit(_bus.ERROR, f"{step.prompt} is required")

    def _finish(self) -> None:
        verb, values, flags = self.verb, self.values, dict(self.flags)
        replay = " ".join(self.replay)
        # Capture provenance before the reset clears it.
        picked = list(self.picked)
        typed = self.typed_prefix(self.replay, picked)
        self._stop_picking()
        self._reset()
        # Repeat the typed half, so the next one is placed with a fresh
        # click rather than landing on top of the last.
        self.repeat_hint = typed or replay
        if self.dry:
            self.bus.emit(_bus.RESULT, replay, verb=verb.name, replay=replay,
                          object=None, dry=True, creates=verb.creates,
                          values=values, flags=flags, picked=picked,
                          typed=typed)
            self._announce()
            return
        doc = _open_transaction(verb, replay, panel=flags.get("panel"))
        try:
            # A counter: a script's emit runs other lines through here,
            # and each of those must not reset it for the outer one.
            self.driving += 1
            with modals.intercepted(force=flags.get("force")) as caught:
                obj = verb.emit({**values, "_flags": flags, "_engine": self})
        except Exception as exc:
            _abort_transaction(doc)
            # _reset already cleared self.verb, so the verb has to be told
            # to clean up by name -- a panel verb whose commit raised left
            # its panel on screen with the engine idle behind it.
            self._abort_as(verb)
            self.bus.emit(_bus.ERROR, f"{verb.name} failed: {exc}")
            self._announce()
            return
        finally:
            self.driving -= 1
        if caught:
            # FreeCAD rejected the request. That is the same kind of answer
            # as a bad quantity, and it travels the same way -- rather than
            # waiting behind a dialog for a click nobody is there to make.
            _abort_transaction(doc)
            self.bus.emit(_bus.ERROR, f"{verb.name}: {caught.fault}")
            self._announce()
            return
        _commit_transaction(doc)
        for notice in caught.notices:
            # The command worked and had something to say. It said it in a
            # box nobody could click, so say it here instead.
            self.bus.emit(_bus.INFO, notice)
        self.bus.emit(_bus.RESULT, replay, verb=verb.name, replay=replay,
                      object=obj, picked=picked, typed=typed,
                      record=verb.record and not self.suppress_record)
        self._announce()

    def _only_optional_left(self) -> bool:
        return all(s.optional or s.default is not None for s in self.pending())

    def typed_prefix(self, replay=None, picked=None) -> str:
        """The command as far as the keyboard took it.

        Everything up to the first value that came from the viewport. That
        is what Up hands back, so the next one can be placed with a fresh
        click; the whole line stays in history for Tab to complete.
        """
        replay = self.replay if replay is None else replay
        picked = self.picked if picked is None else picked
        if not picked:
            return " ".join(replay)
        return " ".join(replay[:min(picked)])

    def _emit_live(self) -> None:
        self.bus.emit(_bus.LIVE, " ".join(self.replay),
                      picked=list(self.picked))

    def _abort_as(self, verb) -> None:
        """Let a named verb undo what starting it set up."""
        if verb is None or verb.abort is None:
            return
        try:
            verb.abort(self)
        except Exception as exc:
            self.bus.emit(_bus.ERROR, f"{verb.name}: {exc}")

    def _abort_verb(self) -> None:
        """Let a verb undo what starting it set up.

        A panel left on screen holding half a command is worse than one
        that was never opened, and the operator has already said stop.
        """
        self._abort_as(self.verb)

    def _reset(self) -> None:
        self.state = IDLE
        self.verb = None
        self.step_index = 0
        self.done = set()
        self.values = {}
        self.steps = None
        self.replay = []
        self.picked = []
        self.flags = {}

    def _announce(self) -> None:
        step = self.current_step()
        if step is None:
            self.bus.emit(_bus.PROMPT, "", step_kind=None, options=[], idle=True)
            self._stop_picking()
            return
        if step.kind == SELECTION:
            # Select the thing, then say what to do to it. Somebody who has
            # already selected should not be asked to select again.
            picked = current_selection()
            if picked:
                self._accept(step, picked, _selection_text(picked))
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
