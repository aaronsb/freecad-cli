"""Capture the screenshots the README uses.

    xvfb-run -a freecad tools/screenshot.py

Four images. Three are widget grabs of the dock, which are faithful. The
hero is a composite: a grab of the whole window with the 3D area replaced by
View.saveImage, because grabbing an OpenGL viewport under a virtual display
comes back as flat colour.
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore, QtWidgets

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "images")

# Chosen to exercise the colouring: coordinates take axis colours, a
# stated unit stands upright where an implied one is italic, an option
# keyword and a relative point each get their own.
SESSION = [
    "new bracket",
    "box 0,0,0 90mm 90mm 8",
    "cylinder 30 55",
    "polyline -45,-45,8 @90,0,0 @0,90,0 close",
    "circle 0,0,63 3/8in",
]


def save(widget, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    widget.grab().save(path)
    App.Console.PrintMessage(f"[shot] {path}\n")
    return path


def render_view(name, width=1400, height=900):
    view = Gui.activeDocument().activeView()
    Gui.Selection.clearSelection()
    view.viewAxonometric()
    Gui.SendMsgToActiveView("ViewFit")
    path = os.path.join(OUT, name)
    view.saveImage(path, width, height, "Current")
    App.Console.PrintMessage(f"[shot] {path}\n")
    return path


def set_height(dock, height):
    mw = Gui.getMainWindow()
    dock.setMinimumHeight(min(height, 120))
    mw.resizeDocks([dock], [height], QtCore.Qt.Vertical)
    QtWidgets.QApplication.processEvents()


# ------------------------------------------------------------------ scenes

def tower(dock):
    """The stress scene: 84 commands, all of them typed."""
    dock.engine.submit("new tower")
    n, dz, twist = 14, 12.0, 14.0
    levels = []
    for i in range(n):
        t = i / (n - 1)
        s = 62.0 * (1 - t) + 18.0 * t
        a0 = math.radians(i * twist)
        z = 10.0 + i * dz
        corners = [(s * math.cos(a0 + k * math.pi / 2),
                    s * math.sin(a0 + k * math.pi / 2), z) for k in range(4)]
        levels.append(corners)
        pts = " ".join(f"{x:.4g},{y:.4g},{z:.4g}" for x, y, z in corners)
        dock.engine.submit(f"polyline {pts} close")
        dock.engine.submit(f"circle 0,0,{z:.4g} {s * 0.52:.4g}")
    for i in range(n - 1):
        for k in range(4):
            x0, y0, z0 = levels[i][k]
            x1, y1, z1 = levels[i + 1][k]
            dock.engine.submit(f"line {x0:.4g},{y0:.4g},{z0:.4g} "
                               f"@{x1 - x0:.4g},{y1 - y0:.4g},{z1 - z0:.4g}")


# ------------------------------------------------------------------- shots

def shot_console(dock):
    """A session transcript, showing what the colouring says."""
    set_height(dock, 260)
    dock.console.set_input("")
    dock.console.verticalScrollBar().setValue(0)
    QtWidgets.QApplication.processEvents()
    save(dock, "console.png")


def shot_midcommand(dock):
    """A getter open: its options in the prompt, validation as you type."""
    set_height(dock, 260)
    dock.engine.submit("polyline")
    dock.engine.submit("0,0,70")
    dock.engine.submit("@60,0,0")
    dock.console.set_input("@0,40,zz")   # the zz reddens as it is typed
    QtWidgets.QApplication.processEvents()
    save(dock, "midcommand.png")
    dock.console.set_input("")
    dock.engine.cancel()


def shot_units(dock):
    """The same command under two schemas."""
    set_height(dock, 250)
    dock.engine.submit("clear")
    dock.engine.submit("units internal")
    dock.engine.submit("cylinder 12 40")
    dock.engine.submit("units imperialbuilding")
    dock.engine.submit("cylinder 12 40")
    dock.engine.submit("box 0,0,0 3/8in 1ft 25.4mm")
    dock.console.set_input("")
    dock.console.verticalScrollBar().setValue(0)
    QtWidgets.QApplication.processEvents()
    save(dock, "units.png")
    dock.engine.submit("units internal")


def shot_check(dock):
    """The validator, showing the semantic roles it renders in."""
    set_height(dock, 330)
    dock.engine.submit("units internal")
    dock.engine.submit("clear")
    for line in ("check cylinder 12 40",
                 "check box 0,0,0 40 zz 20",
                 "check polylne 0,0,0"):
        dock.engine.submit(line)
    dock.console.set_input("")
    dock.console.verticalScrollBar().setValue(0)
    QtWidgets.QApplication.processEvents()
    save(dock, "check.png")


def shot_colour(dock):
    """Axis colours, dimensions, and italic for an implied unit."""
    set_height(dock, 260)
    dock.engine.submit("units internal")
    dock.engine.submit("clear")
    for line in ("box 10,20,30 40mm 30 20",
                 "circle 0,0,0 3/8in",
                 "cylinder 12 45deg" if False else "sphere 18mm",
                 "polyline 0,0,0 @40,-15,0 100<45 close"):
        dock.engine.submit(line)
    dock.engine.submit("polyline")
    dock.engine.submit("10,20,30")
    dock.console.set_input("@40,-15,zz")
    QtWidgets.QApplication.processEvents()
    save(dock, "colour_point.png")
    dock.console.set_input("")
    dock.engine.cancel()

    dock.engine.submit("clear")
    dock.engine.submit("cylinder")
    dock.console.set_input("12")           # bare: unit implied, italic
    QtWidgets.QApplication.processEvents()
    save(dock, "colour_implicit.png")
    dock.console.set_input("12mm")         # stated: upright
    QtWidgets.QApplication.processEvents()
    save(dock, "colour_explicit.png")
    dock.console.set_input("")
    dock.engine.cancel()


def shot_man(dock):
    set_height(dock, 380)
    dock.engine.submit("clear")
    dock.engine.submit("man cylinder")
    dock.console.set_input("")
    dock.console.verticalScrollBar().setValue(0)
    QtWidgets.QApplication.processEvents()
    save(dock, "man.png")


def _view_widget(mw):
    """The Qt widget holding the 3D view.

    The Python View3DInventor object is not a QWidget, so the widget is
    found by class name -- Gui::View3DInventor for the view itself, with the
    MDI subwindow as a fallback.
    """
    for child in mw.findChildren(QtWidgets.QWidget):
        name = child.metaObject().className()
        if "View3DInventor" in name and child.isVisible():
            return child
    mdi = mw.findChild(QtWidgets.QMdiArea)
    return mdi.activeSubWindow() if mdi else None


def _hide_panels(mw, names):
    """Quiet the window down for a portrait: no Report View full of the
    screenshot script's own output, no empty Tasks panel."""
    hidden = []
    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName() in names and d.isVisible():
            d.hide()
            hidden.append(d)
    QtWidgets.QApplication.processEvents()
    return hidden


def shot_hero(dock):
    """Whole window, with the flat-rendered viewport swapped for a real one."""
    mw = Gui.getMainWindow()
    _hide_panels(mw, {"Report view", "Tasks", "Selection view",
                      "Python console"})
    set_height(dock, 235)
    # A document of its own, so the portrait shows the scene it describes
    # rather than everything the earlier shots left behind.
    while App.listDocuments():
        dock.engine.submit("close!")
    dock.engine.submit("clear")
    from fccli.build_info import describe
    dock.console.write(
        f"FreeCAD CLI {describe()} -- {len(dock.engine.registry.names())} "
        "commands. Type man for the list, or click in the viewport.", "info")
    for line in SESSION:
        dock.engine.submit(line)
    dock.console.set_input("")
    view_png = render_view("_hero_view.png", 1600, 1100)
    mw = Gui.getMainWindow()
    QtWidgets.QApplication.processEvents()
    window_png = save(mw, "_hero_window.png")
    try:
        from PIL import Image
        widget = _view_widget(mw)
        if widget is None:
            raise RuntimeError("no 3D view widget")
        pos = widget.mapTo(mw, QtCore.QPoint(0, 0))
        ratio = mw.devicePixelRatio()
        box = (int(pos.x() * ratio), int(pos.y() * ratio),
               int((pos.x() + widget.width()) * ratio),
               int((pos.y() + widget.height()) * ratio))
        window = Image.open(window_png).convert("RGB")
        render = Image.open(view_png).convert("RGB").resize(
            (box[2] - box[0], box[3] - box[1]))
        window.paste(render, box[:2])
        hero = os.path.join(OUT, "hero.png")
        window.save(hero)
        App.Console.PrintMessage(f"[shot] {hero} (composited)\n")
    except Exception as exc:
        App.Console.PrintError(f"[shot] composite failed: {exc}\n")


def run():
    from fccli import dock as D
    dock = D.instance()
    if dock is None:
        App.Console.PrintError("[shot] no dock\n")
        QtWidgets.QApplication.quit()
        return
    Gui.getMainWindow().resize(1760, 1080)
    QtWidgets.QApplication.processEvents()

    for line in SESSION:
        dock.engine.submit(line)
    shot_console(dock)
    shot_midcommand(dock)
    shot_units(dock)
    shot_colour(dock)
    shot_check(dock)
    shot_man(dock)
    shot_hero(dock)

    tower(dock)
    render_view("tower.png", 1300, 1000)
    for tmp in ("_hero_view.png", "_hero_window.png"):
        path = os.path.join(OUT, tmp)
        os.path.exists(path) and os.remove(path)

    # Close every document through the command line, so no confirmation
    # dialog can appear on the way out. save <path> writes without a file
    # chooser; close! discards without asking.
    import tempfile
    scratch = os.path.join(tempfile.gettempdir(), "fccli-shots.FCStd")
    dock.engine.submit(f"save {scratch}")
    dock.engine.submit("close")          # clean now, so it goes quietly
    while App.listDocuments():
        dock.engine.submit("close!")     # anything still dirty is scratch
    os.path.exists(scratch) and os.remove(scratch)
    App.Console.PrintMessage("[shot] all documents closed, no dialogs\n")
    QtCore.QTimer.singleShot(400, QtWidgets.QApplication.quit)


QtCore.QTimer.singleShot(9000, run)
