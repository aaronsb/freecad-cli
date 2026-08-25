---
command: "Draft_Heal"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Heal"
  tooltip: "Heals faulty Draft objects saved with an earlier version of FreeCAD. If an object is selected it tries to heal only that object, otherwise it tries to heal all objects in the active document."
  toolbar: null
  menu: "Utilities"
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_Heal"
  wiki_rev: "0499378"
  seed: "f4030f017846"
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

The Draft Heal command heals problematic Draft objects found in very old files. It tries to recreate the old objects from scratch and transfer their properties to the new objects.

## See also

- Draft_Upgrade
- Draft_Downgrade
