---
command: "Sketcher_ViewSketch"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Align View to Sketch"
  tooltip: "Aligns the camera orientation perpendicular to the active sketch plane"
  toolbar: "Edit Mode"
  menu: "Sketch"
  shortcut: "Q, P"
  workbench: "SketcherWorkbench"
  wiki: "Sketcher_ViewSketch"
  wiki_rev: "0499378"
  seed: "d7683aa14c81"
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

The Sketcher ViewSketch tool aligns the 3D view with the sketch. The view is rotated so that the view direction is perpendicular to the sketch plane, and the X axis of the sketch appears horizontal. It is useful if you have changed the view orientation to examine another aspect of the model and want to return to the default sketch view.
