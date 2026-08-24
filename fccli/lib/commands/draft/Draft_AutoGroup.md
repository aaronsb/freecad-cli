---
command: "Draft_AutoGroup"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Auto-Group"
  tooltip: "Adds new Draft and BIM objects to the selected layer or group"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "DraftWorkbench"
  wiki: "Draft_AutoGroup"
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

The Draft AutoGroup command changes the active Draft Layer or, optionally, the active Std Group or group-like BIM object. New Draft and BIM objects are automatically placed in this active layer or group.

This command was originally intended for groups, hence its name, but was redesigned in FreeCAD version 0.19 when a layer system was introduced. Because handling layers is now the default for the command the rest of this page will primarily focus on layers.

## See also

- Draft_Layer
- Std_Group
