---
command: "PartDesign_Pocket"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Pocket"
  tooltip: "Extrudes the selected sketch or profile and removes it from the body"
  toolbar: "Part Design Modeling Features"
  menu: "Subtractive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Pocket"
  wiki_rev: "0499378"
  seed: "2604465378cc"
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
  of: PartDesign::Pocket
  doc: Extrude the selected profile and cut it out of the body.
  steps: [Length]
  options: [Type, SideType, Length2, TaperAngle]
  hide: [FuzzyTolerance, Direction, Offset2, TaperAngle2, Type2,
         UpToFace2, UpToShape2]
---

The Pocket tool cuts solids by extruding a sketch or a face of a solid along a straight path.

## See also

- PartDesign_Pad
