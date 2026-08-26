---
command: "Part_Offset2D"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "2D Offset"
  tooltip: "Offsets planar shapes in 2D"
  toolbar: null
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Offset2D"
  wiki_rev: "0499378"
  seed: "cfd5efbdf5a0"
# authored from here down; the tool never rewrites these
verb: null
example: select Wire; part_2d_offset offset=2
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part Offset2D tool constructs a wire, parallel to the original wire, at a certain distance from it. Or enlarges/shrinks a planar face, similarly.

The wire/face must be planar. There can be multiple wires in one object, not necessarily coplanar.

## See also

- Part_Offset
- Part_Thickness
- Draft_Offset
