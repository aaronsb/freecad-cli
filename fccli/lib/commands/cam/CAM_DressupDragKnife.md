---
command: "CAM_DressupDragKnife"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Drag Knife"
  tooltip: "Modifies a toolpath to add dragknife corner actions"
  toolbar: null
  menu: "Path Dressup"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_DressupDragKnife"
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

The tool DressupDragKnife uses a cutting edge on a pivot to cut sheet material like vinyl, cardboard, and leather. The cutting point is not aligned with the center of the spindle but rather follows it as the spindle moves. Because the cutting point is offset, the path must be modified to extend past the endpoint of each segment. Also, the dragknife is incapable of making extremely tight turns. To compensate, a pivot 'corner action' is inserted which momentarily lifts the blade slightly and then pivots into the new position.

This tool dresses up an existing path to add corner actions and edge extensions for drag knife cutting.

## See also

- CAM_DressupTag
- CAM_DressupRampEntry
- CAM_DressupDogbone
