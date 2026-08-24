---
command: "FEM_ResultShow"
generated:                     # owned by the tool; rewritten on reconcile
  freecad: "1.1.3"
  label: "Show Result"
  tooltip: "Shows and visualizes the selected result data"
  toolbar: "Results"
  menu: "Results"
  shortcut: "R, S"
  workbench: "FemWorkbench"
  wiki: "FEM_ResultShow"
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

The ResultShow command opens the dialog for a FEM results object. A Result object is automatically created when a FEM analysis was performed using either the solver Calculix or Z88.

A Result object holds the resulting mesh and can visualize the results. It is designed and therefore limited to thermomechanical results. Except for the Solver Elmer, it can be used as an alternative to a result pipeline. A result pipeline can be used to visualize any kind of results (also electrical etc.).

The units used for the Result object are those of the set unit system while for result pipelines, the units are SI.

The visualization of the results is only active when the dialog is open. However, the dialog settings are stored in the FreeCAD model file.

## See also

- FEM_PostPipelineFromResult
- FEM_tutorial
