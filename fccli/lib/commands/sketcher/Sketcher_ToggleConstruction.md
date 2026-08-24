---
command: "Sketcher_ToggleConstruction"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Construction Geometry"
  tooltip: "Toggles between defining geometry and construction geometry modes"
  toolbar: "Geometries"
  menu: "Geometries"
  shortcut: "G, N"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ToggleConstruction"
  wiki_rev: "0499378"
  seed: "5cdd6b27b662"
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

The Sketcher ToggleConstruction tool either toggles the geometry creation tools to/from construction mode, or toggles selected geometry to/from construction geometry.

Construction geometry is marked with a dedicated color (default blue) and ( ) linetype. Construction geometry is not visible outside the sketch, it is intended to help define constraints and other geometry inside the sketch itself. Construction lines can however be used as a rotation axis by PartDesign Revolution.
