---
command: "Arch_CloseHoles"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Close Holes"
  tooltip: "Closes holes in open shapes, turning them into solids"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_CloseHoles"
  wiki_rev: "0499378"
  seed: "576abcf60562"
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

This tool identifies holes (circular sequence of open edges) in a Shape object and attempts to close it by adding it a new face made from that edges sequence. You must still verify yourself that the result is a solid, though.

## See also

- Arch_Check
