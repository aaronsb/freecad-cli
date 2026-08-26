---
command: "Draft_Clone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clone"
  tooltip: "Creates a clone of the selected objects"
  toolbar: "Draft Modification"
  menu: "Modification"
  shortcut: "C, L"
  workbench: "DraftWorkbench"
  wiki: "Draft_Clone"
  wiki_rev: "0499378"
  seed: "033ebfdbf730"
# authored from here down; the tool never rewrites these
verb: null
example: select Box; draft_clone
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft Clone command creates linked copies, clones, of selected objects. The shape of a clone is parametric, it will update if its source object changes. But a clone does have its own position, rotation, and scale, and its own View properties. For BIM objects the command creates a special type of clone: an Arch clone.

The command can be used on 2D objects created with the Draft Workbench or Sketcher Workbench, but also on many 3D objects such as those created with the Part Workbench, PartDesign Workbench or BIM Workbench. Clones of 2D objects can be used in PartDesign Bodies.

## See also

- Draft_Scale
