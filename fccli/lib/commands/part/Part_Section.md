---
command: "Part_Section"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Section"
  tooltip: "Sections 2 selected shapes"
  toolbar: "Part Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Section"
  wiki_rev: "0499378"
  seed: "6661737cfab2"
# authored from here down; the tool never rewrites these
verb: null
example: select Box, Box001; section
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part Section command creates wire geometry at the intersections of two objects. The result is fully parametric.

- An intersection of two solids/faces results in one or more section lines.
- An intersection of two lines, or a line and a solid/face, results in one or more points.

## See also

- Part_CrossSections
