---
command: "Std_LinkMake"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Make Link"
  tooltip: "A link is an object that references another object, either within the same or in another document. Unlike clones, links reference the original shape directly, making them more memory-efficient, which helps with the creation of complex assemblies."
  toolbar: null
  menu: null
  shortcut: null
  workbench: null
  wiki: "Std_LinkMake"
  wiki_rev: "0499378"
  seed: "8b52ff7708f4"
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

[Std LinkMake

creates an App Link (`App::Link` class), a type of object that references or links to another object in the same document, or in another document. It is especially designed to efficiently duplicate a single object multiple times, which helps with the creation of complex assemblies from smaller subassemblies, and from multiple reusable components like screws, nuts, and similar fasteners.

The App Link object was newly introduced in v0.19; in the past, simple duplication of objects could be achieved with [Draft Clone, but this is a less efficient solution due to its implementation, which essentially creates a copy of the internal Shape of the source object. Instead, a Link directly references the original Shape, so it is more memory-efficient.

By itself the Link object can behave like an array, duplicating its base object many times; this can be done by setting its Element Count property to or larger. This "Link Array" object can also be created with the different array tools of the Draft Workbench, for example, [Draft OrthoArray, [Draft PolarArray, and [Draft CircularArray.

When used with the PartDesign Workbench, Links are intended to be used with [PartDesign Bodies, so it is recommended to set Display Mode Body to to select the features of the entire Body, and not the individual features. To create arrays of the internal PartDesign Features, use [PartDesign LinearPattern, [PartDesign PolarPattern, and [PartDesign MultiTransform.

The [Std LinkMake tool is not defined by a particular workbench, but by the base system, thus it is found in the structure toolbar that is available in all workbenches. The Link object, used in conjunction with [Std Part to group various objects, forms the basis of the Assembly3 and Assembly4 Workbenches.

## See also

- Std_Part
- Std_Group
- PartDesign_Body
