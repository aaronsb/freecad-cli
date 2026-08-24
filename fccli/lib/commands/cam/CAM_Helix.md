---
command: "CAM_Helix"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Helix"
  tooltip: "Creates a Helical toolpath from the features of a base object"
  toolbar: "New Operations"
  menu: "CAM"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Helix"
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

The CAM Helix tool appends a helical clearing operation to the Job. Clockwise Helix outputs (G2) G-Code commands. Counterclockwise outputs (G3) G-Code commands. Step Over percentage specifies the concentric step-over as a percentage of the Tool diameter. One or more helical paths will be created at progressively different diameters, to clear the hole.
