# What this spike proves, and what it does not

## Proven

Verified by `tests/test_spike.py`, offscreen, 18 checks.

**Bare keys reach the command line while the viewport holds focus.** An
application-level `QObject.eventFilter` catches the first keystroke, moves
focus to the console, and forwards the event. Subsequent keys arrive
natively. A viewport click steals focus back, and the next keystroke is
recaptured. The filter fires on transitions only, so it is not on the hot
path for ordinary typing.

**Real editors keep their keys.** The focus guard tests
`QApplication.focusWidget()` against `QLineEdit`, `QTextEdit`,
`QPlainTextEdit`, `QAbstractSpinBox`, and `QComboBox`, plus
`activeModalWidget()` and `activePopupWidget()`. That covers the Python
console, the expression editor, spreadsheet cells, the property editor, and
`Gui::QuantitySpinBox` inside Task panels.

**Digits route by step, not by policy.** FreeCAD binds `0`–`6` to the
standard views as bare keys. Since no verb name starts with a digit, digits
pass through while the engine is idle and are consumed while a point or
quantity getter is open. Zero configuration, and it resolves the
highest-traffic collision on its own.

**One state machine serves typed values and picks.** A polyline built from
two typed coordinates and two simulated picks completes correctly and
replays as `polyline 0,0,0 25,0,0 @0,25,0 0,25,0`. Every value records its
typed form as it lands, so a mouse-driven command comes back from history as
editable text.

**A verb typed mid-command restarts, the way Rhino does** — but only when
the token cannot be read as input for the open step, so `c` stays the
`Close` option inside `polyline` rather than becoming `circle`.

## Not yet answered

**Whether `Snapper.getPoint` drags Draft's toolbar along.** `getPoint` sets
`self.ui = Gui.draftToolBar`, so a second input surface may appear beside
the command line. The control strip switches to a raw Coin3D picker so the
difference can be felt. This needs a running GUI to settle.

**Whether `follow` mode fights the Task panels.** Swallowing a `QAction`
trigger and opening the grammar instead is the invasive part of the design:
a bad descriptor breaks a toolbar button, and users blame FreeCAD. The
per-verb kill switch and the global `off` exist for that reason. Default is
`echo`.

**Live trackers.** Rhino rubber-bands from the last point to the cursor at
frame rate. That is Coin3D scene-graph mutation driven by `SoLocation2Event`
and it bypasses the message stream entirely — the widget and the tracker are
peers, both fed by the engine. Not built.

**Sketcher.** Bare `C`, `D`, `E` are Sketcher constraint commands pressed
mid-interaction against a selection. Under usurping they cost one extra
keystroke (Enter). Whether that is acceptable needs live-fire feedback.

**Frecency ranking.** Tab cycles alphabetically. Most-recently-used ordering
is the obvious next step and is unbuilt.

## The 195

FreeCAD ships 940 default shortcuts. 195 use unmodified keys:

```
0-6           standard views
C, D, E       Sketcher constraints
A,R  C,I  D,I two-letter Draft chords
Del End Esc
```

The Draft chords are already a command language — a bad one, with no
discoverability and no arguments. `Shortcuts.cfg` can be imported as a seed
alias file: strip the commas and `ci` + Enter does what `C,I` did. Muscle
memory survives the transition. That import is not built yet.
