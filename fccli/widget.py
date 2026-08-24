"""The terminal masquerade.

A QPlainTextEdit whose last block is the live input line and whose earlier
blocks are read-only scrollback. Terminal conventions are explicit bindings
here -- QPlainTextEdit gives none of them for free.
"""

import os

from .qt import Qt, QtCore, QtGui, QtWidgets
from .highlight import InputHighlighter

HISTORY_PATH = os.path.join(
    os.path.expanduser("~"), ".local", "share", "FreeCAD", "fccli", "history"
)

# Semantic roles, resolved to colour here and only here. The same names
# would map to ANSI in a terminal client.
ROLE_COLOURS = {
    "echo":   "#d4d4d4",
    "info":   "#808080",
    "error":  "#f14c4c",
    "result": "#4ec9b0",
    "prompt": "#dcdcaa",
    "head":   "#9cdcfe",   # what is being described
    "value":  "#b5cea8",   # a parsed number or coordinate
    "ok":     "#4ec9b0",   # would succeed
    "warn":   "#dcdcaa",   # succeeded, but something was dropped
    "bad":    "#f14c4c",   # would not succeed
    "quiet":  "#6a6a6a",   # footnotes
}


class Console(QtWidgets.QPlainTextEdit):
    submitted = QtCore.Signal(str)
    cancelled = QtCore.Signal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._prompt = "> "
        self._history = []
        self._hist_index = None
        self._draft = ""
        self._completions = []
        self._completion_index = 0
        self._comp_head = ""
        self._comp_inserted = None
        self._suggestion = ""
        self._search_mode = False
        self._search_buffer = ""
        self._live = False

        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        font.setPointSize(font.pointSize() + 1)
        self.setFont(font)
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setUndoRedoEnabled(False)
        self.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.setStyleSheet(
            "QPlainTextEdit { background:#1e1e1e; color:#d4d4d4;"
            " selection-background-color:#264f78; border:1px solid #333; }"
        )
        self._load_history()
        self._render_prompt()
        self.highlighter = InputHighlighter(self.document(), self, engine)

    # ------------------------------------------------------------ plumbing

    def prompt_length(self):
        return len(self._prompt)

    def input_text(self):
        block = self.document().lastBlock().text()
        return block[len(self._prompt):]

    def set_input(self, text):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        cur.movePosition(QtGui.QTextCursor.StartOfBlock)
        cur.movePosition(QtGui.QTextCursor.EndOfBlock,
                         QtGui.QTextCursor.KeepAnchor)
        cur.insertText(self._prompt + text)
        self.setTextCursor(cur)
        self._refresh_suggestion()

    def set_prompt(self, text):
        pending = self.input_text()
        self._prompt = text
        self.set_input(pending)

    def write(self, text, role="info"):
        """Insert a line into scrollback, above the live input line."""
        pending = self.input_text()
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        cur.movePosition(QtGui.QTextCursor.StartOfBlock)
        cur.movePosition(QtGui.QTextCursor.EndOfBlock,
                         QtGui.QTextCursor.KeepAnchor)
        cur.removeSelectedText()
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor(ROLE_COLOURS.get(role, "#d4d4d4")))
        cur.setCharFormat(fmt)
        cur.insertText(text)
        cur.insertBlock()
        cur.setCharFormat(QtGui.QTextCharFormat())
        cur.insertText(self._prompt + pending)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    def write_live(self, text, role="echo"):
        """Write the command being built, rewriting it in place.

        A multi-step command occupies one line that grows as each value
        lands, rather than one line per step.
        """
        if not self._live:
            self.write(text, role)
            self._live = True
            return
        doc = self.document()
        block = doc.lastBlock().previous()
        if not block.isValid():
            self.write(text, role)
            return
        cur = QtGui.QTextCursor(block)
        cur.movePosition(QtGui.QTextCursor.StartOfBlock)
        cur.movePosition(QtGui.QTextCursor.EndOfBlock,
                         QtGui.QTextCursor.KeepAnchor)
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor(ROLE_COLOURS.get(role, "#d4d4d4")))
        cur.setCharFormat(fmt)
        cur.insertText(text)
        self.moveCursor(QtGui.QTextCursor.End)
        self.ensureCursorVisible()

    def end_live(self, text=None, role="result"):
        """Finalize the live line, optionally replacing its text."""
        if self._live and text is not None:
            self.write_live(text, role)
        self._live = False

    def clear_scrollback(self):
        pending = self.input_text()
        self._live = False
        self.setPlainText("")
        self._render_prompt()
        self.set_input(pending)

    def _render_prompt(self):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        cur.insertText(self._prompt)
        self.setTextCursor(cur)

    def _at_input(self):
        cur = self.textCursor()
        last = self.document().lastBlock()
        return cur.block() == last and cur.positionInBlock() >= len(self._prompt)

    def _clamp(self):
        cur = self.textCursor()
        last = self.document().lastBlock()
        floor = last.position() + len(self._prompt)
        if cur.position() < floor:
            cur.setPosition(self.document().characterCount() - 1)
            self.setTextCursor(cur)

    # ------------------------------------------------------------- history

    def _load_history(self):
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
                self._history = [ln.rstrip("\n") for ln in fh if ln.strip()][-2000:]
        except OSError:
            self._history = []

    def append_history(self, line, persist=True):
        if not line or (self._history and self._history[-1] == line):
            return
        self._history.append(line)
        if persist:
            self._persist(line)

    def _persist(self, line):
        try:
            os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
            with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def commit_history(self, line):
        """Record a finished command in its assembled form.

        A multi-step command is typed as fragments -- "polyline", then a
        point, then another -- and none of those is worth recalling on its
        own. The provisional fragment that opened the command is dropped in
        favour of the whole thing, which is what Up should hand back.
        """
        while self._history and line.startswith(self._history[-1]):
            self._history.pop()
        self.append_history(line)

    def _history_step(self, delta):
        if not self._history:
            return
        if self._hist_index is None:
            self._draft = self.input_text()
            self._hist_index = len(self._history)
        self._hist_index = max(0, min(len(self._history), self._hist_index + delta))
        if self._hist_index == len(self._history):
            self.set_input(self._draft)
        else:
            self.set_input(self._history[self._hist_index])

    # ---------------------------------------------------------- completion

    def _candidates(self):
        text = self.input_text()
        head, _, tail = text.rpartition(" ")
        step = self.engine.current_step() or self._step_ahead(head)
        if step is not None and step.kind == "quantity" and _is_bare(tail):
            # "cylinder 5" + Tab -> "cylinder 5mm", in whatever the schema says.
            from .units import preferred
            return head, tail, [tail + preferred(
                "angle" if step.unit == "deg" else "length")]
        if step is None and not head:
            pool = self.engine.registry.names()
        elif step is not None:
            pool = list(step.option_names())
            if step.kind == "selection":
                pool += _document_labels()
            pool += self.engine.registry.names()
        else:
            pool = self.engine.registry.names()
        return head, tail, [c for c in pool if c.lower().startswith(tail.lower())]

    def _step_ahead(self, head):
        """Which getter the token being typed would land in.

        A whole command typed on one line -- "cylinder 5" -- never reaches
        the engine until Enter, so there is no current step to consult.
        Resolve the verb from the first token and count the arguments
        already given.
        """
        tokens = head.split()
        if not tokens:
            return None
        hits = self.engine.registry.resolve_prefix(tokens[0])
        if len(hits) != 1:
            return None
        verb = self.engine.registry.get(hits[0])
        index = len(tokens) - 1
        if verb is None or index >= len(verb.steps):
            return None
        return verb.steps[index]

    def _complete(self, backwards=False):
        """Tab cycles. The stem is remembered, so the second Tab does not
        re-derive candidates from the text the first Tab just inserted."""
        cycling = (self._completions
                   and self.input_text() == self._comp_inserted)
        if cycling:
            head, hits = self._comp_head, self._completions
            self._completion_index += -1 if backwards else 1
            self._completion_index %= len(hits)
        else:
            head, _tail, hits = self._candidates()
            if not hits:
                return
            self._completions = hits
            self._comp_head = head
            self._completion_index = len(hits) - 1 if backwards else 0
            if len(hits) > 1:
                self.write("  " + "  ".join(hits), "info")

        pick = hits[self._completion_index]
        text = (head + " " if head else "") + pick
        self.set_input(text)
        self._comp_inserted = text

    def _refresh_suggestion(self):
        """Fish-style ghost text from history."""
        text = self.input_text()
        self._suggestion = ""
        if text:
            for line in reversed(self._history):
                if line.startswith(text) and line != text:
                    self._suggestion = line[len(text):]
                    break
        self.viewport().update()

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self._suggestion:
            return
        painter = QtGui.QPainter(self.viewport())
        painter.setFont(self.font())
        painter.setPen(QtGui.QColor("#5a5a5a"))
        rect = self.cursorRect()
        painter.drawText(rect.right(), rect.bottom() - 3, self._suggestion)
        painter.end()

    # -------------------------------------------------------------- keymap

    def keyPressEvent(self, ev):
        key, mods = ev.key(), ev.modifiers()
        ctrl = bool(mods & Qt.ControlModifier)

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._submit()
            return
        if key == Qt.Key_Escape:
            self.set_input("")
            self.cancelled.emit()
            return
        if key == Qt.Key_Tab:
            self._complete()
            return
        if key == Qt.Key_Backtab:
            self._complete(backwards=True)
            return
        if key == Qt.Key_Up and not ctrl:
            self._history_step(-1)
            return
        if key == Qt.Key_Down and not ctrl:
            self._history_step(1)
            return
        if key == Qt.Key_Right and self._suggestion and self._at_end():
            self.set_input(self.input_text() + self._suggestion)
            return
        if ctrl and key == Qt.Key_A:
            self._move_to_input_start()
            return
        if ctrl and key == Qt.Key_E:
            self._move_to_end()
            return
        if ctrl and key == Qt.Key_U:
            self.set_input("")
            return
        if ctrl and key == Qt.Key_K:
            self._kill_to_end()
            return
        if ctrl and key == Qt.Key_W:
            self._kill_word()
            return
        if ctrl and key == Qt.Key_C:
            self.set_input("")
            self.cancelled.emit()
            return
        if key in (Qt.Key_Backspace, Qt.Key_Left, Qt.Key_Home):
            self._clamp()
            if (key == Qt.Key_Backspace
                    and self.textCursor().positionInBlock() <= len(self._prompt)):
                return
            if key == Qt.Key_Home:
                self._move_to_input_start()
                return

        self._clamp()
        super().keyPressEvent(ev)
        self._hist_index = None
        self._refresh_suggestion()

    def _at_end(self):
        return self.textCursor().position() == self.document().characterCount() - 1

    def _move_to_input_start(self):
        cur = self.textCursor()
        cur.setPosition(self.document().lastBlock().position() + len(self._prompt))
        self.setTextCursor(cur)

    def _move_to_end(self):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.End)
        self.setTextCursor(cur)

    def _kill_to_end(self):
        cur = self.textCursor()
        cur.movePosition(QtGui.QTextCursor.EndOfBlock,
                         QtGui.QTextCursor.KeepAnchor)
        cur.removeSelectedText()

    def _kill_word(self):
        cur = self.textCursor()
        floor = self.document().lastBlock().position() + len(self._prompt)
        cur.movePosition(QtGui.QTextCursor.PreviousWord,
                         QtGui.QTextCursor.KeepAnchor)
        if cur.selectionStart() < floor:
            cur.setPosition(floor, QtGui.QTextCursor.KeepAnchor)
        cur.removeSelectedText()

    def _submit(self):
        text = self.input_text()
        # Fragments of a command in progress are not worth recalling; the
        # assembled command is committed when the engine finishes it.
        if self.engine.state == "idle":
            self.append_history(text, persist=False)
        self._hist_index = None
        self._completions = []
        self._comp_inserted = None
        self._suggestion = ""
        self.set_input("")
        self.submitted.emit(text)


def _is_bare(token):
    """A number with no unit on it yet."""
    if not token:
        return False
    try:
        float(token)
    except ValueError:
        return False
    return True


def _document_labels():
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        return [o.Label for o in doc.Objects] if doc else []
    except Exception:
        return []
