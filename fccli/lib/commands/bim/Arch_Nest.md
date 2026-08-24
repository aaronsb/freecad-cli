---
command: "Arch_Nest"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Nest"
  tooltip: "Nests a series of selected shapes in a container"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_Nest"
  wiki_rev: "0499378"
  seed: "5c95e2ed40bf"
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

The Arch Nest tool allows to select a flat shape to be a container, and a series of other flat shapes to be organized inside the space defined by the container shape. This is typically needed for CNC operations, where you want to cut a series of pieces out of a base panel, and need to organize those pieces in the best possible compact way so they occupy less space on the panel.

The algorithm behind the Nest tool is in constant evolution, and is currently not fully optimized. In the future the performance of this tool should become much better.

## See also

- Arch_Panel
- Arch_Panel_Sheet
