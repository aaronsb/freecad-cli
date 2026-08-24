---
command: "Surface_CurveOnMesh"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Curve on Mesh"
  tooltip: "Creates an approximated curve on top of a mesh. This command only works with a mesh object."
  toolbar: "Surface"
  menu: "Surface"
  shortcut: null
  workbench: "SurfaceWorkbench"
  wiki: "Surface_CurveOnMesh"
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

[Surface CurveOnMesh

creates approximated spline segments on top of a selected mesh.

If the object is not a Mesh, but a parametric Shape or surface, it must be converted first to a mesh using [Mesh FromPartShape.

These edges created on top of the mesh may be further used to re-create the surface in a parametric way by using tools such as [GeomFillSurface and [Sections.
