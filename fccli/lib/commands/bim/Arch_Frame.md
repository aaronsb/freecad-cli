---
command: "Arch_Frame"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Frame"
  tooltip: "Creates a frame object from a planar 2D object (the extrusion path(s)) and a profile. Make sure objects are selected in that order."
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "F, R"
  workbench: "BIMWorkbench"
  wiki: "Arch_Frame"
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

The Arch Frame tool is used to build all kinds of frame objects based on a profile and a layout. The profile is extruded along the edges of the layout, which can be any 2D object such as a sketch, or a Draft object. It is especially useful to create railings, or frame walls. Frame objects can then easily be turned into wall or structure objects.
