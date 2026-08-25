---
command: "Draft_CubicBezCurve"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cubic Bézier Curve"
  tooltip: "Creates a Bézier curve made of 2nd degree (quadratic) and 3rd degree (cubic) segments. Clicking and dragging allows to define segments. Control points and properties of each knot can be edited after creation."
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_CubicBezCurve"
  wiki_rev: "0499378"
  seed: "ddf309c22a09"
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

The Draft CubicBezCurve command creates a Bézier curve of the third degree (four points required).

The Bézier Curve is one of the most commonly used curves in computer graphics. This command allows you to create a continuous spline made up of several 3rd-degree Bézier segments, in a way that is similar to the Bézier tool in Inkscape. A general Bézier curve of any degree can be created with the Draft BezCurve command.

The Draft BezCurve and the Draft CubicBezCurve commands use control points to define the position and curvature of the spline. The Draft BSpline command, on the other hand, specifies the exact points through which the curve will pass.

## See also

- Draft_BezCurve
- Draft_BSpline
