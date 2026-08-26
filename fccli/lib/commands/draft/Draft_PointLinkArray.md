---
command: "Draft_PointLinkArray"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Point Link Array"
  tooltip: "Creates linked copies of the selected object at the points of a point object"
  toolbar: null
  menu: "Array Tools"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_PointLinkArray"
  wiki_rev: "0499378"
  seed: "487147977958"
# authored from here down; the tool never rewrites these
verb: null
example: select Box, Box001; point_link_array
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft PointLinkArray command creates a Link array from a selected object by placing copies at the points from a point compound. Use the Draft PointArray command to create a less efficient regular array instead. Except for the type of array that is created, Link array or regular array, this command is identical to the Draft PointArray command. See there for more information.

## See also

- Draft_OrthoArray
- Draft_PolarArray
- Draft_CircularArray
- Draft_PathArray
- Draft_PathLinkArray
- Draft_PointArray
