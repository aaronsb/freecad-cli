---
command: "Std_Part"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Part"
  tooltip: "Creates a part, which is a general-purpose container to group objects so they act as a unit in the 3D view. It is intended to arrange objects that have a part TopoShape, like part primitives, Part Design bodies, and other parts."
  toolbar: "Structure"
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_Part"
  wiki_rev: "0499378"
  seed: "47b41f1955f4"
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

[Std Part

(internally called App Part) is a general purpose container that keeps together a group of objects so that they can be moved together as a unit in the 3D view.

The Std Part element was developed to be the basic building block to create mechanical assemblies. In particular, it is meant to arrange objects that have a Part TopoShape, like Part Primitives, PartDesign Bodies, and other Part Features. The Std Part provides an Origin object with local X, Y, and Z axes, and standard planes, that can be used as reference to position the contained objects. In addition, Std Parts may be nested inside other Std Parts to create a big assembly from smaller sub-assemblies.

Although it is primarily intended for solid bodies, the Std Part can be used to manage any object that has a Placement property, so it can also contain Mesh Features, sketches, and other objects derived from the App GeoFeature class.

Do not confuse the [PartDesign Body with the [Std Part. The first one is a specific object used in the PartDesign Workbench, intended to model a single contiguous solid by means of PartDesign Features. On the other hand, the Std Part is not used for modelling, just to arrange different objects in space, with the intention to create assemblies.

The [Std Part tool is not defined by a particular workbench, but by the base system, thus it is found in the structure toolbar that is available in all workbenches. To group objects arbitrarily without considering their position, use [Std Group; this object does not affect the placements of the elements that it contains, it is essentially just a folder that is used to keep the Tree view organized.

## See also

- Std_Group
- PartDesign_Body
