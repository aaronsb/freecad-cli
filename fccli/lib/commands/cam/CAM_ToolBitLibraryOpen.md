---
command: "CAM_ToolBitLibraryOpen"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toolbit Library Manager"
  tooltip: "Opens an editor to manage toolbit libraries"
  toolbar: null
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_ToolBitLibraryOpen"
  wiki_rev: "0499378"
  seed: "3c35dc8944fc"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The ToolBit Library editor is the tool for creating, managing, and organize toolbits. Launching the library manager will display the manager as a modal dialog.

From here the user can perform all task related to toolbit management - Select a default library - Create/edit/delete Toolbits - Create libraries - Modify libraries by adding and removing toolbits - Save a library to a new name - Export a library to the LinuxCNC tooltable (.tbl) format

Only the creation of new toolshapes cannot be done from the toolbit library manager. This is an advanced topic. (see CAM ToolShape creation).

The left pane (1) shows a list of all libraries in the current working directory. The current library is highlighted.

The current working directory path is shown in the window title bar (2). A file selector (3) can be used to select a different working directory.

The right side pane (4) shows all toolbits in the currently selected library. Doubleclicking in the left column allows you to change the default tool number for this toolbit. The toolnumber will be used when creating a tool controller. The number is an attribute of the library. This means the same toolbit can exist in multiple tool libraries and have different default toolnumbers in each.

Tools at the top (5) are used to create/add/remove toolbits from the current library.

The save as button (6) can be used to write the library to a new file or export to a valid tooltable format. Currently only LinuxCNC format is supported.

The manager will remember the last active tool library and working directory between uses.

The close button (7) at bottom right will dismiss the tool library manager. Any changes to the current library are persisted to disk. Pressing the Escape key will dismiss the manager but not make any changes to the current library. Whichever library is selected when the manager is dismissed will become the new default and will be shown in the Toolbit Dock.

## See also

- CAM_ToolBitDock
- CAM_Tools
- CAM_ToolBit
