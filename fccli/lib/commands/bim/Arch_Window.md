---
command: "Arch_Window"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Window"
  tooltip: "Creates a window object from a selected object (wire, rectangle or sketch)"
  toolbar: "3D/BIM Tools"
  menu: "3D/BIM"
  shortcut: "W, N"
  workbench: "BIMWorkbench"
  wiki: "Arch_Window"
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

The Arch Window tool creates a base object for all kinds of \"embeddable\" objects, such as windows and doors. It is designed to be either independent, or \"hosted\" inside another component such as an Arch Wall, Arch Structure, or Arch Roof. It has its own geometry, that can be made of several solid components (commonly a frame and inner panels), and also defines a volume to be subtracted from the host objects, in order to create an opening.

Window objects are based on closed 2D objects, such as Draft Rectangles or Sketches, that are used to define their inner components. The base 2D object must therefore contain several closed wires, that can be combined to form filled panels (one wire) or frames (several wires).

The Window tool features several presets. These allow the user to create common types of windows and doors with certain editable parameters, without the need to create the base 2D objects and components manually.

All information applicable to an Arch Window also applies to an Arch Door, as it\'s the same underlying object.
