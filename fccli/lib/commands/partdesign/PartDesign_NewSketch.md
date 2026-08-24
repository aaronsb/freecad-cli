---
command: "PartDesign_NewSketch"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Sketch"
  tooltip: "Creates a new sketch"
  toolbar: null
  menu: "Sketch"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_NewSketch"
  wiki_rev: "0499378"
  seed: "f85dbc3d8e3a"
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

This tool creates a new sketch, creates a new PartDesign Body to contain the sketch if one does not exist and automatically opens the Sketcher workbench after creation.

When creating models using the PartDesign workbench, this tool should be preferred to the [Sketcher NewSketch tool found in the Sketcher workbench.

## See also

- Sketcher_NewSketch
