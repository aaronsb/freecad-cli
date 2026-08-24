---
command: "Sketcher_ConstrainCoincidentUnified"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Coincident Constraint"
  tooltip: "Constrains the selected elements to be coincident"
  toolbar: "Constraints"
  menu: "Constraints"
  shortcut: "C"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainCoincidentUnified"
  wiki_rev: "0499378"
  seed: "58b29eba7eac"
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

The Sketcher ConstrainCoincidentUnified tool creates a coincident constraint between points, fixes points on edges or axes (lines are then treated as infinite, and open curves are virtually extended as well), or creates a concentric constraint between circles, arcs and/or ellipses (by making their centers coincident).

This tool replaces the Sketcher ConstrainCoincident and Sketcher ConstrainPointOnObject tools if the Unify Coincident and PointOnObject option is selected in the preferences.

## See also

- Sketcher_ConstrainCoincident
- Sketcher_ConstrainPointOnObject
