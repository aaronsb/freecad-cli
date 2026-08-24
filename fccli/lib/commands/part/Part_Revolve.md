---
command: "Part_Revolve"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Revolve"
  tooltip: "Revolves the selected shape"
  toolbar: "Frequently-used Part WB tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Revolve"
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

Revolves the selected object around a given axis. The following shape types are allowed, and lead to the listed output shapes:

Input shape Output shape

Vertex Edge Edge Face Wire Shell Face Solid Shell Compound solid (Compsolid)

A Sketch can be used as well. Solids or compound solids are not allowed as input shapes. Normal compounds are currently not allowed either.

The Angle argument specifies how far the object is to be turned. The coordinates move the origin of the axis of revolving, relative to the origin of the coordinate system.

If you select a user defined axis, the numbers define the direction of the revolving axis with respect to the coordinate system: If the Z coordinate is 0 and the Y and X coordinate are non-zero, then the axis will lie in the X-Y-plane. Its angle is such that its tangent is the ratio of the given X and Y coordinates.
