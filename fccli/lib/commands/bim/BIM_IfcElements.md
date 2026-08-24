---
command: "BIM_IfcElements"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Manage IFC Elements"
  tooltip: "Manages how the different elements of the BIM project will be exported to IFC"
  toolbar: "Manage Tools"
  menu: "Manage"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "BIM_IfcElements"
  wiki_rev: "0499378"
  seed: "1d51390c8bda"
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

The IFC Elements Manager dialog allows you to manage names, IFC types and materials of the BIM elements of your model. Its purpose is to offer an easy general view of your model and to allow you to make sure everything is as you wish before exporting the model to IFC.

With it, you can:

- Sort objects alphabetically, by material, by IFC type or according to the model structure. You can also show all or only the currently visible objects
- Rename objects by double-clicking their name
- Change their IFC type either by clicking an individual type or, if more than one is selected, using the "change type to:" drop-down menu
- Change their material either by clicking an individual material or, if more than one is selected, using the "change material to:" drop-down menu
