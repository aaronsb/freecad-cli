---
command: "Draft_PathLinkArray"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Path Link Array"
  tooltip: "Creates linked copies of the selected object along a selected path"
  toolbar: null
  menu: "Array Tools"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_PathLinkArray"
  wiki_rev: "0499378"
  seed: "43b1196817b1"
# authored from here down; the tool never rewrites these
verb: null
example: select Box, Line; path_link_array
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft PathLinkArray command creates a Link array from a selected object by placing copies along a path. Use the Draft PathArray command to create a less efficient regular array instead. Except for the type of array that is created, Link array or regular array, this command is identical to the Draft PathArray command. See there for more information.

## See also

- Draft_OrthoArray
- Draft_PolarArray
- Draft_CircularArray
- Draft_PathArray
- Draft_PointArray
- Draft_PointLinkArray
