---
command: "Sketcher_Split"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Split Edge"
  tooltip: "Splits an edge into 2 segments while preserving constraints"
  toolbar: null
  menu: "Sketcher Tools"
  shortcut: "G, Z"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_Split"
  wiki_rev: "0499378"
  seed: "8788a646b8f3"
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

The Sketcher Split tool splits an edge. If the edge is a closed curve (i.e. a circle, an ellipse or a periodic B-spline) it is converted to an open curve (an arc, an arc of ellipse or a non-periodic B-spline respectively).

## See also

- Sketcher_Trimming
