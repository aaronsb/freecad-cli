"""What a FreeCAD process holds: one engine, one history, one floor.

The dock used to own history, which made `fccli history` impossible to
answer honestly -- a client would have been asking a Qt widget for its
scrollback, and a headless FreeCAD would have had none. History lives here
now and the widget reads it.

The floor is what makes more than one typist safe. Exactly one party holds
it, and it is busy when the engine is collecting or a line is half-typed,
rather than whenever the dock happens to have focus. That rule is what lets
a one-shot from a terminal land in the gaps of someone's session instead of
being refused all day.
"""

import os

from . import bus as _bus

HISTORY_PATH = os.path.join(
    os.path.expanduser("~"), ".local", "share", "FreeCAD", "fccli", "history")

DOCK = "dock"


class History:
    """The command ring, in assembled form.

    A multi-step command is typed as fragments -- "polyline", a point,
    another point -- and none of those is worth recalling alone. Fragments
    are held provisionally and replaced by the whole command when the engine
    finishes it.
    """

    def __init__(self, path=HISTORY_PATH, limit=2000):
        self.path = path
        self.limit = limit
        self.entries = []
        # For a command driven half by mouse, what the keyboard contributed.
        # Keyed by the full line, so the ring itself stays a list of strings
        # and everything that reads it keeps working.
        self.typed = {}
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                self.entries = [ln.rstrip("\n") for ln in fh
                                if ln.strip()][-self.limit:]
        except OSError:
            self.entries = []
        return len(self.entries)

    def add(self, line, persist=True):
        if not line or (self.entries and self.entries[-1] == line):
            return False
        self.entries.append(line)
        del self.entries[:-self.limit]
        if persist:
            self._write(line)
        return True

    def commit(self, line, typed=None):
        """Record a finished command, dropping the fragment that opened it."""
        while self.entries and line.startswith(self.entries[-1]):
            self.entries.pop()
        if typed and typed != line:
            self.typed[line] = typed
        return self.add(line)

    def recall(self, line):
        """What Up hands back for a line: the part that was typed.

        The whole line stays in the ring, so Tab still completes the picked
        tail from it. Recall gives back the half a keyboard produced, ready
        for the next click.
        """
        return self.typed.get(line, line)

    def forget(self):
        """Empty the ring, and the file behind it."""
        self.entries = []
        self.typed = {}
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            open(self.path, "w", encoding="utf-8").close()
        except OSError:
            pass

    def drop(self, line):
        """Remove a provisional entry the finished command supersedes."""
        for i in range(len(self.entries) - 1, -1, -1):
            if self.entries[i] == line:
                del self.entries[i]
                return True
        return False

    def tail(self, limit=None):
        return self.entries[-limit:] if limit else list(self.entries)

    def latest_starting(self, prefix):
        """For the ghost suggestion: the most recent line extending prefix."""
        if not prefix:
            return None
        for line in reversed(self.entries):
            if line.startswith(prefix) and line != prefix:
                return line
        return None

    def _write(self, line):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


class Floor:
    """Who may type. One at a time."""

    def __init__(self, engine):
        self.engine = engine
        self.holder = None
        self.buffer = ""

    def busy(self):
        """Mid-command, or mid-thought."""
        return self.engine.state != "idle" or bool(self.buffer.strip())

    def state(self):
        return {"holder": self.holder, "busy": self.busy(),
                "buffer": self.buffer}

    def claim(self, who, steal=False):
        if self.holder in (None, who):
            self.holder = who
            return True, None
        if steal or not self.busy():
            previous, self.holder = self.holder, who
            return True, previous
        return False, self.holder

    def release(self, who):
        if self.holder == who:
            self.holder = None
            self.buffer = ""
            return True
        return False

    def set_buffer(self, who, text):
        if self.holder not in (None, who):
            return False
        self.holder = who
        self.buffer = text
        if not text.strip() and self.engine.state == "idle":
            self.holder = None
        return True


class Session:
    """The one of each that a FreeCAD process has."""

    def __init__(self, engine, bus=None, history=None):
        self.engine = engine
        self.bus = bus if bus is not None else engine.bus
        self.history = history if history is not None else History()
        self.floor = Floor(engine)
        self._provisional = None
        # Narrows what Tab offers to one corner of FreeCAD. The thousand
        # launchers are the problem; the verbs someone chose are never
        # hidden by it.
        self.scope = None
        engine.session = self          # so a verb can reach the scope
        self.bus.subscribe(self._on_message)

    def _on_message(self, msg):
        if msg.kind != _bus.RESULT:
            return
        # The line as typed and the line as canonicalised are the same
        # command -- "box 0,0,0 40 30 20" and "box 0,0,0 40.00mm 30.00mm
        # 20.00mm" -- and prefix matching alone does not see that, because
        # units were added. Drop the provisional entry explicitly.
        if self._provisional is not None:
            self.history.drop(self._provisional)
            self._provisional = None
        if msg.data.get("record", True):
            self.history.commit(msg.data.get("replay") or msg.text,
                                typed=msg.data.get("typed"))

    def set_buffer(self, who, text):
        """Record what someone is typing, and tell everyone watching.

        One session has one line being typed, the same as it has one prompt.
        A client that cannot render it can still see who is holding it.
        """
        if not self.floor.set_buffer(who, text):
            return False
        self.bus.emit(_bus.BUFFER, text, who=who,
                      holder=self.floor.holder)
        return True

    def submit(self, text, who=DOCK):
        """Run a line, recording it provisionally so a typo can be recalled."""
        if self.engine.state == "idle":
            self._provisional = text if self.history.add(
                text, persist=False) else None
        self.floor.set_buffer(who, "")
        self.engine.submit(text)

    def documents(self):
        """What is open, with enough to tell one instance from another.

        A document name is unique only within a process, so the file path is
        what identifies a session to someone with several FreeCADs open.
        """
        import FreeCAD as App
        from .dirty import is_dirty
        out = []
        active = App.ActiveDocument
        for name in App.listDocuments():
            doc = App.getDocument(name)
            out.append({
                "name": name,
                "label": doc.Label,
                "file": doc.FileName or None,
                "objects": len(doc.Objects),
                "dirty": is_dirty(doc),
                "active": active is not None and doc.Name == active.Name,
            })
        return out

    def state(self):
        import FreeCAD as App
        engine = self.engine
        step = engine.current_step()
        doc = App.ActiveDocument
        return {
            "document": doc.Name if doc is not None else None,
            "documents": self.documents(),
            "objects": len(doc.Objects) if doc is not None else 0,
            "engine": engine.state,
            "verb": engine.verb.name if engine.verb else None,
            "step": step.id if step else None,
            "prompt": step.prompt if step else None,
            "options": step.option_names() if step else [],
            "floor": self.floor.state(),
            "scope": self.scope,
        }
