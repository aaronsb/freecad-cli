---
command: "Draft_Trimex"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Trimex"
  tooltip: "Trims or extends the selected object, or extrudes single faces"
  toolbar: "2D Tools"
  menu: "Modify"
  shortcut: "T, R"
  workbench: "DraftWorkbench"
  wiki: "Draft_Trimex"
  wiki_rev: "0499378"
  seed: "7e7bf0018c9d"
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

The Draft Trimex command trims or extends a selected object. Intersections with the edge of another object can be used to determine new endpoints. The command can also be used to extrude a face, in which case it creates a Part Extrude object.

## See also

- Part_Extrude
