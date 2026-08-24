---
command: "Arch_Rebar"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Custom Rebar"
  tooltip: "Creates a reinforcement bar from the selected face of solid object and/or a sketch"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "R, B"
  workbench: "BIMWorkbench"
  wiki: "Arch_Rebar"
  wiki_rev: "0499378"
  seed: "4474261ac607"
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

The Arch Rebar tool allows you to place reinforcing bars inside Arch Structure objects.

Rebar objects are based on 2D profiles such as Draft objects and Sketches, that must be drawn on a face of the structural object. After creation you can adjust the properties of the rebar, including the number and diameter of the bars, and the offset distance between them and the faces of the structural element.
