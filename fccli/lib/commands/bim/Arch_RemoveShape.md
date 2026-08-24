---
command: "Arch_RemoveShape"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Remove Shape From BIM"
  tooltip: "Removes cubic shapes from BIM components"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_RemoveShape"
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

The Arch RemoveShape tool attempts at removing the inner cubic shape of an Arch Wall or Arch Structure, and adjusting its properties, making it totally parametric. This tool will only work if the underlying shape is cubic (exactly 6 faces, all corners have only right angles).

## See also

- Arch_SplitMesh
- Arch_MeshToShape
