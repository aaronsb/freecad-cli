---
command: "Arch_MultiMaterial"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Multi-Material"
  tooltip: "Creates or edits multi-materials"
  toolbar: null
  menu: null
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_MultiMaterial"
  wiki_rev: "0499378"
  seed: "13a443561989"
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

The Multi-Material tool defines a list of materials with, for each material, a name and a thickness value. This multi-materials list can then be added to an Arch object instead of a single Arch Material .

Not all Arch objects can currently make use of multi-materials, and the use they do of it differs. Currently:

- Walls with a MultiMaterial will use the material definitions and thicknesses to create a multi-layer wall
- Windows with a MultiMaterial will attribute materials with a given name defined inside the MultiMaterial to window components with a same name or type (see below). Material thickness is not considered.
- Panels with a MultiMaterial will use the material definitions and thicknesses to create a multi-layer panel

## See also

- Arch_SetMaterial
