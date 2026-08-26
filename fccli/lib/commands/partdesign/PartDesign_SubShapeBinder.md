---
command: "PartDesign_SubShapeBinder"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Sub-Shape Binder"
  tooltip: "Creates a reference to geometry from one or more objects, allowing it to be used inside or outside a body. It tracks relative placements, supports multiple geometry types (solids, faces, edges, vertices), and can work with objects in the same or external documents."
  toolbar: "Part Design Helper Features"
  menu: "Part Design"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_SubShapeBinder"
  wiki_rev: "0499378"
  seed: "1f544ad6e5ee"
# authored from here down; the tool never rewrites these
verb: null
example: select Box; sub_shape_binder 0 arc
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The PartDesign SubShapeBinder tool creates a shape binder referencing geometry from one or more parent objects. A SubShapeBinder is typically used inside a PartDesign Body to reference geometry outside the Body. Using external geometry directly in a Body is not allowed and will lead to out of scope errors. But a SubShapeBinder can also be used without being nested in a Body.

A SubShapeBinder will track the relative placement of the referenced geometry, which is useful in the context of creating assemblies, but on top of that also has its own placement.

The referenced geometry can consist of one or multiple elements. Each element can be an individual object (for example a PartDesign Body), a subobject (for example a Part Box inside a Std Part, or a sketch or Feature inside a Body), or a subelement (a face, edge or vertex). Which geometry should be selected depends on the intended purpose of the SubShapeBinder. For a Boolean operation you would need to select a solid. For a Pad operation a face, a sketch or a planar wire can be used. And for the external geometry in a sketch, or to attach a sketch, any combination of subelements may be appropriate. Elements can belong to different parent objects, and can even belong to the Body the SubShapeBinder is nested in. Because a SubShapeBinder is Link-based the referenced geometry can also belong to an external document.

## See also

- PartDesign_Clone
