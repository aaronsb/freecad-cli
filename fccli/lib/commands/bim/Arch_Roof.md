---
command: "Arch_Roof"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Roof"
  tooltip: "Creates a roof object from the selected wire."
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "R, F"
  workbench: "BIMWorkbench"
  wiki: "Arch_Roof"
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

The Arch Roof tool allows for the creation of a sloped roof from a selected wire. The created roof object is parametric, keeping its relationship with the base object. The principle is that each edge is seen allotting a profile of roof (slope, width, overhang, thickness).

Note: This tool is still in development, and might fail with very complex shapes.
