---
command: "Draft_BSpline"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "B-Spline"
  tooltip: "Creates a multiple-point B-spline"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "B, S"
  workbench: "DraftWorkbench"
  wiki: "Draft_BSpline"
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

The Draft BSpline command creates a B-spline curve from several points.

The Draft BSpline command specifies the exact points through which the curve will pass. The Draft BezCurve and the Draft CubicBezCurve commands, on the other hand, use control points to define the position and curvature of the spline.

## See also

- Draft_Wire
- Draft_CubicBezCurve
- Draft_BezCurve
