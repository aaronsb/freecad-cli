---
command: "Part_SliceApart"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Slice Apart"
  tooltip: "Slices the selected object by other objects, and splits it apart, creating a compound filter for each slide"
  toolbar: null
  menu: "Split"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_SliceApart"
  wiki_rev: "0499378"
  seed: "c513a0532dd7"
# authored from here down; the tool never rewrites these
verb: null
example: select Box, Box001; slice_apart
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

Tool to split shapes by intersection with other shapes. For example, for a box and a plane, two solids are created.

- Above: the pieces were moved apart manually afterwards, to reveal the slicing.*

Slice apart is the same as Part Slice followed by Part Explode Compound. While "Slice to compound" is fully-parametric, and causes no trouble as the number of pieces changes, "Slice apart" will not update the number of objects as the number of pieces changes. They both create Slice parametric feature, that puts the sliced pieces into a compound, but "Slice apart" explodes the resulting compound into separate objects.

The output shape occupies the same space as the original. But it is split where it intersects with other shapes. The split pieces are individual pieces.

Please visit Part Slice page for more info.

## Tree structure of Slice Apart

The Slice Apart command creates more than only the sliced object. In the following example a cube is sliced by a face.

The slice is created and for each piece of it there is a Part CompoundFilter created, thus the same slice occurs multiple times below each CompoundFilter. All these CompoundFilters are united in a Compound.

## See also

- Part_Slice
- Part_ExplodeCompound
