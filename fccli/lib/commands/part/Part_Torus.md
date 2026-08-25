---
command: "Part_Torus"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Torus"
  tooltip: "Creates a solid torus"
  toolbar: "Solids"
  menu: "Primitives"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Torus"
  wiki_rev: "0499378"
  seed: "595ea867da67"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part Torus command creates a parametric torus solid, a doughnut shape. It is the result of sweeping a circular profile around a circular path. In the coordinate system defined by its Placement property, the circular path of the torus lies on the XY plane with its center at the origin.

A Part Torus can be turned into a segment of a torus by changing its Angle3 property. By changing its Angle1 and/or Angle2 properties the swept profile can become a segment of a circle.

## See also

- Part_Primitives
