---
command: "Draft_SubelementHighlight"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Highlight Subelements"
  tooltip: "Highlights the subelements of the selected objects, to be able to move, rotate, and scale them"
  toolbar: "Draft Modification"
  menu: "Modification"
  shortcut: "H, S"
  workbench: "DraftWorkbench"
  wiki: "Draft_SubelementHighlight"
  wiki_rev: "0499378"
  seed: "dcfbf471aebb"
# authored from here down; the tool never rewrites these
verb: null
example: select Wire; highlight_subelements
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft SubelementHighlight command temporarily highlights selected objects, or the base objects of selected objects. It is intended to be used in conjunction with the subelement mode of the Draft Move command, the Draft Rotate command or the Draft Scale command. Currently subelement mode only works properly for Draft Lines and Draft Wires.

## See also

- Draft_Move
- Draft_Rotate
- Draft_Scale
