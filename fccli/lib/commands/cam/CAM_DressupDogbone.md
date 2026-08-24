---
command: "CAM_DressupDogbone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Dogbone"
  tooltip: "Creates a dogbone dress-up object from a selected toolpath"
  toolbar: null
  menu: "Path Dressup"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_DressupDogbone"
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

The tool DressupDogbone dresses up an existing path to overcut corners on inside angles of a profile or contour operation. A cylindrical cutter cannot cut all the way into an acute corner without colliding with the model. In certain cases, it may be preferable to violate the model and ensure that the material at the corner is removed. This is especially necessary if parts are going to intersect/interlock with each other.

## See also

- CAM_DressupTag
- CAM_DressupRampEntry
- CAM_DressupDragKnife
