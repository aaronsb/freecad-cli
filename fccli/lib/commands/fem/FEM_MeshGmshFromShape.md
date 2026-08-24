---
command: "FEM_MeshGmshFromShape"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh From Shape by Gmsh"
  tooltip: "Creates a FEM mesh from a shape by Gmsh mesher"
  toolbar: "Mesh"
  menu: "Mesh"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshGmshFromShape"
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

For a finite elements analysis the geometry needs to be discretized into a FEM Mesh. This command uses the software Gmsh (which needs to be installed on the system) to generate the mesh.

Depending on your operating system and your installation package, Gmsh might be bundled with FreeCAD or not. For further information see FEM Install.

## See also

- FEM_tutorial
