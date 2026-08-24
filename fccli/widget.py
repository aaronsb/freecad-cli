"""The terminal masquerade.

A QPlainTextEdit whose last block is the live input line and whose earlier
blocks are read-only scrollback. Terminal conventions are explicit bindings
here -- QPlainTextEdit gives none of them for free.
"""

import os

from .qt import Qt, QtCore, QtGui, QtWidgets
from .highlight import InputHighlighter

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

    def __init__(self, engine, parent=None, session=None):
        super().__init__(parent)
        self.engine = engine
        # History belongs to the session, so a socket client and a headless
        # FreeCAD can both see it. The widget keeps only its cursor into it.
        if session is None:
            from .session import Session
            session = Session(engine)
        self.session = session
        self._prompt = "> "
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
        # A line recalled from history, and which part of it came from the
        # viewport. Underlined, because clicking replaces it.
        self._recalled = None

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
        self._render_prompt()
        self.highlighter = InputHighlighter(self.document(), self, engine)

    # ------------------------------------------------------------ plumbing

    def prompt_length(self):
        return len(self._prompt)

    def picked_from(self):
        """Where the recalled line's clicked tail starts, if any."""
        return self._recalled["from"] if self._recalled else None

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
        # Any change away from the recalled line makes it yours: the clicked
        # tail stops being up for grabs.
        if self._recalled is not None and text != self._recalled["full"]:
            self._recalled = None
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
        if not self._paint_spans(cur, text, role):
            cur.setCharFormat(_char_format(role))
            cur.insertText(text)
        cur.movePosition(QtGui.QTextCursor.End)
        cur.setCharFormat(QtGui.QTextCharFormat())
        cur.insertBlock()
        cur.setCharFormat(QtGui.QTextCharFormat())
        cur.insertText(self._prompt + pending)
        self.setTextCursor(cur)
        self.ensureCursorVisible()

    # Only these carry a command. Prose lines are prose, and running the
    # command highlighter over them paints the first word as an unknown verb.
    COMMAND_ROLES = {"echo", "result"}

    def _paint_spans(self, cursor, text, base_role):
        """Colour a finished command in the transcript the way it was typed.

        A command that goes flat the moment it runs loses exactly the thing
        that made it readable while it was being typed.
        """
        if base_role not in self.COMMAND_ROLES:
            return False
        from .highlight import command_spans
        indent = len(text) - len(text.lstrip())
        try:
            spans = command_spans(self.engine.registry, text[indent:], indent)
        except Exception:
            spans = []
        if not spans:
            return False
        cursor.setCharFormat(_char_format(base_role))
        cursor.insertText(text)
        block = cursor.block()
        for start, length, role, implicit in spans:
            span_cursor = QtGui.QTextCursor(block)
            span_cursor.setPosition(block.position() + start)
            span_cursor.setPosition(block.position() + start + length,
                                    QtGui.QTextCursor.KeepAnchor)
            span_cursor.setCharFormat(
                self.highlighter.format_for(role, implicit))
        return True

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
        cur.removeSelectedText()
        if not self._paint_spans(cur, text, role):
            cur.setCharFormat(_char_format(role))
            cur.insertText(text)
        self.moveCursor(QtGui.QTextCursor.End)
        self.ensureCursorVisible()

    def end_live(self, text=None, role="result"):
        """Finalize the live line, optionally replacing its text."""
        if self._live and text is not None:
            self.write_live(text, role)
        self._live = False
        # A line recalled from history, and which part of it came from the
        # viewport. Underlined, because clicking replaces it.
        self._recalled = None

    def clear_scrollback(self):
        pending = self.input_text()
        self._live = False
        # A line recalled from history, and which part of it came from the
        # viewport. Underlined, because clicking replaces it.
        self._recalled = None
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

    @property
    def _history(self):
        return self.session.history.entries

    def append_history(self, line, persist=True):
        return self.session.history.add(line, persist=persist)

    def commit_history(self, line):
        return self.session.history.commit(line)

    def _history_step(self, delta):
        entries = self._history
        if not entries:
            return
        if self._hist_index is None:
            self._draft = self.input_text()
            self._hist_index = len(entries)
        self._hist_index = max(0, min(len(entries), self._hist_index + delta))
        if self._hist_index == len(entries):
            self._recalled = None
            self.set_input(self._draft)
            return
        line = entries[self._hist_index]
        typed = self.session.history.recall(line)
        # Recall the whole command, and mark the part a click produced. It
        # stays visible so the shape of the last command is legible, and
        # underlined so it reads as up for grabs: Enter re-arms it and the
        # next click lands there.
        self.set_input(line)
        self._recalled = {"full": line, "typed": typed,
                          "from": len(typed)} if typed != line else None
        if getattr(self, "highlighter", None) is not None:
            self.highlighter.rehighlight_input()

    # ---------------------------------------------------------- completion

    def _candidates(self):
        from .completion import candidates
        return candidates(self.engine, self.input_text(),
                          history=self.session.history,
                          scope=self.session.scope)

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
        match = self.session.history.latest_starting(text)
        self._suggestion = match[len(text):] if match else ""
        self.viewport().update()

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self._suggestion:
            return
        painter = QtGui.QPainter(self.viewport())
        font = QtGui.QFont(self.font())
        font.setItalic(True)          # not yours until you accept it
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#5a5a5a"))
        rect = self.cursorRect()
        painter.drawText(rect.right(), rect.bottom() - 3, self._suggestion)
        painter.end()

    # -------------------------------------------------------------- keymap

    def contextMenuEvent(self, ev):
        """Right-click: repeat, or pick from recent.

        Rhino repeats the last command on a right-click here; AutoCAD offers
        a Recent Commands menu. They are the same gesture at different
        depths, so both are on it -- the top item repeats, the rest are the
        commands behind it.
        """
        from .completion import recent_commands
        menu = QtWidgets.QMenu(self)
        recent = recent_commands(self.session.history, limit=8)
        if recent:
            first = menu.addAction(f"Repeat:  {recent[0]}")
            first.triggered.connect(
                lambda _=False, line=recent[0]: self._run_recalled(line))
            if len(recent) > 1:
                menu.addSeparator()
                for line in recent[1:]:
                    action = menu.addAction(line)
                    action.triggered.connect(
                        lambda _=False, l=line: self._run_recalled(l))
            menu.addSeparator()
        for label, slot in (("Copy", self.copy), ("Paste", self.paste),
                            ("Clear scrollback", self.clear_scrollback)):
            menu.addAction(label).triggered.connect(slot)
        menu.exec(ev.globalPos())

    def _run_recalled(self, line):
        """Run a line from the menu, placing it fresh if it was clicked."""
        self.set_input(self.session.history.recall(line))
        self._submit()

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
        # Editing a recalled line makes it yours: the picked part stops
        # being up for grabs and Enter runs what is written.
        if self._recalled is not None and \
                self.input_text() != self._recalled["full"]:
            self._recalled = None
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
        recalled = self._recalled
        if recalled is not None and text == recalled["full"]:
            # Untouched since it was recalled: run the part that was typed
            # and wait for a click to place it again.
            text = recalled["typed"]
        self._recalled = None
        self._hist_index = None
        self._completions = []
        self._comp_inserted = None
        self._suggestion = ""
        self.set_input("")
        self.submitted.emit(text)


def _char_format(role):
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(QtGui.QColor(ROLE_COLOURS.get(role, "#d4d4d4")))
    return fmt


def _document_labels():
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        return [o.Label for o in doc.Objects] if doc else []
    except Exception:
        return []
