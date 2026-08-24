---
command: "PartDesign_Hole"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Hole"
  tooltip: "Creates holes in the active body at the center points of circles or arcs of the selected sketch or profile"
  toolbar: "Part Design Modeling Features"
  menu: "Subtractive Features"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Hole"
  wiki_rev: "0499378"
  seed: "3153043e6f0c"
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

The Hole feature creates one or more holes from a selected sketch's circles and arcs. If arcs are present they must be part of closed contours. All non arc/circle entities are ignored but they still must form closed contours. Many parameters can be set such as threading and size, fit, hole type (countersink, counterbore, straight) and more.

The centers of the circles and arcs are used to position the holes, but please note that their radii are not taken into account. The generated holes will be identical even if the radii vary.

## See also

- PartDesign_Pocket
