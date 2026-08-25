---
command: "FEM_PostFilterWarp"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Warp Filter"
  tooltip: "Warps the geometry along a vector field by a certain factor"
  toolbar: "Results"
  menu: "Results"
  shortcut: null
  workbench: "FemWorkbench"
  wiki: "FEM_PostFilterWarp"
  wiki_rev: "0499378"
  seed: "6667772a10ac"
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

Displays the deformed shape of the model using a specified scale factor. Therefore a warp filter only has an effect for result vectors that deform the shape.

The result will be the same like with the *Displacement* slider of the result show dialog with the difference that the displacement is for the Warp filter in the SI unit meter. For example if you use a unit system where the length unit is mm and set a displacement factor of 100 in the result show dialog, you need to set for the Warp filter a factor of 100.000 to get the same result.

## See also

- FEM_PostPipelineFromResult
- FEM_tutorial
