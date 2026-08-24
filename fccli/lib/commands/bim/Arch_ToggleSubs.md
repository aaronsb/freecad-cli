---
command: "Arch_ToggleSubs"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Subcomponents"
  tooltip: "Shows or hides the subcomponents of this object"
  toolbar: null
  menu: "Utils"
  shortcut: "Ctrl+Space"
  workbench: "BIMWorkbench"
  wiki: "Arch_ToggleSubs"
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

The Arch ToggleSubs tools toggles the visibility of all the subtractions of an BIM object between visible and hidden.

Normally, if an Arch object, like an Arch Wall, is selected and you press Space only the external wall will be hidden or made visible, but not the internal objects.

With this tool, the internal subtracted objects will all become visible or hidden.

## See also

- Arch_Component
