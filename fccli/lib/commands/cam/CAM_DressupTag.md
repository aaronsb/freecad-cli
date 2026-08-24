---
command: "CAM_DressupTag"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Tag"
  tooltip: "Creates a tag dress-up object from a selected toolpath"
  toolbar: null
  menu: "Path Dressup"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_DressupTag"
  wiki_rev: "0499378"
  seed: "4f35cb34df5d"
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

The tool DressupTag dresses up an existing path (usually a 2D contour cutting path) to leave tags that hold the part in place. Without them a part (which is not fixed to the base) is liable to fly off the machine uncontrollably as the final cut is made. The tags are intended to be broken off by hand (or using a chisel) and then filed flat to finish the part.

A video explanation of this feature is given at:

## See also

- CAM_DressupRampEntry
- CAM_DressupDogbone
- CAM_DressupDragKnife
