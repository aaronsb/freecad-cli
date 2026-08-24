---
command: "Part_ShapeFromMesh"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Shape From Mesh"
  tooltip: "Creates a shape from the selected mesh"
  toolbar: null
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_ShapeFromMesh"
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

The Part ShapeFromMesh command creates shapes from mesh objects. Mesh objects have limited editing capabilities in FreeCAD, converting them to shapes will allow their use with many more boolean and modification commands.

The inverse operation is Mesh FromPartShape from the Mesh Workbench.

## See also

- Part_MakeSolid
- Part_RefineShape
- Part_PointsFromMesh
