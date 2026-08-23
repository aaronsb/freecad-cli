"""Live validation, rendered as colour.

The highlighter holds a reference to the engine because what counts as a
legal token depends on which getter is open: "Close" is an option keyword
inside polyline and a plain word everywhere else.
"""

from .qt import QtGui, QtCore
from .grammar import POINT, QUANTITY, CHOICE, SELECTION

PALETTE = {
    "verb":     ("#4ec9b0", True),
    "unknown":  ("#f14c4c", False),
    "number":   ("#b5cea8", False),
    "bad":      ("#f14c4c", False),
    "prefix":   ("#c586c0", True),
    "option":   ("#dcdcaa", False),
    "object":   ("#9cdcfe", False),
    "sep":      ("#808080", False),
}


def _fmt(role):
    colour, bold = PALETTE[role]
    f = QtGui.QTextCharFormat()
    f.setForeground(QtGui.QColor(colour))
    if bold:
        f.setFontWeight(QtGui.QFont.Bold)
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

    def highlightBlock(self, text):
        doc = self.document()
        if self.currentBlock().blockNumber() != doc.blockCount() - 1:
            return                              # scrollback keeps its own colour
        offset = self.console.prompt_length()
        if len(text) <= offset:
            return
        self._highlight_input(text[offset:], offset)

    # ----------------------------------------------------------------------

    def _apply(self, start, length, role):
        if length > 0:
            self.setFormat(start, length, self.formats[role])

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
        for opt in step.options:
            if opt.name.lower().startswith(token.lower()):
                self._apply(at, len(token), "option")
                return
        if step.kind == CHOICE:
            ok = any(c.lower().startswith(token.lower()) for c in step.choices)
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
            self._apply(at + span.start, span.end - span.start, role)


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
