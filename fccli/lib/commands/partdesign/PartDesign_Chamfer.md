---
command: "PartDesign_Chamfer"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Chamfer"
  tooltip: "Applies a chamfer to the selected edges or faces"
  toolbar: "Part Design Dress-Up Features"
  menu: "Dress-Up Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Chamfer"
  wiki_rev: "0499378"
  seed: "c21d6020176d"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: PartDesign::Chamfer
  doc: Bevel the selected edges or faces.
  steps: [Size]
  options: [ChamferType, Size2, Angle]
  hide: [FuzzyTolerance]
---

The PartDesign Chamfer tool creates chamfers on the selected edges of an object. It adds a Chamfer object to the document with its corresponding representation in the Tree view.

## See also

- PartDesign_Fillet
