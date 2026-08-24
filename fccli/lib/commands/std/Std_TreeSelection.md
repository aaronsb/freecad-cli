---
command: "Std_TreeSelection"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "&Go to Selection"
  tooltip: "Scrolls to the first selected item"
  toolbar: null
  menu: "Tree View Actions"
  shortcut: "T, G"
  workbench: null
  wiki: "Std_TreeSelection"
  wiki_rev: "0499378"
  seed: "1aada85d243a"
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

The Std TreeSelection command scrolls the Tree view to the first created object in a 3D view selection.

If the Tree view SyncSelection mode is off, the Tree view is scrolled to the first created object in the selection whose parent is already expanded in the Tree view. If none of the objects' parents are expanded the command will have no effect in that mode.
