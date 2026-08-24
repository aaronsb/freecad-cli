---
command: "Sketcher_ConstrainAngle"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Angle Dimension"
  tooltip: "Constrains the angle between two straight lines or between one line and the X-axis of the sketch if only one is selected"
  toolbar: null
  menu: "Constraints"
  shortcut: "K, A"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ConstrainAngle"
  wiki_rev: "0499378"
  seed: "ef66cc843360"
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

The Sketcher ConstrainAngle tool fixes the angle between two edges (lines are then treated as infinite, and open curves are virtually extended as well), the angle of a line with the horizontal axis of the sketch, or the aperture angle of a circular arc.

## See also

- Sketcher_ConstrainPerpendicular
