---
command: "BIM_Trash"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Move to Trash"
  tooltip: "Moves the selected objects to the trash folder"
  toolbar: null
  menu: "Utils"
  shortcut: "Shift+Del"
  workbench: "BIMWorkbench"
  wiki: "BIM_Trash"
  wiki_rev: "0499378"
  seed: "8b12424c493d"
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

The BIM Trash tool moves the selected objects to the "Trash" group. The Trash group will be created if not already present in the document. The Trash group is simply a hidden group, that allows you to not permanently delete objects, but still retain them in the document. This is useful when you are unsure if you'll need objects later, or if an object cannot be deleted because other objects depend on it.
