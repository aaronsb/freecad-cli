---
command: "Arch_Grid"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Grid"
  tooltip: "Creates a customizable grid object"
  toolbar: "Annotation Tools"
  menu: "Annotation"
  shortcut: "A, X"
  workbench: "BIMWorkbench"
  wiki: "Arch_Grid"
  wiki_rev: "0499378"
  seed: "5e5dede7745a"
# authored from here down; the tool never rewrites these
verb: null
example: grid
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Arch Grid tool allows you to place a grid-like object in the document. This object is meant to serve as a base to build Arch objects that need a regular but complex frame, such as windows, curtain walls, column grids, railings, etc. The Grid object is editable like a spreadsheet, where you can add or remove columns and rows, define their size, and merge cells.

The Grid is a 2D object, and can therefore be used anywhere a 2D shape such as a Draft or Sketch is needed, but it can also behave as a Arch AxisSystem, and be used to propagate the placement of other Arch objects.

## See also

- Arch_Axis
- Arch_AxisSystem
