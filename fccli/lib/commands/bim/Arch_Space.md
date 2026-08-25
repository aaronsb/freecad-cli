---
command: "Arch_Space"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Space"
  tooltip: "Creates a space object from selected boundary objects"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "S, A"
  workbench: "BIMWorkbench"
  wiki: "Arch_Space"
  wiki_rev: "0499378"
  seed: "370ccc850992"
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

The Arch Space tool allows you to define an empty volume, either by basing it on a solid shape, or by defining its boundaries, or a mix of both. If it is based solely on boundaries, the volume is calculated by starting from the bounding box of all the given boundaries, and subtracting the spaces behind each boundary. The Space object always defines a solid volume. The floor area of a space object, calculated by intersecting a horizontal plane at the center of mass of the space volume, can also be displayed.
