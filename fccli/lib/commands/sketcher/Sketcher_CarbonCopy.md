---
command: "Sketcher_CarbonCopy"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Carbon Copy"
  tooltip: "Copies the geometry of another sketch"
  toolbar: "Sketcher Tools"
  menu: "Sketcher Tools"
  shortcut: "G, W"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_CarbonCopy"
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

The Sketcher CarbonCopy tool copies all geometry and constraints from another sketch into the active sketch.

Dimensional constraints which exist before the copy function remain linked to the original sketch's dimensional constraints through expressions.
