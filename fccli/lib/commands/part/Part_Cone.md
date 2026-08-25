---
command: "Part_Cone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cone"
  tooltip: "Creates a solid cone"
  toolbar: "Solids"
  menu: "Primitives"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Cone"
  wiki_rev: "0499378"
  seed: "b00251c602fd"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type:
  of: Part::Cone
  doc: Create a truncated cone from a base radius, a top radius, and a height.
  steps: [Radius1, Radius2, Height]
  prompts:
    Radius1: radius of the bottom face
    Radius2: radius of the top face
    Height: height along the Z axis
  options: [Angle]
  strict: true
---

The Part Cone command creates a parametric cone solid. In the coordinate system defined by its Placement property, the bottom face of the cone lies on the XY plane with its center at the origin.

The default Part Cone is truncated. It can be turned into a full, untruncated, cone by changing its Radius1 or Radius2 property to zero. It can be turned into a segment of a cone by changing its Angle property.

## See also

- Part_Primitives
