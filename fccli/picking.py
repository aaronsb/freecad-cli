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
    """Bring ``Gui.Snapper`` into existence.

    It is installed by Draft, not by the core GUI, so it is absent until
    something pulls Draft in. Importing DraftTools is the bootstrap Draft
    documents for exactly this. Done lazily on the first point step, so
    FreeCAD starts no slower for people who never pick.
    """
    global _SNAPPER_READY
    if _SNAPPER_READY is not None:
        return _SNAPPER_READY
    if hasattr(Gui, "Snapper"):
        _SNAPPER_READY = True
        return True
    try:
        import DraftTools  # noqa: F401
    except Exception as exc:
        App.Console.PrintWarning(f"[fccli] could not load Draft: {exc}\n")
        _SNAPPER_READY = False
        return False
    _SNAPPER_READY = hasattr(Gui, "Snapper")
    if _SNAPPER_READY:
        report_grid(notify)
    return _SNAPPER_READY


_GRID_CHECKED = False


def report_grid(notify=None):
    """Say what Draft's grid is about to do, once, and change nothing.

    Bootstrapping Draft builds its grid tracker, which reads the operator's
    own `alwaysShowGrid`, `grid` and `gridSpacing` preferences. When the
    spacing is 0 the grid draws as a handful of stray lines across the
    model and Draft prints "Draft Grid: Spacing value is zero" once per
    update, three times per bootstrap.

    This used to turn the grid off and suppress the warnings. That read the
    operator's preferences and overruled them: `alwaysShowGrid` was on,
    Draft honoured it in setTrackers, and the picker switched it back off
    for the rest of the session. The command line is a way of interacting
    with FreeCAD, not a second opinion about how FreeCAD should be set up.

    So the grid is left exactly as configured, and the condition is
    reported the way every other fault is -- as a line on the command line,
    naming where to fix it.
    """
    global _GRID_CHECKED
    if _GRID_CHECKED or notify is None:
        return
    _GRID_CHECKED = True
    if not _grid_will_draw() or _grid_spacing() != 0:
        return
    notify("Draft's grid spacing is 0, so its grid draws as stray lines. "
           "Preferences -> Draft -> Grid and snapping -> Grid spacing.")


def _grid_will_draw():
    """Whether the operator has asked for the grid at all."""
    try:
        prefs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
        return prefs.GetBool("alwaysShowGrid", True) or \
            prefs.GetBool("grid", True)
    except Exception:
        return False


def _grid_spacing():
    """Draft's grid spacing as a number, read the way Draft reads it."""
    try:
        prefs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Draft")
        return App.Units.Quantity(prefs.GetString("gridSpacing", "1 mm")).Value
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
