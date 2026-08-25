---
command: "Std_Group"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "New Group"
  tooltip: "Creates a group, which is a general-purpose container to group objects in the tree view, regardless of their data type. It is a simple folder to organize the objects in a model."
  toolbar: "Structure"
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_Group"
  wiki_rev: "0499378"
  seed: "7fb61358549b"
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

Std Group (internally called App DocumentObjectGroup) is a general purpose container that allows you to group different types of objects in the Tree view, regardless of their data type. It is used as a simple folder to categorize and organize the objects in your model, in order to keep a logical structure. Std Groups may be nested inside other Std Groups.

The Std Group tool is not defined by a particular workbench, but by the base system, thus it is found in the structure toolbar that is available in all workbenches.

To group 3D objects as a single unit, with the intention of creating assemblies, use Std Part instead.

## See also

- Std_Part
- Draft_SelectGroup
- Draft_AddToGroup
