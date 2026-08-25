---
command: "Part_ExplodeCompound"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Explode Compound"
  tooltip: "Splits up a compound of shapes into separate objects, creating a compound filter for each shape"
  toolbar: null
  menu: "Compound"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_ExplodeCompound"
  wiki_rev: "0499378"
  seed: "4d9980b9b7d0"
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

The Part ExplodeCompound tool splits a compound of shapes, to make each contained shape (child) available as a separate object. The children are automatically put into a Group if there is more than one child.

It is semi-parametric: the shapes of the children will update as the source compound changes, but if the number of children in the compound is changed, the explosion will be either missing some shapes, or have redundant objects in an error state.

Placements of extracted shapes follow the placements of the originals, plus the Placement property of each child.

The tool will also explode non-compound shapes into their lower-level constituents: compsolids into solids, solids into shells, shells into faces, faces into wires, wires into edges, edges into vertices.

## See also

- Part_Compound
- Draft_Downgrade
