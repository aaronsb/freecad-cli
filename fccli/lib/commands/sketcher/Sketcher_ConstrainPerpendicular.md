---
command: "Sketcher_ConstrainPerpendicular"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Perpendicular Constraint"
  tooltip: "Constrains the selected lines to be perpendicular"
  toolbar: "Constraints"
  menu: "Constraints"
  shortcut: "N"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainPerpendicular"
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

The Sketcher ConstrainPerpendicular tool constrains two lines to be perpendicular, or two edges, or an edge and an axis, to be perpendicular at their intersection. Lines are treated as infinite, and open curves are virtually extended as well. The constraint can also connect two edges, forcing them to be perpendicular at the joint.

## See also

- Sketcher_ConstrainAngle
