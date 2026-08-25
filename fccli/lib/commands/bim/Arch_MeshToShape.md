---
command: "Arch_MeshToShape"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mesh to Shape"
  tooltip: "Turns selected meshes into Part shape objects"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_MeshToShape"
  wiki_rev: "0499378"
  seed: "c655a051f224"
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

The Arch MeshToShape tool converts a selected Mesh (Mesh Feature) object into a Shape (Part Feature) object.

This tool is optimized for objects with flat faces (no curves). The corresponding tool [Part ShapeFromMesh from the Part Workbench might be more suited for objects that contain curved surfaces.

## See also

- Arch_SplitMesh
- Arch_RemoveShape
