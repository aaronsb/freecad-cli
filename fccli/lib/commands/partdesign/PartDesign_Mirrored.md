---
command: "PartDesign_Mirrored"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Mirror"
  tooltip: "Mirrors the selected features or active body"
  toolbar: "Part Design Transformation Features"
  menu: "Transformation Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Mirrored"
  wiki_rev: "0499378"
  seed: "b58815397d07"
# authored from here down; the tool never rewrites these
verb: null
example: select AdditiveBox001; partdesign_mirror comboplane=Base XZ-plane
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: PartDesign::Mirrored
  doc: Mirror the selected features across a plane.
  hide: [FuzzyTolerance]
---

The PartDesign Mirrored tool mirrors one or more features.

## See also

- PartDesign_MultiTransform
