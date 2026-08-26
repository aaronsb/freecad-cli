---
command: "Draft_Snap_Intersection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Snap Intersection"
  tooltip: "Snaps to the intersection of 2 edges, and the intersection of a face and an edge"
  toolbar: "Draft Snap"
  menu: "Snapping"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Snap_Intersection"
  wiki_rev: "0499378"
  seed: "8ac1f59d86f4"
# authored from here down; the tool never rewrites these
verb: null
example: snap_intersection
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft Snap Intersection option snaps to the intersection of two edges. The edges can belong to Draft or BIM objects but also to objects created with other workbenches.

This snap option will also find apparent intersections of (extended) straight edges if Draft Snap WorkingPlane is active as well.

## See also

- Draft_Snap
- Draft_Snap_Lock
