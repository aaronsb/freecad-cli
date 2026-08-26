---
command: "Arch_Axis"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Axis"
  tooltip: "Creates a set of axes"
  toolbar: "Annotation Tools"
  menu: "Annotation"
  shortcut: "A, X"
  workbench: "BIMWorkbench"
  wiki: "Arch_Axis"
  wiki_rev: "0499378"
  seed: "58d44a7c8f63"
# authored from here down; the tool never rewrites these
verb: null
example: axis
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Arch Axis tool allows you to place a series of axes in the current document. The distance and the angle between axes is customizable, as well as the numbering style. The axes serve mainly as references to snap objects onto, but can also be used together with Arch AxisSystems. They can also be referenced by other Arch objects to create parametric arrays, for example of beams or columns. Arch Grids can also be used in places of axes.

## See also

- Arch_AxisSystem
- Arch_Grid
