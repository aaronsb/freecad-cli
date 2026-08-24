---
command: "FEM_MeshNetgenFromShape"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh From Shape by Netgen"
  tooltip: "Creates a FEM mesh from a solid or face shape by Netgen internal mesher"
  toolbar: "Mesh"
  menu: "Mesh"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshNetgenFromShape"
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

For a finite element analysis, the geometry needs to be discretized into a FEM Mesh. This command uses Netgen (which needs to be installed on the system) to generate the mesh. Netgen meshes are not supported by Elmer.

Depending on your operating system and installation package, Netgen might be bundled with FreeCAD or not. For further information see FEM Install.

## See also

- FEM_tutorial
