"""The toggle command.

This lives in the package rather than in InitGui.py: FreeCAD executes
InitGui.py in a namespace that does not survive, so a class defined there is
gone by the time a deferred callback runs, and Gui.addCommand fails with
"name is not defined".
"""

import FreeCADGui as Gui

NAME = "FCCLI_Toggle"


class CommandLineToggle:
    def GetResources(self):
        return {
            "MenuText": "Command Line",
            "ToolTip": "Show or hide the FreeCAD CLI command line",
            "Accel": "Ctrl+`",
        }

    def IsActive(self):
        return True

    def Activated(self):
        from . import dock
        d = dock.instance()
        if d is not None and d.isVisible():
            d.hide()
        else:
            dock.show()


def register():
    Gui.addCommand(NAME, CommandLineToggle())
    return NAME
