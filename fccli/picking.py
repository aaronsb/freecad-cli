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

_SNAPPER_READY = None


def ensure_snapper():
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
        quiet_grid()
    return _SNAPPER_READY


def quiet_grid():
    """Keep Draft's grid out of the scene.

    Bootstrapping Draft creates its grid tracker, which is Draft workbench
    furniture the command line never asked for. It also renders as a handful
    of stray lines when the user's Draft gridSpacing preference is 0.
    """
    snapper = getattr(Gui, "Snapper", None)
    if snapper is None:
        return
    try:
        snapper.setTrackers()
    except Exception:
        pass
    grid = getattr(snapper, "grid", None)
    if grid is None:
        return
    try:
        grid.show_always = False
        grid.show_during_command = False
        grid.off()
    except Exception:
        pass


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
            return
        self._callback = callback
        self._last = last
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
        if self._snapping and not ensure_snapper():
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
        quiet_grid()
        if point is not None:
            return App.Vector(point.x, point.y, point.z)
        return super().resolve(pos)

    def _on_move(self, info) -> None:
        """Drive the snap tracker so the user sees what will be picked."""
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
        quiet_grid()


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
        if not ensure_snapper():
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
