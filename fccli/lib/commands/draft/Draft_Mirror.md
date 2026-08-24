---
command: "Draft_Mirror"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mirror"
  tooltip: "Mirrors the selected objects along a line defined by 2 points"
  toolbar: "3D Tools"
  menu: "Modify"
  shortcut: "M, I"
  workbench: "DraftWorkbench"
  wiki: "Draft_Mirror"
  wiki_rev: "0499378"
  seed: "85ce98f110f8"
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

The Draft Mirror command creates mirrored copies, Part Mirror objects, from selected objects. A Part Mirror object is parametric, it will update if its source object changes.

The command can be used on 2D objects created with the Draft Workbench or Sketcher Workbench, but also on many 3D objects such as those created with the Part Workbench, PartDesign Workbench or BIM Workbench.

## See also

- Draft_Clone
