# SPDX-License-Identifier: LGPL-2.1-or-later

"""Live validation, rendered as colour.

The highlighter holds a reference to the engine because what counts as a
legal token depends on which getter is open: "Close" is an option keyword
inside polyline and a plain word everywhere else.
"""

from .qt import QtGui, QtCore
from .grammar import (POINT, QUANTITY, CHOICE, SELECTION, assignment,
                      match_choice, settable)

PALETTE = {
    "verb":     ("#4ec9b0", True),
    "unknown":  ("#f14c4c", False),
    "number":   ("#b5cea8", False),
    "bad":      ("#f14c4c", False),
    "prefix":   ("#c586c0", True),
    "option":   ("#dcdcaa", False),
    "object":   ("#9cdcfe", False),
    "sep":      ("#808080", False),

    # Coordinates carry FreeCAD's axis colours, desaturated. The viewport
    # already teaches red-green-blue for x-y-z; the command line says the
    # same thing. Muted so an x never reads as the error red, which stays
    # saturated and keeps its wavy underline.
    "axis_x":   ("#d98e73", False),
    "axis_y":   ("#8fbc7a", False),
    "axis_z":   ("#7aa6d9", False),

    # A number's dimension, named by FreeCAD's Unit.Type.
    "dim_length": ("#b5cea8", False),
    "dim_angle":  ("#c9a26d", False),
    "dim_area":   ("#a3c9a8", False),
    "dim_volume": ("#a3c9a8", False),
    "dim_mass":   ("#c9b0d9", False),
    "scalar":     ("#9cb8c9", False),
}


def _fmt(role, italic=False):
    """Weight and slant each carry one meaning.

    Bold is the verb: the token that decides what every other token means.
    Italic is anything the command line supplied rather than the person --
    a unit taken from the schema, or a suggestion not yet accepted.
    """
    colour, bold = PALETTE[role]
    f = QtGui.QTextCharFormat()
    f.setForeground(QtGui.QColor(colour))
    if bold:
        f.setFontWeight(QtGui.QFont.Bold)
    if italic:
        f.setFontItalic(True)
    if role == "bad":
        f.setUnderlineStyle(QtGui.QTextCharFormat.WaveUnderline)
        f.setUnderlineColor(QtGui.QColor(colour))
    return f


class InputHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document, console, engine):
        super().__init__(document)
        self.console = console
        self.engine = engine
        self.formats = {k: _fmt(k) for k in PALETTE}
        self.implicit_formats = {k: _fmt(k, italic=True) for k in PALETTE}

    def format_for(self, role, implicit=False):
        table = self.implicit_formats if implicit else self.formats
        return table.get(role, self.formats["number"])

    def highlightBlock(self, text):
        doc = self.document()
        if self.currentBlock().blockNumber() != doc.blockCount() - 1:
            return                              # scrollback keeps its own colour
        offset = self.console.prompt_length()
        if len(text) <= offset:
            return
        self._highlight_input(text[offset:], offset)
        self._mark_picked(text, offset)

    def _mark_picked(self, text, offset):
        """Underline what a click produced, on a line recalled from history.

        Colour already says what a token is. Underline says where it came
        from, and that clicking will replace it.
        """
        start = self.console.picked_from()
        if start is None:
            return
        at = offset + start
        length = len(text) - at
        if length <= 0:
            return
        fmt = QtGui.QTextCharFormat()
        fmt.setUnderlineStyle(QtGui.QTextCharFormat.DotLine)
        fmt.setUnderlineColor(QtGui.QColor("#7a7a7a"))
        self.setFormat(at, length, fmt)

    # ----------------------------------------------------------------------

    def _apply(self, start, length, role, implicit=False):
        if length > 0:
            table = self.implicit_formats if implicit else self.formats
            self.setFormat(start, length, table[role])

    def rehighlight_input(self):
        doc = self.document()
        self.rehighlightBlock(doc.lastBlock())

    def _highlight_input(self, body, base):
        step = self.engine.current_step()
        for start, token in _tokens(body):
            at = base + start
            if step is None:
                self._highlight_verb(token, at)
            else:
                self._highlight_argument(token, at, step)

    def _highlight_verb(self, token, at):
        hits = self.engine.registry.resolve_prefix(token)
        self._apply(at, len(token), "verb" if len(hits) == 1
                    else "unknown" if not hits else "option")

    def _highlight_argument(self, token, at, step):
        # `angle=180`: the keyword is an option, and the value after it is
        # read as the property it names takes it -- so a value that will
        # not parse is underlined where it is, not the whole token
        # (ADR-204).
        named = assignment(token)
        if named is not None:
            option = settable(self._settable(), named[0])[0]
            if option is not None and option.takes is not None:
                head = len(named[0]) + 1
                self._apply(at, head, "option")
                self._highlight_value(named[1], at + head, option.takes)
                return
        for opt in step.options:
            if opt.name.lower().startswith(token.lower()):
                self._apply(at, len(token), "option")
                return
        if step.kind == CHOICE:
            ok = bool(match_choice(step.choices, token))
            self._apply(at, len(token), "option" if ok else "unknown")
            return
        if step.kind == SELECTION:
            self._apply(at, len(token), "object" if _resolves(token) else "unknown")
            return
        if step.kind in (POINT, QUANTITY):
            self._highlight_numeric(token, at, step)
            return
        if self.engine.registry.resolve_prefix(token):
            self._apply(at, len(token), "verb")

    def _settable(self):
        """The verb's value-carrying options, wherever they are rendered."""
        engine = self.engine
        steps = engine.steps if engine.steps is not None else (
            engine.verb.steps if engine.verb else [])
        return [o for s in steps for o in s.options if o.sets]

    def _highlight_value(self, token, at, step):
        """An option's value, coloured as the kind that takes it."""
        if step.kind == CHOICE:
            ok = bool(match_choice(step.choices, token))
            self._apply(at, len(token), "option" if ok else "unknown")
        elif step.kind == SELECTION:
            self._apply(at, len(token),
                        "object" if _resolves(token) else "unknown")
        elif step.kind in (POINT, QUANTITY):
            self._highlight_numeric(token, at, step)

    def _highlight_numeric(self, token, at, step):
        from .parsing import parse_point, parse_quantity
        res = (parse_point(token, self.engine.last_point())
               if step.kind == POINT else parse_quantity(token))
        if not res.spans:
            self._apply(at, len(token), "bad" if not res.ok else "number")
            return
        for span in res.spans:
            role = span.role if span.ok else "bad"
            if role not in PALETTE:
                role = "number"
            self._apply(at + span.start, span.end - span.start, role,
                        implicit=span.implicit)


def command_spans(registry, text, offset=0):
    """Spans for a whole command line, resolved from the line itself.

    The input highlighter asks the engine what step is open. A line already
    in the scrollback has no open step -- the engine moved on -- so the verb
    is read from the first token and its own steps walked. That is what lets
    a finished command stay coloured in the transcript rather than going
    flat the moment it runs.
    """
    from .parsing import parse_point, parse_quantity
    from .grammar import POINT, QUANTITY, SELECTION, CHOICE

    out = []
    tokens = _tokens(text)
    if not tokens:
        return out

    start, first = tokens[0]
    hits = registry.resolve_prefix(first.rstrip("!"))
    verb = registry.get(hits[0]) if len(hits) == 1 else None
    out.append((offset + start, len(first), "verb" if verb else "unknown",
                False))
    if verb is None:
        return out

    # A token goes to the step whose kind it matches, which is the rule the
    # engine follows -- `circle 0,0,0 20` and `circle 20 0,0,0` both run.
    # Walking the steps in declaration order instead coloured the second
    # one entirely `bad`: the line ran, and read as a syntax error.
    options = [o for s in verb.steps for o in s.options if o.sets]
    remaining, last_point = list(verb.steps), None
    for start, token in tokens[1:]:
        # An assignment names its own target and consumes no step, the way
        # the engine reads one (ADR-204).
        named = assignment(token)
        if named is not None:
            option = settable(options, named[0])[0]
            if option is not None and option.takes is not None:
                head = len(named[0]) + 1
                out.append((offset + start, head, "option", False))
                last_point = _value_spans(out, option.takes, named[1],
                                          offset + start + head, last_point)
                continue
        step = _step_for(remaining, token)
        if step is None:
            out.append((offset + start, len(token), "option", False))
            continue
        if any(o.name.lower().startswith(token.lower()) for o in step.options):
            out.append((offset + start, len(token), "option", False))
            continue
        last_point = _value_spans(out, step, token, offset + start, last_point)
        if not step.repeat and step in remaining:
            remaining.remove(step)
    return out


def _value_spans(out, step, token, at, last_point):
    """One value's spans, read as the kind that takes it.

    Returns the point a relative coordinate after this one measures from.
    Shared by a step's own value and an option's, for the reason
    `Engine._read_value` is shared: they are one reading (ADR-204).
    """
    from .parsing import parse_point, parse_quantity

    if step.kind == POINT:
        res = parse_point(token, last_point)
        if res.ok:
            last_point = res.value
        _extend(out, res, at, len(token))
    elif step.kind == QUANTITY:
        _extend(out, parse_quantity(token, unit_hint=step.unit),
                at, len(token))
    elif step.kind == SELECTION:
        out.append((at, len(token),
                    "object" if _resolves(token) else "unknown", False))
    elif step.kind == CHOICE:
        ok = bool(match_choice(step.choices, token))
        out.append((at, len(token), "option" if ok else "unknown", False))
    else:
        out.append((at, len(token), "number", False))
    return last_point


def _step_for(remaining, token):
    """Which pending step this token belongs to, by kind.

    The same reading engine._step_for_token does: a coordinate is
    recognisably a coordinate and a scalar recognisably a scalar, and
    steps of one kind stay positional among themselves.
    """
    from .parsing import parse_quantity
    from .grammar import POINT, QUANTITY

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
    return next((s for s in remaining if s.kind == wanted), head)


def _extend(out, res, base, length):
    if not res.spans:
        out.append((base, length, "number" if res.ok else "bad", False))
        return
    for span in res.spans:
        role = span.role if span.ok else "bad"
        out.append((base + span.start, span.end - span.start,
                    role if role in PALETTE else "number", span.implicit))


def _tokens(text):
    out, i, n = [], 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        start = i
        while i < n and not text[i].isspace():
            i += 1
        if i > start:
            out.append((start, text[start:i]))
    return out


def _resolves(label):
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        if doc is None:
            return False
        return any(o.Name == label or o.Label == label for o in doc.Objects)
    except Exception:
        return False
