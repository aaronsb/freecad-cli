---
command: "CAM_Pocket3D"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "3D Pocket"
  tooltip: "Creates a 3D Pocket toolpath from a face or faces"
  toolbar: "New Operations"
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Pocket3D"
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

This command inserts a path 3D Pocket object into the Job. This operation takes into account the bottom surface of the pocket, as well as selected walls that are not vertical. In its current state, this operation is used to rough out a pocket with non-vertical walls and/or non-horizontal bottom. A common finishing technique is to use a ball end mill with the experimental 3D Surface operation.
