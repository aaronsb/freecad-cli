---
command: "PartDesign_MultiTransform"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Multi-Transform"
  tooltip: "Applies multiple transformations to the selected features or active body"
  toolbar: "Part Design Transformation Features"
  menu: "Transformation Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_MultiTransform"
  wiki_rev: "0499378"
  seed: "769608653df5"
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

The PartDesign MultiTransform tool creates a pattern of one or more features. The pattern can include multiple transformations where each subsequent transformation is applied to the result of the previous transformation.

The available transformations are: Mirrored, LinearPattern, PolarPattern and Scaled. The first three are also available as separate tools.

## See also

- PartDesign_Mirrored
- PartDesign_LinearPattern
- PartDesign_PolarPattern
- PartDesign_Scaled
