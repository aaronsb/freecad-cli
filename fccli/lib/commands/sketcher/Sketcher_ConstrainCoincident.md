---
command: "Sketcher_ConstrainCoincident"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Coincident Constraint"
  tooltip: "Constrains the selected elements to be coincident"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainCoincident"
  wiki_rev: "0499378"
  seed: "7721e0b95cab"
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

The Sketcher ConstrainCoincident tool creates a coincident constraint between points, or ( ) a concentric constraint between circles, arcs and/or ellipses (by making their centers coincident). This tool is replaced by the Sketcher ConstrainCoincidentUnified tool if the Unify Coincident and PointOnObject option is selected in the preferences.

## See also

- Sketcher_ConstrainCoincidentUnified
- Sketcher_ConstrainPointOnObject
