---
command: "Sketcher_ConstrainTangent"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Tangent/Collinear Constraint"
  tooltip: "Constrains the selected elements to be tangent or collinear"
  toolbar: "Constraints"
  menu: "Constraints"
  shortcut: "T"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainTangent"
  wiki_rev: "0499378"
  seed: "c93b540ced81"
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

The Sketcher ConstrainTangent tool constrains two edges, or an edge and an axis, to be tangent. Lines are treated as infinite, and open curves are virtually extended as well. The constraint can also connect two edges, forcing them to be tangent at the joint. If two lines are selected, or a line and the endpoint of another line, the lines are made collinear.
