---
command: "Sketcher_MapSketch"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Attach Sketch"
  tooltip: "Attaches a sketch to the selected geometry element"
  toolbar: "Sketcher"
  menu: "Sketch"
  shortcut: null
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_MapSketch"
  wiki_rev: "0499378"
  seed: "cd1de862c6c1"
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

The Sketcher MapSketch tool attaches a sketch to selected geometry.

Typical use cases are:

- The sketch was created on a standard plane (XY, XZ or YZ) and you want to attach it to the face of a solid in order to build a new feature upon it.
- The sketch was attached to a specific face of a solid but you need to attached it to a different face.
- A broken model needs to be repaired.

## See also

- Sketcher_ReorientSketch
- Sketcher_NewSketch
