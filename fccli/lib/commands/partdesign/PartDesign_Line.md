---
command: "PartDesign_Line"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Datum Line"
  tooltip: "Creates a new datum line"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Line"
  wiki_rev: "0499378"
  seed: "50e52b70071a"
# authored from here down; the tool never rewrites these
verb: null
example: select BaseFeature.Edge1; datum_line attachmentoffsetz=5
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

Creates a datum line which can be used as reference for sketches, other datum geometry or features. For example it can be used as revolution axis for Revolution and Groove features.

## See also

- PartDesign_Point
- PartDesign_Plane
