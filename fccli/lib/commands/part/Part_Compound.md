---
command: "Part_Compound"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Compound"
  tooltip: "Compounds the selected shapes"
  toolbar: null
  menu: "Compound"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Compound"
  wiki_rev: "0499378"
  seed: "b5fae704b511"
# authored from here down; the tool never rewrites these
verb: null
example: select Box, Box001; compound
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

This command creates a compound of objects with a topological shape such as solid objects and other objects with faces and/or edges. It cannot handle meshes as they do not have a topological shape.

## See also

- Part_Fuse
- Part_CompoundFilter
- Part_ExplodeCompound
