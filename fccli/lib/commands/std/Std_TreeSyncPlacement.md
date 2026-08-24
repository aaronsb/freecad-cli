---
command: "Std_TreeSyncPlacement"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "&3 Sync Placement"
  tooltip: "Adjusts the placement on drag-and-drop of objects across coordinate systems (e.g. in part containers)"
  toolbar: null
  menu: "Tree View Actions"
  shortcut: "T, 3"
  workbench: null
  wiki: "Std_TreeSyncPlacement"
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

The Std TreeSyncPlacement command toggles the Tree view SyncPlacement mode. If this mode is on, the Placement of objects is automatically adjusted when they are dragged and dropped from one container into another container with a different coordinate system, preserving their placement relative to the global coordinate system.
