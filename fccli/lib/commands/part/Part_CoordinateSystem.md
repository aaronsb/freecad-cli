---
command: "Part_CoordinateSystem"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Coordinate System"
  tooltip: "Creates a coordinate system that can be attached to other objects"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_CoordinateSystem"
  wiki_rev: "0499378"
  seed: "3c16d973d603"
# authored from here down; the tool never rewrites these
verb: null
example: coordinate_system
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part CoordinateSystem command creates a coordinate system object that can be attached to other objects. A coordinate system is one of several datum objects. A datum object is typically used to attach multiple other objects to. If the position or orientation of a datum object changes, all objects attached to it will follow.

## See also

- Part_DatumPlane
- Part_DatumLine
- Part_DatumPoint
