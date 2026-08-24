---
command: "Part_Extrude"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Extrude"
  tooltip: "Extrudes the selected sketch or profile"
  toolbar: "Frequently-used Part WB tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Extrude"
  wiki_rev: "0499378"
  seed: "d2668dc2d4f9"
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

Part Extrude extends a shape by a specified distance, in a specified direction. The output shape type will vary depending on the input shape type and the options selected.

In most common scenarios, the following lists the expected output shape type from a given input shape type,

- Extrude a Vertex (point), will produce a lineal Edge (Line)
- Extrude a open edge (e.g. line, arc), will produce a open face (e.g. plane)
- Extrude a closed edge (e.g. circle), will optionally produce a closed face (e.g. an open ended cylinder) or if the parameter "solid" is "true" will produce a solid (e.g. a closed solid cylinder)
- Extrude a open Wire (e.g. a Draft Wire), will produce a open shell (several joined faces)
- Extrude a closed Wire (e.g. a Draft Wire), will optionally produce a shell (several joined faces) or if the parameter "solid" is "true" will produce a solid
- Extrude a face (e.g. plane), will produce a solid (e.g. Cuboid)
- Extrude a [Draft ShapeString, will produce a compound of solids (the string is a compound of the letters which are each a solid)
- Extrude a shell of faces, will produce a Compsolid.

## See also

- Draft_Trimex
- PartDesign_Pad
