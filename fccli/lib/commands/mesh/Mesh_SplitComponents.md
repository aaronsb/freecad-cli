---
command: "Mesh_SplitComponents"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Split by Components"
  tooltip: "Splits the selected mesh into its components"
  toolbar: "Mesh Segmentation"
  menu: "Meshes"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: "Mesh_SplitComponents"
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

The Mesh SplitComponents command splits a mesh object into its components. A mesh component is a complete group of connected faces. For each component a new non-parametric mesh object, a Mesh Feature, is created. If the original mesh object contains only one component, and this is usually the case, a single new mesh object, effectively a copy, is created. This command is the counterpart of the Mesh Merge command.

## See also

- Mesh_Merge
