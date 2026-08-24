---
command: "Part_Sphere"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Sphere"
  tooltip: "Creates a solid sphere"
  toolbar: "Solids"
  menu: "Primitives"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Sphere"
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

The Part Sphere command creates a parametric sphere solid. It is the result of revolving a circular arc profile around an axis. In the coordinate system defined by its Placement property, the center of the sphere is positioned at the origin, and its axis of revolution is the Z axis.

A Part Sphere can be truncated at the top and/or bottom by changing its Angle1 and/or Angle2 properties. It can be turned into a segment of a sphere by changing its Angle3 property.

## See also

- Part_Primitives
