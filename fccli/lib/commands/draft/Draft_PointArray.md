---
command: "Draft_PointArray"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Point Array"
  tooltip: "Creates copies of the selected object at the points of a point object"
  toolbar: "3D Tools"
  menu: "Modify"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_PointArray"
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

The Draft PointArray command creates a regular array from a selected base object by placing copies at the points from a point object. Use the Draft PointLinkArray command to create a more efficient Link array instead. Except for the type of array that is created, Link array or regular array, the Draft PointLinkArray command is identical to this command.

The base object can be a 2D object created with the Draft Workbench or Sketcher Workbench, but also a 3D object such as those created with the Part Workbench, PartDesign Workbench or BIM Workbench.

The point object can be any object with a shape and vertices (including a Std Part containing one or more of such objects), as well as a mesh and a point cloud. Duplicate points in the point object are filtered out.

## See also

- Draft_OrthoArray
- Draft_PolarArray
- Draft_CircularArray
- Draft_PathArray
- Draft_PathLinkArray
- Draft_PointLinkArray
