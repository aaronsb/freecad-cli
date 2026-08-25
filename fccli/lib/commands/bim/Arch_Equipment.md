---
command: "Arch_Equipment"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Equipment"
  tooltip: "Creates an equipment from a selected object (Part or Mesh)"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "E, Q"
  workbench: "BIMWorkbench"
  wiki: "Arch_Equipment"
  wiki_rev: "0499378"
  seed: "d297e479b8f0"
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

The Arch Equipment tool offers you a simple and convenient way to insert non-structural, standalone elements such as pieces of furniture, hydro-sanitary equipments or electrical appliances to your projects. Equipments are based on Part shapes, which allow them to benefit from the solidity and possibilities of BRep geometry, and generate nice views when rendered to plan and section views.

As of version 0.17, equipment objects also have a HiRes property where a Mesh object can be attached. Equipment objects can then be made to display that mesh in the 3D view instead of their shape, which allows to use any high-resolution mesh objects such as detailed pieces of furniture commonly found on websites.

When using the Arch OBJ exporter, all equipment objects that are in mesh display mode will be exported as their mesh instead of their shape.
