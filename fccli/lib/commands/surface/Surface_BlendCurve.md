---
command: "Surface_BlendCurve"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Blend Curve"
  tooltip: "Joins 2 edges with continuity"
  toolbar: "Surface"
  menu: "Surface"
  shortcut: null
  workbench: "SurfaceWorkbench"
  wiki: "BlendCurve"
  wiki_rev: "0499378"
  seed: "7d2b41b1803f"
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

[Surface Blend Curve

creates a Bezier curve between two edges, with desired continuity.

The base geometry can belong to curves created with the Draft Workbench or the Sketcher Workbench, but can also belong to solid objects such as those created with the Part Workbench.
