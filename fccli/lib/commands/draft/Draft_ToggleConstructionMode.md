---
command: "Draft_ToggleConstructionMode"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Construction Mode"
  tooltip: "Toggles the construction mode"
  toolbar: null
  menu: "Utilities"
  shortcut: "C, M"
  workbench: "DraftWorkbench"
  wiki: "Draft_ToggleConstructionMode"
  wiki_rev: "0499378"
  seed: "b7dc98309855"
# authored from here down; the tool never rewrites these
verb: null
example: toggle_construction_mode
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Draft ToggleConstructionMode command switches Draft construction mode on or off. If construction mode is on new Draft objects are placed in a dedicated group and given a predefined color. This feature is intended for, often temporary, construction geometry used to provide new snap points for creating other objects. When the construction geometry is no longer needed the construction group can easily be hidden or deleted.

## See also

- Draft_AddConstruction
- Draft_AutoGroup
