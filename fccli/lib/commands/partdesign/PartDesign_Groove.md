---
command: "PartDesign_Groove"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Groove"
  tooltip: "Revolves the sketch or profile around a line or axis and removes it from the body"
  toolbar: "Part Design Modeling Features"
  menu: "Subtractive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Groove"
  wiki_rev: "0499378"
  seed: "b0d8a3f4f87f"
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
  of: PartDesign::Groove
  doc: Revolve the selected profile around an axis and cut it from the body.
  steps: [Angle]
  options: [Type, Angle2]
  hide: [FuzzyTolerance, UpToFace2, UpToShape2]
---

The Groove tool revolves a selected sketch or profile about a given axis, cutting out material from the support .

## See also

- PartDesign_Revolution
