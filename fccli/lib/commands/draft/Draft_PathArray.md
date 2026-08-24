---
command: "Draft_PathArray"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Path Array"
  tooltip: "Creates copies of the selected object along a selected path"
  toolbar: "3D Tools"
  menu: "Modify"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_PathArray"
  wiki_rev: "0499378"
  seed: "0a4faffa8faf"
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

The Draft PathArray command creates a regular array from a selected object by placing copies along a path. Use the Draft PathLinkArray command to create a more efficient Link array instead. Except for the type of array that is created, Link array or regular array, the Draft PathLinkArray command is identical to this command.

Both commands can be used on 2D objects created with the Draft Workbench or Sketcher Workbench, but also on many 3D objects such as those created with the Part Workbench, PartDesign Workbench or BIM Workbench.

## See also

- Draft_OrthoArray
- Draft_PolarArray
- Draft_CircularArray
- Draft_PathLinkArray
- Draft_PointArray
- Draft_PointLinkArray
