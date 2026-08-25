---
command: "PartDesign_ShapeBinder"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Shape Binder"
  tooltip: "Creates a new shape binder"
  toolbar: null
  menu: "Part Design"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_ShapeBinder"
  wiki_rev: "0499378"
  seed: "764505816eb2"
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

The PartDesign ShapeBinder tool creates a shape binder referencing geometry from a single parent object. A ShapeBinder is used inside a PartDesign Body to reference geometry outside the Body. Using external geometry directly in a Body is not allowed and will lead to out of scope errors.

A ShapeBinder will track the relative placement of the referenced geometry, which is useful in the context of creating assemblies, if its Trace Support property is set to . See the Example below to understand how this works.

The referenced geometry can either be a single object (for example a Part Box, a PartDesign Body, or a sketch or Feature inside a Body), or one or more subelements (faces, edges or vertices) belonging to the same parent object. Which geometry should be selected depends on the intended purpose of the ShapeBinder. For a Boolean operation you would need to select a solid. For a Pad operation a face or a sketch can be used. And for the external geometry in a sketch, or to attach a sketch, any combination of subelements may be appropriate. The referenced geometry can also belong to the Body the ShapeBinder is nested in.

## See also

- PartDesign_SubShapeBinder
- PartDesign_Clone
