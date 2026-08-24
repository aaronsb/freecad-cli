---
command: "Part_ProjectionOnSurface"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Project on Surface"
  tooltip: "Projects edges, wires, or faces of one shape onto a face of another shape. The camera view determines the direction of the projection."
  toolbar: "Part Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_ProjectionOnSurface"
  wiki_rev: "0499378"
  seed: "65cc2369cce0"
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

[Part ProjectionOnSurface

is used to project a Shape on top of a face from another object; this can be used to project a logo or textual object (see [Draft ShapeString) onto different surfaces to create interesting effects.

Given a source Shape, this tool can project edges, wires (closed edges), or entire faces from it; the result can be new edges, new wires, new faces, or even new extruded solids which can be used in boolean operations for effects such as engraving or stamping.
