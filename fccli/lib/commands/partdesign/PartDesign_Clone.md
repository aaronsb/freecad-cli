---
command: "PartDesign_Clone"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Clone"
  tooltip: "Copies a solid object parametrically as the base feature of a new body"
  toolbar: "Part Design Helper Features"
  menu: "Part Design"
  shortcut: null
  workbench: "PartDesignWorkbench"
  wiki: "PartDesign_Clone"
  wiki_rev: "0499378"
  seed: "a1f88bf929eb"
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

PartDesign Clone creates a linked copy of a selected object which will follow any future edits to the original object (except placement). For example, one use case is when you want to do PartDesign Boolean on an object created in another workbench. Most types of objects are accepted, as long as they are single solids. If you need to clone multiple objects (i.e., bodies) or a Part Container, you may use Draft Workbench's clone. One caveat is that the Part Design Workbench's clone sets the current placement of the clone as zero (both Cartesian translation and spatial orientations). While the Draft's workbenches clone calculates and sets the numerical values of the current placement and orientation of the cloned objects with respect to the cloned object container.

## See also

- Draft_Clone
