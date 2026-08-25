---
command: "Draft_Shape2DView"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Shape 2D View"
  tooltip: "Creates a 2D projection of the selected objects on the XY-plane. The initial projection direction is the opposite of the current active view direction."
  toolbar: "Draft Modification"
  menu: "Modification"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Shape2DView"
  wiki_rev: "0499378"
  seed: "af6fe005c17a"
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

The Draft Shape2DView command creates 2D projections from selected objects, usually 3D solids or Arch SectionPlanes. The projections are placed in the 3D view.

Draft Shape2DView projections can be displayed on a TechDraw Workbench page using the TechDraw DraftView command. Alternatively the TechDraw Workbench offer its own projection commands. But these create projections that are only displayed on the drawing page and not in the 3D view.

## See also

- TechDraw_ProjectShape
