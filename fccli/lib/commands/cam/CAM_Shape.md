---
command: "CAM_Shape"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "From Shape"
  tooltip: "Creates a toolpath from a selected shape"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "CAMWorkbench"
  wiki: "CAM_Shape"
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

The tool Shape doesn\'t match the current CAM workflow. For that reason it\'s moved to the experimental features.

This tool generates tool-paths from CAM Object edges.

Tool-paths are uncompensated for tool radius. There is no Tool controller associated with the generated tool-paths .
