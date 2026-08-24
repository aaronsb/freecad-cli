---
command: "Mesh_Union"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Union"
  tooltip: "Unifies the selected meshes"
  toolbar: "Mesh Boolean"
  menu: "Boolean"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: "Mesh_Union"
  wiki_rev: "0499378"
  seed: "567e1095b7ba"
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

The Mesh Union command creates a new non-parametric mesh object, a Mesh Feature, that is the union (fusion) of two mesh objects.

OpenSCAD must be installed to use this command, and the path to its executable must be set in the OpenSCAD preferences.

## See also

- Mesh_Intersection
- Mesh_Difference
