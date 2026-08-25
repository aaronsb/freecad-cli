---
command: "Arch_Wall"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Wall"
  tooltip: "Creates a wall object from scratch or from a selected object (wire, face or solid)"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "W, A"
  workbench: "BIMWorkbench"
  wiki: "Arch_Wall"
  wiki_rev: "0499378"
  seed: "f9330c0c7732"
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

The Arch Wall tool builds a Wall object from scratch or on top of any other shape-based or mesh-based object. A wall can be built without any base object, in which case it behaves as a cubic volume, using length, width and height properties. When built on top of an existing shape, a wall can be based on:

- A linear 2D object, such as lines, wires, arcs or sketches, in which case you can change thickness, alignment (right, left or centered) and height. The length property has no effect.
- A flat face, in which case you can only change the height. Length and width properties have no effect. If the base face is vertical, however, the wall will use the width property instead of height, allowing you to build walls from space-like objects or mass studies.
- A solid, in which case length, width and height properties have no effect. The wall simply uses the underlying solid as its shape.
- A mesh, in which case the underlying mesh must be a closed, manifold solid.

Walls can also have additions or subtractions. Additions are other objects whose shapes are joined in this Wall's shape, while subtractions are subtracted. Additions and subtractions can be added with the Arch Add and Arch Remove tools. Additions and subtractions have no influence over wall parameters such as height and width, which can still be changed. Walls can also have their height automatic, if they are included into a higher-level object such as floors. The height must be kept at 0, then the wall will adopt the height specified in the parent object.

When several walls should intersect, you need to place them into a floor to have their geometry intersected.
