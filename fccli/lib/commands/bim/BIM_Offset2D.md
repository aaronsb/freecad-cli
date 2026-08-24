---
command: "BIM_Offset2D"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "2D Offset"
  tooltip: "Utility to offset planar shapes"
  toolbar: "2D Tools"
  menu: "Modify"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Offset2D"
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

The Part Offset2D tool constructs a wire, parallel to the original wire, at a certain distance from it. Or enlarges/shrinks a planar face, similarly.

The wire/face must be planar. There can be multiple wires in one object, not necessarily coplanar.

## See also

- Part_Offset
- Part_Thickness
- Draft_Offset
