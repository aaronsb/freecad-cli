---
command: "Sketcher_RemoveAxesAlignment"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Remove Axes Alignment"
  tooltip: "Modifies the constraints to remove axes alignment while trying to preserve the constraint relationship of the selection"
  toolbar: "Sketcher Tools"
  menu: "Sketcher Tools"
  shortcut: "Z, R"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_RemoveAxesAlignment"
  wiki_rev: "0499378"
  seed: "d9ef7a6b9394"
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

The Sketcher RemoveAxesAlignment tool removes the axes alignment of selected edges by replacing Horizontal and Vertical constraints with Parallel and Perpendicular constraints. The edges can then be rotated without losing their orthogonal relationship.
