---
command: "Std_AddonMgr"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "&Addon Manager"
  tooltip: "Manages external workbenches, macros, and preference packs"
  toolbar: null
  menu: "Tools"
  shortcut: null
  workbench: null
  wiki: "Std_AddonMgr"
  wiki_rev: "0499378"
  seed: "5877f4967068"
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

The Std AddonMgr command opens the Addon manager. With the Addon manager you can install and manage external workbenches, macros, and preference packs provided by the FreeCAD community. By default the available addons are taken from two repositories, FreeCAD-addons and from the Macros recipes page. If GitPython and git are installed on your system, additional macros will be loaded from FreeCAD-macros. Custom repositories can be added in the Addon manager preferences.

Due to changes to the GitHub platform in the year 2020 the Addon manager no longer works if you use FreeCAD version 0.17 or earlier. You need to upgrade to version 0.18.5 or later. Alternatively you can install addons manually, see Notes below.

## See also

- External_workbenches
- Macros
