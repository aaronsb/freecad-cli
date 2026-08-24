---
command: "Draft_Polygon"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Polygon"
  tooltip: "Creates a regular polygon (triangle, square, pentagon…)"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "P, G"
  workbench: "DraftWorkbench"
  wiki: "Draft_Polygon"
  wiki_rev: "0499378"
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

The Draft Polygon command creates a regular polygon on the current working plane from a center and a radius. The radius can be defined by picking a point.

A Draft Polygon can be switched from inscribed to circumscribed by changing its Draw Mode property. The corners of a Draft Polygon can be filleted (rounded) or chamfered by changing its Fillet Radius or Chamfer Size respectively.
