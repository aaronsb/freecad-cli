---
command: "FEM_MeshClear"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clear FEM Mesh"
  tooltip: "Clears the mesh of a FEM mesh object"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshClear"
  wiki_rev: "0499378"
  seed: "112d831d8365"
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

Enables the user to reinitialize the mesh from the FreeCAD FEM mesh object. The mesh still exists but does not have any vertices, edges, faces or elements. The meshing information, Netgen/Gmsh parameters, mesh regions, mesh groups and mesh boundary layer remain in the Model Tree, which means the mesh can be reproduced later. The main use of this function is to lighten the FreeCAD file, either to improve performance when using FreeCAD, to save disk space or enable easy transfer of files without losing meshing data.

## See also

- FEM_tutorial
