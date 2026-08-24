---
command: "Draft_Arc"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Arc"
  tooltip: "Creates a circular arc from a center point and a radius"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "A, R"
  workbench: "DraftWorkbench"
  wiki: "Draft_Arc"
  wiki_rev: "0499378"
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

The Draft Arc command creates a circular arc on the current working plane from a center, a radius, a start angle and an aperture angle. The radius and the angles can be defined by picking points.

A Draft Arc is in fact a Draft Circle with a First Angle that is not the same as its Last Angle.

## See also

- Draft_Arc_3Points
- Draft_Circle
