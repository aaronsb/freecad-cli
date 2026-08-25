---
command: "Std_StoreWorkingView"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "St&ore Working View"
  tooltip: "Stores a temporary working view for the current document"
  toolbar: null
  menu: "Standard Views"
  shortcut: "Shift+End"
  workbench: null
  wiki: "Std_StoreWorkingView"
  wiki_rev: "0499378"
  seed: "182a54c81aec"
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

The Std StoreWorkingView command stores the camera settings of the active 3D view in its temporary working view. This view can be recalled with the Std RecallWorkingView command.

Each 3D view has its own working view. Storing a new working view will overwrite the existing working view of the active 3D view. When a 3D view is closed its working view is lost.

## See also

- Std_RecallWorkingView
- Std_FreezeViews
