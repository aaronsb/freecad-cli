---
command: "Sketcher_Clone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clone"
  tooltip: "Creates a clone of the geometry taking as reference the last selected point"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_Clone"
  wiki_rev: "0499378"
  seed: "e259ee290382"
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

The Sketcher Clone command clones the selected sketch elements from one point to another, using the last selected point as reference. If any constraints are part of the source elements, then the new constraints are linked to the source constraints; if the constraints in the source are changed, the constraints in the clone are also changed. To avoid this linking see [Sketcher Copy.

Note that a clone of a clone becomes a Sketcher Copy. If you wish to create linked constraints, clone the original source elements again.

## See also

- Sketcher_Copy
- Sketcher_Move
