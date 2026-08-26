---
command: "Part_TransformedCopy"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Transformed Copy"
  tooltip: "Creates a non-parametric copy with transformed placement of the selected shapes"
  toolbar: null
  menu: "Copy"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_TransformCopy"
  wiki_rev: "0499378"
  seed: "0e9455ddd3e0"
# authored from here down; the tool never rewrites these
verb: null
example: select Box; transformed_copy
aliases: []
requires: []
panel: null
family: null
choice: null
also: []
rank: null
type: null
---

The Part TransformedCopy command creates non-parametric copies of objects. It is intended for objects nested in containers.

The Placement of the copies is adjusted, accounting for the placement of the container(s), so that their position and rotation relative to the global coordinate system is the same as that of the original objects. If the selected objects are not nested, or nested in a container with a default placement, this command produces the same results as Part SimpleCopy.

## See also

- Part_SimpleCopy
