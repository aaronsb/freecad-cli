---
command: "Arch_AxisSystem"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Axis System"
  tooltip: "Creates an axis system from a set of axes"
  toolbar: "Annotation Tools"
  menu: "Annotation"
  shortcut: "X, S"
  workbench: "BIMWorkbench"
  wiki: "Arch_AxisSystem"
  wiki_rev: "0499378"
  seed: "92f72aa7f042"
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

The AxisSystem tool allows you to combine two or three Arch Axis objects.

This is useful to define the intersection points between the different axes. Arch objects can then use this system to duplicate their shape on the different intersection points.

*Three Arch Axis objects combined into one Arch AxisSystem. An Arch Structure object uses this system as its **Axis* property, to have its shape duplicated at each intersection point.**

## See also

- Arch_Axis
- Arch_Grid
