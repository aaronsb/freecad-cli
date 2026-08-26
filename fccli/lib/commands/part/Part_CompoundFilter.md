---
command: "Part_CompoundFilter"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Compound Filter"
  tooltip: "Filters out objects from the selected compound by characteristics like volume, area, or length, or by choosing specific items. If a second object is selected, it will be used as reference, for example, for collision or distance filtering."
  toolbar: null
  menu: "Compound"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_CompoundFilter"
  wiki_rev: "0499378"
  seed: "cba9f9a35f0b"
# authored from here down; the tool never rewrites these
verb: null
example: select Compound; compound_filter
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The CompoundFilter can be used to extract the individual pieces of the result of e.g. a Part Slice operation, with which you have split an object.

It can extract children by their indexes, test children for collisions with stencil shape, and filter children based on their properties, such as length, area, volume.

If there is only one child in the result, the output is the child. If there is more than one child to output, the output is a new compound.
