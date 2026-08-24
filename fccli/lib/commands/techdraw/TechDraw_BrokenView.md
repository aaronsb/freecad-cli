---
command: "TechDraw_BrokenView"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Broken View"
  tooltip: "Inserts a new broken view for the selected objects or base view and break definition objects"
  toolbar: "TechDraw Views"
  menu: "TechDraw Views"
  shortcut: null
  workbench: "TechDrawWorkbench"
  wiki: "TechDraw_BrokenView"
  wiki_rev: "0499378"
  seed: "8c490e578114"
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

The TechDraw BrokenView tool inserts a "broken view" that is either based on an existing part view, or one or more objects, such as Bodies or Parts. The broken view also requires one or more sketches that define the location and size of the areas to be removed. The BrokenView behaves similarly to other Views. The projection direction is taken from the existing part view, the 3D camera direction or the normal of a selected face.

## See also

- TechDraw_View
