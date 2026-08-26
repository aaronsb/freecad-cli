---
command: "PartDesign_LinearPattern"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Linear Pattern"
  tooltip: "Duplicates the selected features or the active body in a linear pattern"
  toolbar: "Part Design Transformation Features"
  menu: "Transformation Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_LinearPattern"
  wiki_rev: "0499378"
  seed: "ca104214e572"
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
  of: PartDesign::LinearPattern
  doc: Repeat the selected features along a direction.
  steps: [Length, Occurrences]
  options: [Mode, Offset]
  hide: [FuzzyTolerance, Direction2, Length2, Mode2, Occurrences2, Offset2,
         SpacingPattern, SpacingPattern2, Spacings, Spacings2]
---

The PartDesign LinearPattern tool creates a linear pattern of one or more features.

## See also

- PartDesign_MultiTransform
