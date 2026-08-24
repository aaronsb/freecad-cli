---
command: "Mesh_Difference"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Difference"
  tooltip: "Creates a boolean difference of the selected meshes"
  toolbar: "Mesh Boolean"
  menu: "Boolean"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: "Mesh_Difference"
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

The Mesh Difference command creates a new non-parametric mesh object, a Mesh Feature, that is the difference of two mesh objects: one mesh object is cut from the other.

OpenSCAD must be installed to use this command, and the path to its executable must be set in the OpenSCAD preferences.

## See also

- Mesh_Union
- Mesh_Intersection
