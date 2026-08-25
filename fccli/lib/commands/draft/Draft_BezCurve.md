---
command: "Draft_BezCurve"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Bézier Curve"
  tooltip: "Creates an n-degree Bézier curve. The more points, the higher the degree."
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "B, Z"
  workbench: "DraftWorkbench"
  wiki: "Draft_BezCurve"
  wiki_rev: "0499378"
  seed: "cc6b065fcaa0"
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

The Draft BezCurve command creates a Bézier curve from several points.

The command creates a single Bézier curve with a Degree that is `number_of_points - 1`. It can be transformed into a piecewise Bézier curve by reducing this property.

The Draft BezCurve and the Draft CubicBezCurve commands use control points to define the position and curvature of the spline. The Draft BSpline command, on the other hand, specifies the exact points through which the curve will pass.

## See also

- Draft_CubicBezCurve
- Draft_BSpline
