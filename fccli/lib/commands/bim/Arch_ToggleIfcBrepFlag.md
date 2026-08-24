---
command: "Arch_ToggleIfcBrepFlag"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Toggle IFC B-Rep Flag"
  tooltip: "Forces an object to be exported as B-rep or not"
  toolbar: null
  menu: "Utils"
  shortcut: null
  workbench: "BIMWorkbench"
  wiki: "Arch_ToggleIfcBrepFlag"
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

The Arch ToggleIfcBrepFlag tool turns the IfcBrep flag of a selected BIM object on/off (the default is always off). If the flag in on, when exported to IFC, the object will be exported as an IfcFacetedBrep object, even if a higher-level kind of export such as IfcExtrudedAreaSolid or IfcBooleanResult is possible. Although IfcFacetedBrep objects are heavier and less editable (they loose some geometry information such as the modeling history), they are often less error-prone. Setting this flag allows to solve some cases of objects that are not exported correctly when the flag is not set.

## See also

- Arch_IfcExplorer
- Arch_IFC
