# SPDX-License-Identifier: LGPL-2.1-or-later

"""Viewport picking.

Three backends:

``snap``     Coin3D event callbacks for the click, ``Gui.Snapper.snap()`` for
             the snapping. Snapping and trackers, no UI of its own. Default.
``getpoint`` ``Gui.Snapper.getPoint()``. Also brings ``Gui.draftToolBar``,
             which opens Draft's Point dialog in the Tasks panel -- a second
             input surface competing with the command line.
``raw``      Coin3D callbacks alone. No snapping.
"""

import FreeCAD as App
import FreeCADGui as Gui

def _is_point(value):
    return value is not None and hasattr(value, "x") and hasattr(value, "y")

_SNAPPER_READY = None


def ensure_snapper(notify=None):
    """Bring ``Gui.Snapper`` into existence, and say what Draft's grid will do.

    It is installed by Draft, not by the core GUI, so it is absent until
    something pulls Draft in. Importing DraftTools is the bootstrap Draft
    documents for exactly this. Done lazily on the first point step, so
    FreeCAD starts no slower for people who never pick.

    The report sits out here rather than inside the bootstrap because the
    bootstrap runs at most once and usually does nothing: anyone who opened
    Draft or BIM before their first pick already has a Snapper, and those
    are exactly the people who have grid preferences worth reporting on. It
    kept its own counsel for everyone it was written for.
    """
    global _SNAPPER_READY
    if _SNAPPER_READY is None:
        _SNAPPER_READY = _bootstrap_snapper()
    if _SNAPPER_READY:
        report_grid(notify)
    return _SNAPPER_READY


def _bootstrap_snapper():
    """Pull Draft in, once.

    Draft's own `setTrackers` used to be called from here. It was dropped
    as redundant -- `Snapper.snap` calls it itself, unconditionally -- and
    that moves the build of nine Coin trackers plus `grid.set()` into the
    first mouse-move callback of the first pick. On a large model that is
    a visible hitch in the frame after the click. Weighed and accepted:
    one frame inside the command the operator just started is cheaper than
    a line of setup here that reads like the grid suppression coming back.
    """
    if hasattr(Gui, "Snapper"):
        return True
    try:
        import DraftTools  # noqa: F401
    except Exception as exc:
        App.Console.PrintWarning(f"[fccli] could not load Draft: {exc}\n")
        return False
    return hasattr(Gui, "Snapper")


_GRID_REPORTED = False


def report_grid(notify=None):
    """Name Draft's zero-spacing grid once, and change nothing.

    Draft's grid tracker reads the operator's own `alwaysShowGrid`, `grid`
    and `gridSpacing`. At a spacing of 0 `gridTracker.update` empties both
    line sets and returns, leaving the axes and the human figure on screen
    with no grid between them, and prints "Draft Grid: Spacing value is
    zero" once per update.

    This used to turn the grid off and suppress those warnings, which read
    the operator's preferences and overruled them -- see the settings
    section of docs/conventions.md. The condition is reported instead.

    The flag is tested last and set only when something was said, so a
    spacing corrected mid-session is picked up: Draft carries a parameter
    observer for that key precisely because it changes while a session
    runs. Two preference reads per point step is nothing.
    """
    global _GRID_REPORTED
    if notify is None or _GRID_REPORTED:
        return
    if not _grid_will_draw() or _grid_spacing() != 0:
        return
    _GRID_REPORTED = True
    notify("Draft's grid spacing is 0, so it draws no grid -- just its axes "
           "and the human figure. Preferences -> Draft -> Grid and snapping.")


def _draft_param(name):
    """One Draft preference, read the way Draft reads it.

    Through `draftutils.params`, whose types and defaults are parsed from
    Draft's own preference pages, so a default this module never sees stays
    correct for as long as the key resolves. Only ever called once Draft
    has loaded.

    `silent=True` because a key that does not resolve is not an exception
    -- `get_param` prints and returns None, which no `except` here would
    catch. Draft calls it unguarded once per new view; this runs once per
    point prompt, and a twenty-point polyline would have put forty lines
    of Draft's diagnostic into the console this module exists to keep
    clear. None reads as falsy and nothing gets reported, which is right.
    """
    from draftutils import params
    return params.get_param(name, silent=True)


def _grid_will_draw():
    """Whether Draft is about to draw the grid, as things stand.

    `setTrackers` draws for `alwaysShowGrid` outright, and for `grid` only
    while `App.activeDraftCommand` is set. Reporting on the second without
    that check told people about a grid that was not going to appear.

    The second disjunct cannot fire from any caller today: this is reached
    only from a point step, and a point step never runs under a Draft
    command -- the verbs that reach one through `runCommand` hand picking
    to Draft's own snapper instead. It is here because it is the condition
    `setTrackers` actually applies, so the answer stays right if that ever
    changes. Nothing exercises it, and no test can until something does.
    """
    try:
        if _draft_param("alwaysShowGrid"):
            return True
        return bool(_draft_param("grid")
                    and getattr(App, "activeDraftCommand", None))
    except Exception:
        return False


def _grid_spacing():
    """Draft's grid spacing as a number, or None if it could not be read."""
    try:
        return App.Units.Quantity(_draft_param("gridSpacing")).Value
    except Exception:
        return None


def _active_view():
    doc = Gui.ActiveDocument
    return doc.ActiveView if doc is not None else None


class _ViewPicker:
    """Shared Coin3D plumbing: a click callback, optionally a move callback."""

    wants_move = False

    def __init__(self, notify=None) -> None:
        self.notify = notify
        self.backend = self.name
        self._callback = None
        self._last = None
        self._view = None
        self._cbs = []

    def start(self, callback, last=None) -> None:
        self.stop()
        view = _active_view()
        if view is None:
            # The step has already been prompted for. Returning quietly
            # left the engine waiting on a click that could never arrive,
            # with nothing said about why.
            if self.notify:
                self.notify("no 3D view to pick in -- type the point instead")
            return
        self._callback = callback
        # Only ever a point. Draft's snapper takes lastpoint straight to
        # its own tracker and raises there if it is anything else, after
        # having already part-configured it.
        self._last = last if _is_point(last) else None
        self._view = view
        self._cbs.append(
            ("SoMouseButtonEvent",
             view.addEventCallback("SoMouseButtonEvent", self._on_click)))
        if self.wants_move:
            self._cbs.append(
                ("SoLocation2Event",
                 view.addEventCallback("SoLocation2Event", self._on_move)))

    def stop(self) -> None:
        for kind, cb in self._cbs:
            try:
                self._view.removeEventCallback(kind, cb)
            except Exception:
                pass
        self._cbs = []
        self._view = None
        self._callback = None
        self._last = None
        self._teardown()

    def _teardown(self) -> None:
        pass

    def _on_move(self, info) -> None:
        pass

    def _on_click(self, info) -> None:
        if info.get("State") != "DOWN" or info.get("Button") != "BUTTON1":
            return
        pos = info.get("Position")
        if not pos or self._view is None or self._callback is None:
            return
        point = self.resolve(pos)
        if point is not None:
            self._callback(point)

    def resolve(self, pos):
        pt = self._view.getPoint(pos[0], pos[1])
        return App.Vector(pt.x, pt.y, pt.z) if pt is not None else None


class RawPicker(_ViewPicker):
    """Direct Coin3D callbacks. No snapping, no Draft UI."""

    name = "raw"


class SnapPicker(_ViewPicker):
    """Coin3D callbacks resolved through the Snapper. Snapping, no dialog."""

    name = "snap"
    wants_move = True

    def __init__(self, notify=None) -> None:
        super().__init__(notify)
        self._snapping = True

    def start(self, callback, last=None) -> None:
        if self._snapping and not ensure_snapper(self.notify):
            self._snapping = False
            self.backend = "raw (fallback)"
            if self.notify:
                self.notify("Draft did not load; picking without snapping")
        super().start(callback, last=last)

    def resolve(self, pos):
        if not self._snapping:
            return super().resolve(pos)
        try:
            point = Gui.Snapper.snap(tuple(pos), lastpoint=self._last)
        except Exception as exc:
            if self.notify:
                self.notify(f"snap failed ({exc}); using the raw point")
            point = None
        if point is not None:
            return App.Vector(point.x, point.y, point.z)
        return super().resolve(pos)

    def _on_move(self, info) -> None:
        """Let the Snapper draw.

        One call does both jobs. The snap marker says what a click would
        land on, and passing lastpoint makes Draft light its own trackLine
        from there to the cursor -- the rubber band, drawn by the code that
        already owns rubber bands in FreeCAD, in the colour the rest of
        Draft uses.
        """
        pos = info.get("Position")
        if not pos or not self._snapping:
            return
        try:
            Gui.Snapper.snap(tuple(pos), lastpoint=self._last)
        except Exception:
            pass

    def _teardown(self) -> None:
        if not self._snapping:
            return
        try:
            Gui.Snapper.off()
        except Exception:
            pass


class GetPointPicker:
    """``Gui.Snapper.getPoint``.

    Kept for comparison: it is FreeCAD's own point getter, and it opens
    Draft's Point dialog in the Tasks panel alongside the command line.
    """

    name = "getpoint"

    def __init__(self, notify=None) -> None:
        self.notify = notify
        self.backend = self.name
        self._active = False
        self._callback = None

    def start(self, callback, last=None) -> None:
        self.stop()
        if not ensure_snapper(self.notify):
            return
        self._callback = callback
        self._active = True

        def on_pick(point, *rest):
            if point is None:            # Escape inside the Snapper
                self._active = False
                return
            self._callback(point)
            if self._active:
                self.start(self._callback, last=point)

        try:
            Gui.Snapper.getPoint(last=last, callback=on_pick)
        except Exception as exc:
            self._active = False
            if self.notify:
                self.notify(f"getPoint failed: {exc}")

    def stop(self) -> None:
        self._active = False
        self._callback = None
        if not hasattr(Gui, "Snapper"):
            return
        try:
            Gui.Snapper.off()
            Gui.Snapper.getPoint()       # documented as the cancel form
        except Exception:
            pass


BACKENDS = {"snap": SnapPicker, "getpoint": GetPointPicker, "raw": RawPicker}
DEFAULT_BACKEND = "snap"


def make_picker(kind: str = DEFAULT_BACKEND, notify=None):
    return BACKENDS.get(kind, SnapPicker)(notify)
