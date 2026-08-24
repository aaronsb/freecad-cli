---
command: "Arch_SectionPlane"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Section Plane"
  tooltip: "Creates a section plane object, including the selected objects"
  toolbar: "Annotation Tools"
  menu: "Annotation"
  shortcut: "S, E"
  workbench: "BIMWorkbench"
  wiki: "Arch_SectionPlane"
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

The Arch SectionPlane tool places in the current document a section plane "thing", which defines a section or view plane. The "thing" takes its placement according to the current Draft Working Plane and can be relocated and reoriented by moving and rotating it, until it describes the 2D view you want to obtain. The Section plane object will only consider a certain set of objects. Objects that are selected when you create a Section Plane will be added to that set automatically. Other objects can later be added or removed from a SectionPlane object with the Arch Add component and Arch Remove component tools, or by double-clicking the Section Plane in the tree view.

The Section Plane alone won't create any view of its objects set. For that, you must create a TechDraw ArchView to create a view in a TechDraw page.

## See also

- Draft_Shape2DView
