---
command: "Sketcher_Intersection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "External Intersection"
  tooltip: "Creates the intersection of external geometry with the sketch plane"
  toolbar: null
  menu: "Sketcher Tools"
  shortcut: "G, I"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_Intersection"
  wiki_rev: "0499378"
  seed: "fe9ddef11fbd"
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

The Sketcher Intersection tool intersects faces and/or edges belonging to objects outside the sketch with the sketch plane. The intersected geometry is called "external geometry". It stays parametrically linked to its source objects. External geometry is marked with a dedicated color (default magenta) and linetype. It can be defining geometry that is visible outside the sketch or construction geometry that is not visible outside the sketch.

## See also

- Sketcher_ToggleConstruction
