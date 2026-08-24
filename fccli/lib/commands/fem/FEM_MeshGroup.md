---
command: "FEM_MeshGroup"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh Group"
  tooltip: "Creates a mesh group"
  toolbar: "Mesh"
  menu: "Mesh"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_MeshGroup"
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

The FEM MeshGroup command enables the user to create groups of Vertices, Edges, Surfaces and elements. It is useful in case of using FreeCAD as a pre-processor to export an organized and labeled mesh. The mesh is then usable by external solver codes, where mesh groups can be used more readily to set boundary conditions and attribute solver related properties. It is possible to use the FreeCAD mesh group object name or the label as the group name on export of the mesh. If the label is chosen, the user has to be mindful if special characters are used. If the mesh export format does not allow special character its fallback is to use the mesh group object name.

FEM MeshGroup therefore enables FreeCAD to be used with external solvers (or viewers such as ParaView) when they are not yet implemented with their own case-writing routine within FreeCAD.
