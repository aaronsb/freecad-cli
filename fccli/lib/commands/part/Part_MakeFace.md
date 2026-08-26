---
command: "Part_MakeFace"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Face From Wires"
  tooltip: "Creates a face from the selected wires (e.g. from a sketch)"
  toolbar: "Part Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_MakeFace"
  wiki_rev: "0499378"
  seed: "048cc08f9164"
# authored from here down; the tool never rewrites these
verb: null
example: select Wire; face_from_wires
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part MakeFace command creates a planar face from one or more coplanar closed wires (contours). They can be any valid wire, i.e. created with the Part Workbench, the Draft Workbench or the Sketcher Workbench. The contours should not self-intersect, or intersect each other. They can be nested to create voids.

## See also

- Part_RuledSurface
