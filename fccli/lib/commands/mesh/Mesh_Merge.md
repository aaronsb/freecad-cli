---
command: "Mesh_Merge"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Merge"
  tooltip: "Merges selected meshes into one"
  toolbar: "Mesh Segmentation"
  menu: "Meshes"
  shortcut: null
  workbench: "MeshWorkbench"
  wiki: "Mesh_Merge"
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

The Mesh Merge command creates a new non-parametric mesh object, a Mesh Feature, by combining the meshes of two or more mesh objects. The command does not perform a Boolean union, the new object will contain separate mesh components. For a Boolean union use the Mesh Union command instead. This command is the counterpart of the Mesh SplitComponents command.

## See also

- Mesh_SplitComponents
