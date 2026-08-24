---
command: "FEM_MeshRegion"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh Refinement"
  tooltip: "Creates a FEM mesh refinement"
  toolbar: "Mesh"
  menu: "Mesh"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshRegion"
  wiki_rev: "0499378"
  seed: "14a9b46aada7"
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

Enables the user to set a localized set of meshing parameters by selecting a set of elements (vertex, edge, face) and applying the parameters to it. It is especially useful for refining meshes in areas of interest or areas where the solver will generate a stronger gradient of a variable. For example, it can be used to refine the mesh around stress-risers (sharp edges, holes, notches, ...) in mechanical analysis, or at areas of contraction in a fluid flow.

Refining the mesh has the advantage of enabling accurate simulation where needed, while allowing coarser mesh in the wider domain, thus drastically optimizing the computation time while maintaining meaningful solutions output.

## See also

- FEM_tutorial
