---
command: "Sketcher_ConstrainEqual"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Equal Constraint"
  tooltip: "Constrains the selected edges or circles to be equal"
  toolbar: "Constraints"
  menu: "Constraints"
  shortcut: "E"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainEqual"
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

The Sketcher ConstrainEqual tool constrains edges to have an equal length (lines) or curvature (other edges except B-splines). Selected edges must have the same type. Circles and circular arcs are of the same type (their radii are made equal), and so are ellipses and elliptical arcs (their major and minor radii are made equal).
