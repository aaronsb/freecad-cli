---
command: "CAM_Comment"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Comment"
  tooltip: "Adds a Comment to the CNC program"
  toolbar: null
  menu: "Supplemental Commands"
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Comment"
  wiki_rev: "0499378"
  seed: "8762096d13c8"
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

The tool Comment inserts a comment. When exporting a project to G-code, the comments will be inserted in the G-code program, and can be read by people reading the file. Some machine controllers will also display comments on their display screens.
