---
command: "CAM_ToolController"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Tool Controller"
  tooltip: "Adds a new tool controller to the active job"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_ToolController"
  wiki_rev: "0499378"
  seed: "9bc216a7b152"
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

A tool controller carries properties for how a tool should be used in one or more operations.

For example a tool, like a 1/4 inch cutter can run at many different spindle speeds and feed rates. The same tool might be used in different ways in the same job.
