---
command: "FEM_ConstraintTransform"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Local Coordinate System"
  tooltip: "Creates a local coordinate system on a face"
  toolbar: "Geometrical Analysis Features"
  menu: "Geometrical Analysis Features"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ConstraintTransform"
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

Transforms the coordinate system of a face to a user-defined coordinate system - rectangular or cylindrical. This coordinate system affects the boundary condition and load definitions. For example, you can use it to fix the displacements in the normal direction of an inclined face. Just select the proper component of the displacement boundary condition.

## See also

- FEM_ConstraintPlaneRotation
