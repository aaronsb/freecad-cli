---
command: "Sketcher_CreateFillet"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Fillet"
  tooltip: "Creates a fillet between 2 selected lines or at coincident points"
  toolbar: null
  menu: "Sketcher Tools"
  shortcut: "G, F, F"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_CreateFillet"
  wiki_rev: "0499378"
  seed: "0563b73b910d"
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

The Sketcher CreateFillet tool creates a fillet between two non-parallel edges. The tool can also create a chamfer. If two straight edges connected by a Coincident constraint are filleted or chamfered, the corner point can optionally be preserved. The tool then adds a Point object that has a Point on object constraint with both edges. Constraints connected to the corner point are transferred to the new point object.
