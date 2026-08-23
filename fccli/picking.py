"""Viewport picking.

Two backends. Snapper is the default because it brings FreeCAD's snapping,
tracker, and working-plane handling for free. The raw Coin3D backend exists
so the spike can answer whether Snapper's own toolbar UI gets in the way.
"""

import FreeCAD as App
import FreeCADGui as Gui


class SnapperPicker:
    """Wraps ``Gui.Snapper.getPoint`` -- FreeCAD's equivalent of GetPoint."""

    name = "snapper"

    def __init__(self) -> None:
        self._active = False
        self._callback = None

    def start(self, callback, last=None) -> None:
        self.stop()
        self._callback = callback
        self._active = True

        def on_pick(point, *rest):
            if point is None:          # Escape inside the Snapper
                self._active = False
                return
            self._callback(point)
            # Re-arm for the next pick; the engine stops us when it advances
            # past the step or the verb completes.
            if self._active:
                self.start(self._callback, last=point)

        try:
            Gui.Snapper.getPoint(last=last, callback=on_pick)
        except Exception as exc:
            App.Console.PrintError(f"[fccli] snapper unavailable: {exc}\n")
            self._active = False

    def stop(self) -> None:
        self._active = False
        self._callback = None
        try:
            Gui.Snapper.off()
            Gui.Snapper.getPoint()   # documented as the cancel form
        except Exception:
            pass


class RawPicker:
    """Direct Coin3D callbacks. No snapping, no Draft toolbar."""

    name = "raw"

    def __init__(self) -> None:
        self._cb = None
        self._view = None
        self._callback = None

    def start(self, callback, last=None) -> None:
        self.stop()
        self._callback = callback
        view = Gui.ActiveDocument and Gui.ActiveDocument.ActiveView
        if view is None:
            return
        self._view = view
        self._cb = view.addEventCallback("SoMouseButtonEvent", self._on_event)

    def _on_event(self, info):
        if info.get("Type") != "SoMouseButtonEvent":
            return
        if info.get("State") != "DOWN" or info.get("Button") != "BUTTON1":
            return
        pos = info.get("Position")
        if not pos or self._view is None:
            return
        pt = self._view.getPoint(pos[0], pos[1])
        if pt is not None and self._callback:
            self._callback(App.Vector(pt.x, pt.y, pt.z))

    def stop(self) -> None:
        if self._cb is not None and self._view is not None:
            try:
                self._view.removeEventCallback("SoMouseButtonEvent", self._cb)
            except Exception:
                pass
        self._cb = None
        self._view = None
        self._callback = None


def make_picker(kind: str = "snapper"):
    return SnapperPicker() if kind == "snapper" else RawPicker()
