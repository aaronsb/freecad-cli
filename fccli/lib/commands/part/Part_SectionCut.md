---
command: "Part_SectionCut"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Persiste&nt Section Cut"
  tooltip: "Creates a new object as a boolean intersection of all visible shapes and the selected axis planes"
  toolbar: null
  menu: "Part"
  shortcut: null
  workbench: "PartWorkbench"
  wiki: "Part_SectionCut"
  wiki_rev: "0499378"
  seed: "83d96d3f0ca1"
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

The Section Cut feature is available for all workbenches but it only works for Part and PartDesign objects and assemblies of those. It creates a persistent cut of objects and assemblies. Since the cut result is a normal Part Cut object, it can be modified further or for example 3D-printed. See below for possible applications.

## See also

- Std_ToggleClipPlane
