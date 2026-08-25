---
command: "FEM_PostApplyChanges"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Apply Changes to Pipeline"
  tooltip: "Applies changes to parameters directly and not on recompute only"
  toolbar: "Results"
  menu: "Results"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_PostApplyChanges"
  wiki_rev: "0499378"
  seed: "4d18019f530e"
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

Toggles if changes to pipelines and filters are applied immediately or not.

If the feature is active, changes to filter functions and filters have an immediate effect. However, for large result meshes this can slow down the PC significantly.

If the feature is not active, a change of the size and position of functions first have an effect after recomputing the function object (see Std Refresh). For changes to filters, the change will first have an effect when pressing in the filter dialog the button Apply or by recomputing the filter object.

## See also

- Std_Refresh
- FEM_PostCreateFunctions
