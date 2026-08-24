---
command: "CAM_Post"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Post Process"
  tooltip: "Post Processes the selected job"
  toolbar: "Project Setup"
  menu: "CAM"
  shortcut: "P, P"
  workbench: "CAMWorkbench"
  wiki: "CAM_Post"
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

The tool Post exports the selected CAM Job to a G-code file.

Each CNC Controller speaks a specific G-code dialect, requiring a Dialect-correct Postprocessor to translate the final output from the agnostic internal FreeCAD G-code dialect.
