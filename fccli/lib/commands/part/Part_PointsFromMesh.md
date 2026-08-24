---
command: "Part_PointsFromMesh"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Points From Shape"
  tooltip: "Creates distributed points from the selected shape"
  toolbar: null
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_PointsFromMesh"
  wiki_rev: "0499378"
  seed: "394bcb7f50c7"
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

The Part PointsFromMesh command creates points objects from geometric objects.

The resulting shapes are compounds of vertices, which can be used as reference to further create lines, sketches and faces with other commands, like those from the Sketcher or the Draft workbenches.

## See also

- Part_ShapeFromMesh
- Part_MakeSolid
- Part_RefineShape
