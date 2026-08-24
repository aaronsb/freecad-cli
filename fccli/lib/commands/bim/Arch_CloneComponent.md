---
command: "Arch_CloneComponent"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clone Component"
  tooltip: "Clones an object as an undefined architectural component"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_CloneComponent"
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

The Arch Clone Component produces Arch Components that are clones of selected Arch objects.

Unlike the Draft Clone tool, which will produce a clone of the same type as the selected object, this tool produces a generic Arch Component object that can assume any role, not necessarily the role of the cloned object.

The clone component will simply have its CloneOf property set to the selected object.

## See also

- Draft_Clone
- Arch_Component
