---
command: "OpenSCAD_Minkowski"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Minkowski Sum"
  tooltip: "Creates a Minkowski sum"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "OpenSCADWorkbench"
  wiki: "OpenSCAD_Minkowski"
  wiki_rev: "0499378"
  seed: "851f8787eb66"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

Applies a Minkowski sum to selected shapes.

## Mathematical Definition

Add each element of subset A to each element of subset B to get Minkowski sum.

## Geometrical Definition

Sweep element A along all boundaries of element B. Resulting space which is occupied by both elements is Minkowski sum.

Example of Minkowski sum applied to cylinder and cube. Note: that the height of Minkowski sum is height of cylinder plus height of cube.
