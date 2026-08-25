---
command: "Draft_Arc_3Points"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Arc From 3 Points"
  tooltip: "Creates a circular arc from 3 points"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "A, T"
  workbench: "DraftWorkbench"
  wiki: "Draft_Arc_3Points"
  wiki_rev: "0499378"
  seed: "127f064e79ef"
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

The Draft Arc 3Points command creates a circular arc on the current working plane from three points that define its circumference. The center and radius are calculated from these points.

A Draft Arc is in fact a Draft Circle with a First Angle that is not the same as its Last Angle.

## See also

- Draft_Arc
- Draft_Circle
