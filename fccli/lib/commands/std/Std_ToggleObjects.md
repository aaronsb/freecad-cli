---
command: "Std_ToggleObjects"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "To&ggle All Objects"
  tooltip: "Toggles the visibility of all objects in the active document"
  toolbar: null
  menu: "Visibility"
  shortcut: null
  workbench: null
  wiki: "Std_ToggleObjects"
  wiki_rev: "0499378"
  seed: "2a954367a704"
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

The Std ToggleObjects command toggles the visibility of all objects belonging to the active document in 3D views. Be careful when you use this command as it will also toggle the visibility of sub-elements of PartDesign bodies and objects used for Part Booleans. In most cases these should stay invisible.

## See also

- Std_ToggleVisibility
- Std_ShowSelection
- Std_HideSelection
- Std_ShowObjects
- Std_HideObjects
