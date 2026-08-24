---
command: "Draft_Fillet"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Fillet"
  tooltip: "Creates a fillet between 2 selected edges"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "F, I"
  workbench: "DraftWorkbench"
  wiki: "Draft_Fillet"
  wiki_rev: "0499378"
  seed: "311c061b39ad"
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

The Draft Fillet command creates a fillet, a rounded corner, or a chamfer, a straight edge, between two selected edges.

In the command only works properly if both selected edges are straight.

In if the selected objects have multiple edges, their first edge will be used. This may not be the edge that was picked in the 3D view.

## See also

- Draft_Line
- Draft_Wire
