---
command: "Draft_Wire"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Polyline"
  tooltip: "Creates a polyline"
  toolbar: "Drafting Tools"
  menu: "2D Drafting"
  shortcut: "P, L"
  workbench: "DraftWorkbench"
  wiki: "Draft_Wire"
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

The Draft Wire command creates a polyline, a sequence of several connected line segments. The command can also be used to join Draft Lines and Draft Wires.

The corners of a Draft Wire can be filleted (rounded) or chamfered by changing its Fillet Radius or Chamfer Size respectively. It is also possible to subdivide the edges of a Draft Wire by changing its Subdivisions property.

## See also

- Draft_Line
- Draft_BSpline
