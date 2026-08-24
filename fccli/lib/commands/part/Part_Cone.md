---
command: "Part_Cone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cone"
  tooltip: "Creates a solid cone"
  toolbar: "Solids"
  menu: "Primitives"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Cone"
  wiki_rev: "0499378"
  seed: "b00251c602fd"
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

The Part Cone command creates a parametric cone solid. In the coordinate system defined by its Placement property, the bottom face of the cone lies on the XY plane with its center at the origin.

The default Part Cone is truncated. It can be turned into a full, untruncated, cone by changing its Radius1 or Radius2 property to zero. It can be turned into a segment of a cone by changing its Angle property.

## See also

- Part_Primitives
