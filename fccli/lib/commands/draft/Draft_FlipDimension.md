---
command: "Draft_FlipDimension"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Flip Dimension"
  tooltip: "Flips the normal direction of the selected dimensions (linear, radial, angular). If other objects are selected they are ignored."
  toolbar: "Draft Modification"
  menu: "Modification"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_FlipDimension"
  wiki_rev: "0499378"
  seed: "9519365b9aee"
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

The Draft FlipDimension command rotates the dimension text of selected Draft Dimensions 180° around the dimension line. It can be used to correct dimensions whose text appears mirrored. The command does not work properly for angular dimensions.
