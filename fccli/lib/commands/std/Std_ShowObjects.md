---
command: "Std_ShowObjects"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Show &All Objects"
  tooltip: "Shows all objects in the document"
  toolbar: null
  menu: "Visibility"
  shortcut: null
  workbench: null
  wiki: "Std_ShowObjects"
  wiki_rev: "0499378"
  seed: "f5ba2791e9d6"
# authored from here down; the tool never rewrites these
verb: null
example: show_all_objects
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Std ShowObjects command shows all objects belonging to the active document in 3D views. Be careful when you use this command as it will also show sub-elements of PartDesign bodies and objects used for Part Booleans. In most cases these should stay invisible.

## See also

- Std_ToggleVisibility
- Std_ShowSelection
- Std_HideSelection
- Std_ToggleObjects
- Std_HideObjects
