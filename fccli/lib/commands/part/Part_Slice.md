---
command: "Part_Slice"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Slice to Compound"
  tooltip: "Slices the selected object by using other objects as cutting tools and storing the results in one compound"
  toolbar: null
  menu: "Split"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Slice"
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

The Part Slice also known as Slice to compound tool is used to split shapes by intersection with other shapes. For example, for a box and a plane, a compound of two solids is created.

There are two commands to slice a shape: Part Slice apart and Part Slice to compound. They both create a \'Slice\' parametric feature, that puts the sliced pieces into a compound. However, Part Slice Apart explodes the resulting compound into separate objects. \"Slice to compound\" is fully-parametric, and causes no trouble as the number of pieces changes. \"Slice apart\" will not update the number of objects as the number of pieces changes.

The output shape occupies the same space as the original. But it is split where it intersects with other shapes. The split pieces are put into a compound (or compsolid), so the object appears to remain in one piece. You need to explode the compound to get the individual pieces. If you want to access the individual pieces in a parametric way you can use Part Compound Filter for this purpose. For quick non-parametric access use Draft Downgrade.

The tool has three modes: \"Standard\", \"Split\", and \"CompSolid\". There is no selection form, they are predefined but can be accessed after the operation on the resulting slices level.

\"Standard\" and \"Split\" differ by the action of the tool on wires, shells and compsolids: if \"Split\", those are separated; if \"Standard\", they are kept together (get extra segments).

Compounding structure in \"Standard\" and \"Split\" modes follows the compounding structure of shape being sliced.

In \"CompSolid\" mode, the output is a compsolid (or a compound of compsolids, if the resulting solids form more than one island of connectedness). Compsolid is a set of solids connected by faces; they are related to solids like wires are related to edges, and shells are related to faces; the name is probably a shortened phrase \"composite solid\".

The overall action of the tool is very similar to Part Boolean Fragments, except only the pieces from the first shape are in the result.

## See also

- Part_BooleanFragments
- Part_XOR
- Part_CompJoinFeatures
- Part_Boolean
