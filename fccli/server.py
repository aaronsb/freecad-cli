# SPDX-License-Identifier: LGPL-2.1-or-later

"""A unix socket onto the running session.

Not a second copy of the command language reached over a wire: the server
subscribes to the same bus the dock does, and calls the same engine. One
process, one registry, one document. Starting a command from a terminal
changes the dock's prompt, because there is one prompt.

The server runs on the GUI thread. FreeCAD's API is not thread-safe and
`engine.submit` touches the document, so a worker thread would have to hand
every command back here anyway.

Socket path is per process, so several FreeCADs do not collide::

    $XDG_RUNTIME_DIR/fccli/<pid>.sock      mode 0600

Never TCP. This executes commands in a live CAD session.
"""

import json
import os
import tempfile

import FreeCAD as App

from . import bus as _bus
from .qt import QtCore, QtNetwork

PROTOCOL = 1


def socket_dir():
    root = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return os.path.join(root, "fccli")


def socket_path(pid=None):
    return os.path.join(socket_dir(), f"{pid or os.getpid()}.sock")


class Server(QtCore.QObject):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.path = socket_path()
        self._server = None
        self._clients = {}          # QLocalSocket -> dict
        self._next_id = 1
        self._unsubscribe = None

    # ------------------------------------------------------------ lifecycle

    def start(self):
        os.makedirs(socket_dir(), mode=0o700, exist_ok=True)
        QtNetwork.QLocalServer.removeServer(self.path)
        self._server = QtNetwork.QLocalServer(self)
        self._server.setSocketOptions(QtNetwork.QLocalServer.UserAccessOption)
        if not self._server.listen(self.path):
            App.Console.PrintWarning(
                f"[fccli] socket: {self._server.errorString()}\n")
            self._server = None
            return None
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        self._server.newConnection.connect(self._accept)
        self._unsubscribe = self.session.bus.subscribe(self._broadcast)
        return self.path

    def stop(self):
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        for sock in list(self._clients):
            sock.disconnectFromServer()
        self._clients.clear()
        if self._server is not None:
            self._server.close()
            self._server = None
        try:
            os.remove(self.path)
        except OSError:
            pass

    # ------------------------------------------------------------- clients

    def _accept(self):
        while self._server and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            name = f"client:{self._next_id}"
            self._next_id += 1
            self._clients[sock] = {"name": name, "buffer": b"",
                                   "subscribed": False}
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(lambda s=sock: self._drop(s))
            self._send(sock, {"kind": "hello", "protocol": PROTOCOL,
                              "pid": os.getpid(), "client": name,
                              "clients": len(self._clients),
                              **self.session.state()})

    def _drop(self, sock):
        info = self._clients.pop(sock, None)
        if info:
            self.session.floor.release(info["name"])
        sock.deleteLater()

    def _send(self, sock, payload):
        try:
            sock.write((json.dumps(payload) + "\n").encode("utf-8"))
            sock.flush()
        except Exception:
            pass

    def _broadcast(self, msg):
        if not self._clients:
            return
        payload = {"kind": msg.kind, "text": msg.text, **msg.data}
        payload.pop("object", None)          # not JSON serialisable
        line = (json.dumps(payload, default=str) + "\n").encode("utf-8")
        for sock, info in list(self._clients.items()):
            if info["subscribed"]:
                try:
                    sock.write(line)
                    sock.flush()
                except Exception:
                    pass

    # ------------------------------------------------------------ dispatch

    def _read(self, sock):
        info = self._clients.get(sock)
        if info is None:
            return
        info["buffer"] += bytes(sock.readAll())
        while b"\n" in info["buffer"]:
            line, _, info["buffer"] = info["buffer"].partition(b"\n")
            if not line.strip():
                continue
            try:
                request = json.loads(line.decode("utf-8"))
            except ValueError:
                self._send(sock, {"kind": "error", "text": "bad json"})
                continue
            self._send(sock, self._dispatch(info, request))

    def _busy(self):
        """Why a command cannot run right now, if it cannot.

        Busy is an ordinary condition, not a fault -- someone using FreeCAD
        has a dialog open a good fraction of the time.
        """
        try:
            import FreeCADGui as Gui
            if Gui.Control.activeDialog():
                return {"kind": "busy", "reason": "modal",
                        "detail": "a task panel is open", "retryable": True}
        except Exception:
            pass
        return None

    def _dispatch(self, info, request):
        op = request.get("op")
        who = info["name"]
        session, floor = self.session, self.session.floor

        if op == "ping":
            return {"kind": "pong", "pid": os.getpid()}

        if op == "state":
            return {"kind": "state", **session.state(),
                    "clients": len(self._clients)}

        if op == "buffer":
            text = request.get("text", "")
            if not session.set_buffer(who, text):
                return {"kind": "ignored", "reason": "floor",
                        "holder": floor.holder}
            return {"kind": "buffered", "holder": floor.holder}

        if op == "complete":
            from .completion import candidates
            head, tail, hits = candidates(session.engine,
                                          request.get("text", ""),
                                          history=session.history,
                                          scope=session.scope)
            return {"kind": "completions", "head": head, "tail": tail,
                    "candidates": hits[:200]}

        if op == "documents":
            return {"kind": "documents", "documents": session.documents()}

        if op == "history":
            return {"kind": "history",
                    "entries": session.history.tail(request.get("limit"))}

        if op == "subscribe":
            info["subscribed"] = True
            return {"kind": "subscribed"}

        if op == "unsubscribe":
            info["subscribed"] = False
            return {"kind": "unsubscribed"}

        if op == "claim":
            ok, holder = floor.claim(who, steal=request.get("steal", False))
            if ok:
                return {"kind": "claimed", "displaced": holder}
            return {"kind": "busy", "reason": "floor", "holder": holder,
                    "retryable": True}

        if op == "release":
            floor.release(who)
            return {"kind": "released"}

        if op == "cancel":
            session.engine.cancel()
            return {"kind": "cancelled"}

        if op == "submit":
            busy = self._busy()
            if busy:
                return busy
            # A trailing ! forces past a refusal, and a held floor is a
            # refusal. Otherwise a session whose floor is stuck cannot even
            # be told to quit.
            text = request.get("text", "")
            forced = text.split()[0].endswith("!") if text.split() else False
            ok, holder = floor.claim(
                who, steal=request.get("steal", False) or forced)
            if not ok:
                return {"kind": "busy", "reason": "floor", "holder": holder,
                        "retryable": True}
            collected = _Collector(session.bus, session.engine.registry)
            try:
                session.submit(text, who=who)
            finally:
                collected.stop()
                if session.engine.state == "idle":
                    floor.release(who)
            return {"kind": "done", **collected.summary(),
                    **session.state()}

        return {"kind": "error", "text": f"unknown op: {op!r}"}


class _Collector:
    """What one submitted line produced, so a one-shot can answer at once."""

    def __init__(self, bus, registry=None):
        self.messages = []
        self.registry = registry
        self._stop = bus.subscribe(self._on)

    def _on(self, msg):
        payload = {"kind": msg.kind, "text": msg.text}
        role = msg.data.get("role")
        if role:
            payload["role"] = role
        if msg.kind in (_bus.RESULT, _bus.LIVE, _bus.ECHO):
            # Ship the spans, not just the text. A terminal then paints a
            # command the way the dock paints it -- axis colours on a
            # coordinate, the dimension on a number, italic where the unit
            # was implied -- from the same computation rather than its own.
            payload["spans"] = self._spans(msg.text)
        if msg.kind == _bus.RESULT:
            payload["replay"] = msg.data.get("replay")
            payload["dry"] = bool(msg.data.get("dry"))
        self.messages.append(payload)

    def _spans(self, text):
        if self.registry is None or not text:
            return []
        try:
            from .highlight import command_spans
            return [[start, length, role, bool(implicit)]
                    for start, length, role, implicit
                    in command_spans(self.registry, text)]
        except Exception:
            return []

    def stop(self):
        self._stop()

    def summary(self):
        errors = [m["text"] for m in self.messages if m["kind"] == _bus.ERROR]
        results = [m for m in self.messages if m["kind"] == _bus.RESULT]
        return {"messages": self.messages,
                "errors": errors,
                "ok": not errors,
                "result": results[-1]["text"] if results else None}
