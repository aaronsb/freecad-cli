---
command: "Draft_Snap_Extension"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Snap Extension"
  tooltip: "Snaps to an imaginary line that extends beyond the endpoints of straight edges"
  toolbar: "Draft Snap"
  menu: "Snapping"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Snap_Extension"
  wiki_rev: "0499378"
  seed: "111482060c54"
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

The Draft Snap Extension option snaps to an imaginary line that extends beyond the endpoints of straight edges. The edges can belong to Draft or BIM objects but also to objects created with other workbenches.

Up to 8 edges can be referenced by this snap option and Draft Snap Parallel, making it possible to snap to virtual intersections. Both snap options can also be combined with other snap options.

## See also

- Draft_Snap
- Draft_Snap_Lock
