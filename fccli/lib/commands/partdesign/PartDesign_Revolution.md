---
command: "PartDesign_Revolution"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Revolve"
  tooltip: "Revolves the selected sketch or profile around a line or axis and adds it to the body"
  toolbar: "Part Design Modeling Features"
  menu: "Additive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Revolution"
  wiki_rev: "0499378"
  seed: "d8502bb433c2"
# authored from here down; the tool never rewrites these
verb: null
example: select Sketch001; revolve revolveangle=270
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: PartDesign::Revolution
  doc: Revolve the selected profile around an axis and add it to the body.
  steps: [Angle]
  options: [Type, Angle2]
  hide: [FuzzyTolerance, UpToFace2, UpToShape2]
---

The Revolution tool creates a solid by revolving a selected sketch or 2D object about a given axis.

## See also

- PartDesign_Groove
