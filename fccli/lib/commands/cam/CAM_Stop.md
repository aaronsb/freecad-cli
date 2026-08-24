---
command: "CAM_Stop"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Stop"
  tooltip: "Adds an optional or mandatory stop to the program"
  toolbar: null
  menu: "Supplemental Commands"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Stop"
  wiki_rev: "0499378"
  seed: "992c3c295735"
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

The tool Stop inserts a Stop command (M1). This command will Pause a running program on the CNC controller, waiting for user interaction to continue.

Note: this does not stop the spindle.
