---
command: "Part_Cut"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Cut"
  tooltip: "Cuts 2 selected shapes"
  toolbar: "Frequently-used Part WB tools"
  menu: "Boolean"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_Cut"
  wiki_rev: "0499378"
  seed: "4a4198706200"
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

The Part Cut tool cuts (subtracts) selected Part objects, the last one being subtracted from the first one. This operation is fully parametric and the components can be modified and the result recomputed.

This tool is an automated form of the Boolean operation.

## See also

- Part_Boolean
- Part_Fuse
- Part_Common
