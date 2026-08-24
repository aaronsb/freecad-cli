---
command: "CAM_Simulator"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Legacy CAM Simulator"
  tooltip: "Simulates G-code on stock"
  toolbar: null
  menu: "CAM"
  shortcut: "P, M"
  workbench: "CAMWorkbench"
  wiki: "CAM_Simulator"
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

The Simulator tool allows Simulation of the CAM Job by sweeping 3D Models of the Tools used in each Operation, along the G-Code paths, subtracting material from the Stock, where the stock and tool overlap, providing visualization of the Job. This allows detection and isolation of errors prior to running the Job on a mill.

## See also

- CAM_Inspect
