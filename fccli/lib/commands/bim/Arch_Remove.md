---
command: "Arch_Remove"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Remove Component"
  tooltip: "Removes the selected components from their parents, or creates a hole in a component"
  toolbar: "Object Tools"
  menu: "Modify"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_Remove"
  wiki_rev: "0499378"
  seed: "31d7b24e0bd0"
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

The Arch Remove tools allows you to do 2 kinds of operations:

- Remove a subcomponent from an Arch object, for example remove a box that has been added to a wall, like in the Arch Add example.
- Subtract a shape-based object from an Arch component such as a Arch Wall or Arch Structure

The counterpart of this tool is the Arch Add tool.

## See also

- Arch_CutPlane
- Arch_Add
