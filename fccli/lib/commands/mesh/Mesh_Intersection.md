---
command: "Mesh_Intersection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Intersection"
  tooltip: "Creates a boolean intersection from the selected meshes"
  toolbar: "Mesh Boolean"
  menu: "Boolean"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: "Mesh_Intersection"
  wiki_rev: "0499378"
  seed: "36ebe84d3b1f"
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

The Mesh Intersection command creates a new non-parametric mesh object, a Mesh Feature, that is the intersection (common) of two mesh objects.

OpenSCAD must be installed to use this command, and the path to its executable must be set in the OpenSCAD preferences.

## See also

- Mesh_Union
- Mesh_Difference
