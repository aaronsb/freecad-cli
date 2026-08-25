---
command: "Arch_Reference"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "External Reference"
  tooltip: "Creates an external reference object"
  toolbar: null
  menu: null
  shortcut: "E, X"
  workbench: "BIMWorkbench"
  wiki: "Arch_Reference"
  wiki_rev: "0499378"
  seed: "66c46a391fe6"
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

The Arch Reference tool allows you to place an object in the current document that copies its shape and colors from a Part-based object (including Arch BuildingPart) stored in another FreeCAD file. If that FreeCAD file changes, the reference object is marked to be reloaded.
