---
command: "Arch_Add"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Add Component"
  tooltip: "Adds the selected components to the active object"
  toolbar: "Object Tools"
  menu: "Modify"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_Add"
  wiki_rev: "0499378"
  seed: "561fcedd974e"
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

The Add tool allows you to do 4 kinds of operations:

- Add shape-based objects to an Arch component, such as a wall or structure. These objects make then part of the Arch component, and allow you to modify its shape but keeping its base properties such as width and height
- Add Arch components, such as a Arch Walls or Arch Structures, to a group-based arch object such as Arch Floors.
- Add Axis systems to structural objects
- Add objects to section planes

The counterpart of this tool is the Arch Remove tool.

## See also

- Arch_Remove
