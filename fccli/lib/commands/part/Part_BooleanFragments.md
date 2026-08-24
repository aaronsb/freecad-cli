---
command: "Part_BooleanFragments"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Boolean Fragments"
  tooltip: "Creates a boolean union which is sliced at the intersections of the selected shapes"
  toolbar: null
  menu: "Split"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_BooleanFragments"
  wiki_rev: "0499378"
  seed: "95d5e24b87f8"
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

The Part BooleanFragments tool computes all fragments that can result from applying Boolean operations between input shapes. For example, for two intersecting spheres, three non-overlapping but touching solids are generated.

The output shape is always a compound. The content of the compound depends on input shape types and operation mode. That means, you don't immediately get access to individual pieces of the result - the pieces remain grouped together. The individual pieces can be extracted by exploding the compound (Draft Downgrade).

The tool has three modes: "Standard", "Split", and "CompSolid".

"Standard" and "Split" differ by the action of the tool on wires, shells and compsolids. If "Split", those are separated. If "Standard", they are kept together (get extra segments).

Compounding structure in "Standard" and "Split" modes follows the compounding structure of inputs. That is, if you feed in two compounds, each containing a sphere like on example above, the result will also contain two compounds, each containing the pieces of the originally contained sphere. That means, the common piece will be repeated twice in the result. Only if the input spheres are both not in compounds, the result will contain the common piece once.

In "CompSolid" mode, the solids are joined into a compsolid (compsolid is a set of solids connected by faces; they are related to solids like wires are related to edges, and shells are related to faces; the name is probably a shortened phrase "composite solid"). The output is a non-nested compound of compsolids.

## See also

- Part_Slice
- Part_XOR
- Part_CompJoinFeatures
- Part_Boolean
