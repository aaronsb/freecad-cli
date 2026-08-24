---
command: "CAM_ToolBitDock"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Add toolbit…"
  tooltip: "Opens the toolbit selection dialog"
  toolbar: "Tool Commands"
  menu: "CAM"
  shortcut: "P, T"
  workbench: "CAMWorkbench"
  wiki: "CAM_ToolBitDock"
  wiki_rev: "0499378"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
rank: null
type: null
---

The ToolBit Dock is easily accessible from the main toolbar in the CAM workbench. Pressing the button will toggle the state of the dock. The dock is displayed in the right position by default but may be moved by the user.

The purpose of the dock is to display the currently selected library and allow the user to quickly add tool controllers to the CAM Job(s).

Double-clicking on a toolbit will create a single tool controller for the toolbit. Multi-selecting toolbits and pressing the 'Add to Job' button will create tool controllers for all toolbits in the library.

The user may also select multiple tools and use the 'add...' button at the bottom to add tool controllers for the selection.

+++ | | The top of the panel shows the name of the current library (1). All tool libraries from that location are scanned and shown in the dock. The dock will remember the last selection between uses. A manager button at the top right (4) allows the user to launch the library manager. The library manager can be used to maintain the toolbits and to select a different library. | +++

## See also

- CAM_ToolBitLibraryOpen
- CAM_Tools
- CAM_ToolBit
