---
command: "Sketcher_ValidateSketch"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Validate Sketch"
  tooltip: "Validates a sketch by checking for missing coincidences, invalid constraints, and degenerate geometry"
  toolbar: "Part Design Helper Features"
  menu: "Sketch"
  shortcut: null
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ValidateSketch"
  wiki_rev: "0499378"
  seed: "0d65af4023ff"
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

The Sketcher ValidateSketch tool can analyze and repair a sketch that is no longer editable or has invalid constraints, or add missing coincident constraints to a sketch created from imported geometry such as DXF files. It can also be useful to locate a missing coincidence in a native sketch that generates an error when trying to apply a PartDesign feature.

## See also

- Sketcher_ConstrainCoincident
