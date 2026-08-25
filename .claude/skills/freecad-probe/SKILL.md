---
name: freecad-probe
description: Drive a real FreeCAD GUI under Xvfb to confirm a change works in the app — build a shape, read a prompt, check a verb runs — without opening a window on the operator's screen or leaving FreeCAD running. Use when a change needs verifying live rather than only in the offscreen suite, when writing or running a probe script, or when make bvt / make socket behaves oddly. Triggers on "check it in the real app", "run it under Xvfb", "does this work live", "the GUI", "probe FreeCAD", "bvt".
---

# Driving a real FreeCAD, safely

The offscreen suite (`make test`) covers the grammar with no GUI. Anything
that needs a window — a panel opening, the picker, the prompt repainting, a
command actually running — needs a real FreeCAD. Drive it under Xvfb so it
never opens on the operator's screen.

## The two invariants that will bite

- **`QT_QPA_PLATFORM=xcb` is mandatory.** Qt6 reads its platform from
  `XDG_SESSION_TYPE`, so on a Wayland session `xvfb-run`'s `DISPLAY` is
  ignored and FreeCAD opens on the operator's actual screen. Every probe
  and both `make bvt`/`make socket` set it.
- **Never `pkill -f Xvfb` in a compound Bash command.** It kills the
  agent's own process tree and returns exit 144 with no output. If you must
  clean up a stray Xvfb, do it in a standalone call, and prefer letting the
  probe quit itself.

## A probe script

```python
import sys
from PySide6 import QtCore, QtWidgets
def say(t): print("PROBE " + t, flush=True)
def run():
    try:
        from fccli import dock as D
        dock = D.instance()
        P = lambda: QtWidgets.QApplication.processEvents()
        dock.session.submit("box 0,0,0 10 10 10"); P()
        say("objects: " + ",".join(o.Name for o in __import__("FreeCAD").ActiveDocument.Objects))
    except Exception:
        import traceback; say("ERROR " + traceback.format_exc().replace(chr(10), " // "))
    QtCore.QTimer.singleShot(200, QtWidgets.QApplication.quit)
QtCore.QTimer.singleShot(9000, run)          # wait for the dock to load
QtCore.QTimer.singleShot(45000, QtWidgets.QApplication.quit)   # backstop
```

- `singleShot(9000, run)` waits for the dock; the addon loads a few seconds
  after FreeCAD's main window.
- Print `PROBE`-prefixed lines and `flush=True`, so you can grep them out of
  FreeCAD's own chatter.
- Flatten a traceback onto one line (`replace(chr(10), " // ")`) — a bare
  newline loses the prefix and the message with it.
- Drive through the session, not the widgets: `dock.session.submit(line)`
  then `processEvents()`. Read state off `dock.session`, `dock.console`,
  `dock.engine`, or `FreeCAD.ActiveDocument`.

## Running it

```bash
QT_QPA_PLATFORM=xcb timeout 90 \
  xvfb-run -a -s "-screen 0 1600x1000x24" freecad /path/to/probe.py \
  > /tmp/…/probe.out 2>&1
grep -a "^PROBE" /tmp/…/probe.out
```

Write the probe to the scratchpad, not the repo. `timeout` plus the backstop
timer means a hung probe ends on its own.

## Driving from outside, over the socket

For a change to the socket path, drive a running instance with `bin/fccli`:

```bash
bin/fccli start --headless --timeout 120     # starts one under Xvfb
bin/fccli exec 'box 0,0,0 10 10 10'
bin/fccli exec 'man cylinder'
bin/fccli cancel && bin/fccli exec 'quit!'   # ALWAYS end this way
```

**Never leave FreeCAD running.** `bin/fccli cancel` clears any open step,
then `exec 'quit!'`. `quit!` on its own is read as input for an open step
and hangs.

## What a probe is for

Confirming the app does the thing — a shape is created, a prompt reads what
you expect, a refusal fires. It is not a substitute for the suites: land the
offscreen checks in `tests/offscreen.py` and the GUI ones in `tests/bvt.py`.
A probe is how you find out what to assert.
