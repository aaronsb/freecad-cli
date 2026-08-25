---
command: "Part_Thickness"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Thickness"
  tooltip: "Removes the selected faces and offsets the remaining shape outward to add thickness"
  toolbar: "Part Tools"
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Thickness"
  wiki_rev: "0499378"
  seed: "e4b2c57a9b64"
# authored from here down; the tool never rewrites these
verb: null
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Thickness tool works on a solid shape and transforms it into a hollow object, giving to each of its faces a defined and constant thickness. On some solids it allows you to significantly speed up the work, and avoids making extrusions and pockets.

## See also

- Part_Offset
