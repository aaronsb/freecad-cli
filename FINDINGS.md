# Findings

What was learned building this, mostly about FreeCAD internals that are not
documented anywhere obvious. Each item below cost a debugging session; they
are recorded so the next one is cheaper.

Everything here is verified by `tests/offscreen.py`, which runs offscreen
without a FreeCAD GUI.

## Verified behaviour

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

## Answered since

**`Snapper.getPoint` does drag Draft's toolbar along.** Confirmed against a
running GUI: it opens Draft's Point dialog — `Local ΔX/ΔY/ΔZ`, *Enter
Point*, *Relative*, *Global* — in the Tasks panel, competing with the
command line for the same input.

The fix keeps the snapping and drops the dialog: take the click through
Coin3D event callbacks and resolve the screen position with
`Gui.Snapper.snap()`, which has no UI of its own. That is the `snap`
backend, now the default. `getpoint` remains selectable for comparison.

**`Gui.Snapper` does not exist until Draft is loaded.** It is installed by
Draft, not the core GUI, so a first point step raised *module 'FreeCADGui'
has no attribute 'Snapper'*. `import DraftTools` is the bootstrap Draft
documents for this; it runs lazily on the first pick, and falls back to
un-snapped picking if Draft will not load.

**FreeCAD exposes no unsaved-changes flag to Python.** `Document.isSaved()`
reports whether the document has a file at all and stays true after every
later edit; the GUI's modified flag is C++ only. The addon tracks its own
edits, so `close` can refuse instead of raising FreeCAD's modal.

## Found while wiring it up

**`package.xml` gates whether `Init.py` and `InitGui.py` run at all.** With
`<content><other>`, FreeCAD 1.1 adds the addon directory to `sys.path` and
never executes either file — no error, no warning. Declaring
`<content><workbench>` makes the loader run them. Verified by removing
`package.xml` entirely, which also restores execution via the legacy path.

**`XDG_DATA_HOME` relocates FreeCAD's own `Mod` directory.** A test harness
that repoints it to a scratch directory — to keep a run's files out of the
operator's — hides every installed addon from FreeCAD, and the run dies with
*No module named 'fccli'* before it reaches a single check. `XDG_STATE_HOME`
is safe to redirect and is where a history file belongs anyway, so the two
suites that launch a real FreeCAD set only that one.

**`GetInt(name, default)` does not create the entry it defaults.** Worth
knowing before blaming a preference that reappears after being deleted:
something is writing it, and reading is not what did. Verified directly
against a group with no entries.

**A class defined in `InitGui.py` does not survive a deferred callback.**
FreeCAD executes that file in a namespace that is discarded, so
`Gui.addCommand` from a `QTimer` callback fails with *name is not defined*.
The command class lives in `fccli/command.py` for that reason.

**The bottom dock area is already crowded.** Report View and the Python
console occupy it, so a dock added there gets a narrow column against the
right edge rather than a strip. The top area is empty, spans the full width,
and is where Rhino puts its command line.

**View → Panels needs no registration.** That menu is built from
`QMainWindow::createPopupMenu()`, which enumerates dock widgets, so any dock
added to the main window appears there automatically.

**Symlinks in `Mod` work.** An earlier failure was the `<other>` content
type, not the symlink.

**Draft's grid follows the Snapper in.** Bootstrapping Draft creates its
grid tracker, which is workbench furniture the command line never asked
for -- and it renders as a handful of stray lines across the model when the
user's Draft `gridSpacing` preference is `0`. The picker now turns
`show_always` and `show_during_command` off and hides it, rather than
rewriting the preference.

**History recorded fragments, not commands.** Each typed line went into the
ring, so a polyline built over four Enters left `polyline`, `0,0,0`,
`30,0,0`, `close` -- none of them worth recalling. Fragments are now held
provisionally and replaced by the assembled command when the engine
finishes it, which is what makes Up hand back a mouse-driven command as
editable text.

## Open

Tracked as issues:
[#1 describe](https://github.com/aaronsb/freecad-cli/issues/1) ·
[#2 live trackers](https://github.com/aaronsb/freecad-cli/issues/2) ·
[#4 alias import](https://github.com/aaronsb/freecad-cli/issues/4) ·
[#5 frecency](https://github.com/aaronsb/freecad-cli/issues/5) ·
[#6 follow mode](https://github.com/aaronsb/freecad-cli/issues/6) ·
[#7 Sketcher keys](https://github.com/aaronsb/freecad-cli/issues/7)


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
