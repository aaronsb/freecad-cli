---
command: "Draft_Dimension"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Dimension"
  tooltip: "Creates a linear dimension for a straight edge, a circular edge, or 2 picked points, or an angular dimension for 2 straight edges"
  toolbar: "Draft Annotation"
  menu: "Annotation"
  shortcut: "D, I"
  workbench: "DraftWorkbench"
  wiki: "Draft_Dimension"
  wiki_rev: "0499378"
  seed: "a4f3aa32748c"
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

The Draft Dimension command creates a linear dimension, a radial dimension or an angular dimension.

Linear dimensions based on edges and radial dimensions are parametric. This means that they will update if the measured edge is modified. Measured edges can belong to Draft objects but also to solid bodies. Angular dimensions are not parametric.

Draft Dimensions can be displayed on a TechDraw Workbench page using the TechDraw DraftView or TechDraw ArchView commands. Alternatively the TechDraw Workbench offer its own dimension commands. But these create dimensions that are only displayed on the drawing page and not in the 3D view.

## See also

- Draft_FlipDimension
