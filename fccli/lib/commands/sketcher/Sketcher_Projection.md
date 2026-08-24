---
command: "Sketcher_Projection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "External Projection"
  tooltip: "Creates the projection of external geometry in the sketch plane"
  toolbar: null
  menu: "Sketcher Tools"
  shortcut: "G, X"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_Projection"
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

The Sketcher Projection tool projects edges and/or vertices belonging to objects outside the sketch onto the sketch plane. The projected geometry is called \"external geometry\". It stays parametrically linked to its source objects. External geometry is marked with a dedicated color (default magenta) and linetype. It can be defining geometry that is visible outside the sketch or construction geometry that is not visible outside the sketch.

## See also

- Sketcher_ToggleConstruction
