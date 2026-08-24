---
command: "PartDesign_Body"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Body"
  tooltip: "Creates a new body and activates it"
  toolbar: "Part Design Helper Features"
  menu: "Part Design"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Body"
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

A PartDesign Body is the base element to create solids shapes with the PartDesign Workbench. It can contain sketches, datum objects, and PartDesign Features that help in building a single contiguous solid.

The Body provides an Origin object which includes local X, Y, and Z axes, and standard planes. These elements can be used as references to attach sketches and primitive objects.

Do not confuse the PartDesign Body with the Std Part. The first one is a specific object used in the PartDesign Workbench, intended to model a single contiguous solid by means of PartDesign Features. The Std Part is a grouping object intended to create assemblies; it is not used for modelling, just to arrange different objects in space. Multiple bodies, and other Std Parts, can be placed inside a single Std Part to create a complex assembly.

## See also

- Std_Part
- Feature_editing
