---
command: "Std_ToggleNavigation"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle Navigation/&Edit Mode"
  tooltip: "Toggles between navigation and edit mode"
  toolbar: null
  menu: "View"
  shortcut: "Esc"
  workbench: null
  wiki: "Std_ToggleNavigation"
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

The Std ToggleNavigation command is intended for certain inspection operations and certain interactive mesh editing operations. These operations are quite 'expensive' and therefore rely on an edit mode during which most navigation options are disabled. With this command it is possible to temporarily switch from edit mode to navigation mode, and, after changing the 3D view, switch back to edit mode.

Do not confuse this command with the Std Edit command.
