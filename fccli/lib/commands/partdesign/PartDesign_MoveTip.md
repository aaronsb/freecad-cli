---
command: "PartDesign_MoveTip"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Set Tip"
  tooltip: "Moves the tip of the body to the selected feature"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_MoveTip"
  wiki_rev: "0499378"
  seed: "3ab95da585cf"
# authored from here down; the tool never rewrites these
verb: null
example: select BaseFeature; set_tip
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

Set tip, as this command is labeled in the context menu, redefines the tip, which is the feature exposed outside of the Body. By default, the tip is the last feature added to the Body; but sometimes it can be useful to temporarily set the tip to a feature earlier in the tree. This may be done to add a sketch, datum geometry or a feature which in retrospect should have been created earlier in the Body's history.

The tip is visually distinguished in the Model tree by a small white down arrow in a green circle overlayed on the feature's icon. For example, the following feature is the tip:

## See also

- PartDesign_MoveFeature
- PartDesign_MoveFeatureInTree
