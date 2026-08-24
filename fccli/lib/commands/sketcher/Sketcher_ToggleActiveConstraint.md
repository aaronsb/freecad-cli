---
command: "Sketcher_ToggleActiveConstraint"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Constraints"
  tooltip: "Toggles the state of the selected constraints"
  toolbar: null
  menu: "Constraints"
  shortcut: "K, Z"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ToggleActiveConstraint"
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

The Sketcher ToggleActiveConstraint tool activates or deactivates selected constraints. Deactivating constraints allows you to test other geometry arrangements without deleting constraints.

This is tool is similar to Sketcher ToggleDrivingConstraint, but contrary to that tool also works for geometric constraints, and values of deactivated dimensional constraints are preserved.

## See also

- Sketcher_ToggleDrivingConstraint
