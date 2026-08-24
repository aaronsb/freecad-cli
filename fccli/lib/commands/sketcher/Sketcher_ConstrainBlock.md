---
command: "Sketcher_ConstrainBlock"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Block Constraint"
  tooltip: "Constrains the selected edges as fixed"
  toolbar: "Constraints"
  menu: "Constraints"
  shortcut: "K, B"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainBlock"
  wiki_rev: "0499378"
  seed: "9059468aae88"
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

The Sketcher ConstrainBlock tool blocks edges in place with a single constraint. It is mainly intended for B-splines, which can be difficult to fully constrain otherwise.

The block constraint only affects the freely movable parts of an edge. Blocked edges can have other constraints, and applying additional constraints to a blocked edge can modify it.

## See also

- Sketcher_ConstrainLock
