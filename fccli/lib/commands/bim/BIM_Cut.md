---
command: "BIM_Cut"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Difference"
  tooltip: "Creates a difference between two shapes"
  toolbar: "3D Tools"
  menu: "Modify"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_Cut"
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

The Part Cut tool cuts (subtracts) selected Part objects, the last one being subtracted from the first one. This operation is fully parametric and the components can be modified and the result recomputed.

This tool is an automated form of the Boolean operation.

## See also

- Part_Boolean
- Part_Fuse
- Part_Common
