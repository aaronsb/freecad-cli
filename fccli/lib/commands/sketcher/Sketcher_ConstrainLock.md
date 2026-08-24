---
command: "Sketcher_ConstrainLock"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Lock Position"
  tooltip: "Constrains the selected vertices by adding horizontal and vertical distance constraints"
  toolbar: null
  menu: "Constraints"
  shortcut: "K, L"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainLock"
  wiki_rev: "0499378"
  seed: "d01b3cd78600"
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

The Sketcher ConstrainLock tool applies Horizontal distance and Vertical distance constraints to points. If a single point is selected the constraints reference the origin of the sketch. If two or more points are selected the constraints reference the last point in the selection.

## See also

- Sketcher_ConstrainBlock
