---
command: "FEM_ClippingPlaneAdd"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clipping Plane on Face"
  tooltip: "Adds a clipping plane on a selected face"
  toolbar: "Utilities"
  menu: "Utilities"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_ClippingPlaneAdd"
  wiki_rev: "0499378"
  seed: "8af9e011c383"
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

Adds a clipping plane for the whole model view. All visible objects will be cut by it, no matter if these are geometric models, meshes or result pipelines.

The clipping plane is the same you get when using the feature Toggle Clip Plane with the difference that the clipping plane is persistent. Therefore it shares the same functionality of providing only hollow cuts.

## See also

- FEM_tutorial
