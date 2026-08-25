---
command: "Part_XOR"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Boolean XOR"
  tooltip: "Performs an 'exclusive OR' boolean operation with two or more selected objects, or with the shapes inside a compound. Overlapping volumes of the shapes will be removed."
  toolbar: null
  menu: "Split"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_XOR"
  wiki_rev: "0499378"
  seed: "d5392035df03"
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

The Part XOR command removes geometry shared by an even number of objects and leaves a void space between the involved objects. For two objects it represents a symmetric version of Part Cut.

## See also

- Part_BooleanFragments
- Part_Slice
- Part_CompJoinFeatures
- Part_Boolean
