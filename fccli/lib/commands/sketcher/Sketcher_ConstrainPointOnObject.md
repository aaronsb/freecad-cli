---
command: "Sketcher_ConstrainPointOnObject"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Point-On-Object Constraint"
  tooltip: "Constrains the selected point onto the selected object"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainPointOnObject"
  wiki_rev: "0499378"
  seed: "59e38d91b099"
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

The Sketcher ConstrainPointOnObject tool fixes points on edges or axes. Lines are treated as infinite, and open curves are virtually extended as well. This tool is replaced by the Sketcher ConstrainCoincidentUnified tool if the Unify Coincident and PointOnObject option is selected in the preferences.

## See also

- Sketcher_ConstrainCoincidentUnified
- Sketcher_ConstrainCoincident
