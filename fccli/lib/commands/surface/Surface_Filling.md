---
command: "Surface_Filling"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Filling"
  tooltip: "Creates a surface from a series of selected boundary edges. Additionally, the surface may be constrained by edges and vertices that are not on the boundary."
  toolbar: "Surface"
  menu: "Surface"
  shortcut: null
  workbench: "SurfaceWorkbench"
  wiki: "Surface_Filling"
  wiki_rev: "0499378"
  seed: "94e00da96418"
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

[Surface Filling

creates a surface from a series of connected boundary edges. The curvature of the surface can be additionally controlled by non-boundary edges and vertices, and a support surface.

The base geometry can belong to curves created with the Draft Workbench or the Sketcher Workbench, but can also belong to solid objects such as those created with the Part Workbench or the PartDesign Workbench.
